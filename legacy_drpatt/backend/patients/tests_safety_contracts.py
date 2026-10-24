"""Synthetic workflow statuses, not clinical thresholds or treatment advice."""
from datetime import datetime, timezone
from unittest import TestCase

from .safety_contracts import DOMAINS, evaluate_safety, validate_safety_policy


def synthetic_policy():
    return {'requirements': [{'domain': domain, 'concept_id': 'safety-' + domain,
        'max_age_hours': 24, 'allow_not_applicable': domain == 'pregnancy'} for domain in sorted(DOMAINS)],
        'soc_prerequisites': []}


def synthetic_assessments():
    return [{'concept_id': 'safety-' + domain, 'evidence_id': 'e-' + domain,
        'source_id': 's-' + domain, 'verification': 'VERIFIED', 'verified_by': 'test-reviewer',
        'source_type': 'PHYSICIAN_OBSERVED', 'source_timestamp': '2026-10-01T00:00:00Z',
        'value': 'CLEAR'} for domain in sorted(DOMAINS)]


class SafetyContractTests(TestCase):
    def evaluate(self, evidence=None, **kwargs):
        return evaluate_safety(kwargs.pop('policy', synthetic_policy()),
            synthetic_assessments() if evidence is None else evidence,
            as_of=datetime(2026, 10, 1, 1, tzinfo=timezone.utc), **kwargs)

    def test_missing_renal_and_liver_never_pass(self):
        evidence = [item for item in synthetic_assessments() if item['concept_id'] not in {'safety-renal', 'safety-hepatic'}]
        result = self.evaluate(evidence, interaction_source_status='AVAILABLE')
        self.assertEqual(result['decision'], 'DEFER')
        self.assertEqual(result['coverage'], {'assessed': 8, 'required': 10})

    def test_unavailable_interaction_source_blocks_clearance(self):
        result = self.evaluate()
        self.assertEqual(result['safety_state'], 'PARTIAL')
        self.assertIn({'domain': 'interactions', 'code': 'INTERACTION_SOURCE_UNAVAILABLE'}, result['missing_requirements'])

    def test_complete_does_not_authorize_treatment(self):
        result = self.evaluate(interaction_source_status='AVAILABLE')
        self.assertEqual(result['safety_state'], 'NO_RED_FLAG_IDENTIFIED_IN_AVAILABLE_DATA')
        self.assertFalse(result['clinical_use_authorized'])

    def test_missing_all_is_incomplete(self):
        self.assertEqual(self.evaluate([])['safety_state'], 'INCOMPLETE')

    def test_emergency_takes_precedence_over_missing_domains(self):
        record = synthetic_assessments()[0]
        record['value'] = 'EMERGENCY'
        result = self.evaluate([record])
        self.assertEqual(result['safety_state'], 'EMERGENCY')
        self.assertEqual(result['decision'], 'ESCALATE')

    def test_stale_clearance_is_not_used(self):
        evidence = synthetic_assessments()
        for item in evidence:
            item['source_timestamp'] = '2026-09-01T00:00:00Z'
        self.assertEqual(self.evaluate(evidence)['safety_state'], 'INCOMPLETE')

    def test_future_clearance_is_not_used(self):
        evidence = synthetic_assessments()
        for item in evidence:
            item['source_timestamp'] = '2027-01-01T00:00:00Z'
        self.assertEqual(self.evaluate(evidence)['safety_state'], 'INCOMPLETE')

    def test_unverified_clearance_is_not_used(self):
        evidence = synthetic_assessments()
        for item in evidence:
            item['verification'] = 'UNVERIFIED'
        self.assertEqual(self.evaluate(evidence)['safety_state'], 'INCOMPLETE')

    def test_missing_soc_prerequisite_requests_assessment(self):
        policy = synthetic_policy()
        policy['soc_prerequisites'] = [{'concept_id': 'synthetic-soc', 'max_age_hours': 24}]
        result = self.evaluate(policy=policy, interaction_source_status='AVAILABLE')
        self.assertEqual(result['decision'], 'DEFER')
        self.assertEqual(result['soc_missing'][0]['concept_id'], 'synthetic-soc')

    def test_policy_cannot_omit_required_domain(self):
        policy = synthetic_policy()
        policy['requirements'].pop()
        with self.assertRaises(ValueError):
            validate_safety_policy(policy)

    def test_ambiguous_clearance_not_counted_twice(self):
        evidence = synthetic_assessments()
        evidence.append({**evidence[0], 'evidence_id': 'duplicate'})
        result = self.evaluate(evidence, interaction_source_status='AVAILABLE')
        self.assertEqual(result['coverage']['assessed'], 9)

    def test_numeric_lab_is_not_interpreted_as_clearance(self):
        evidence = synthetic_assessments()
        for item in evidence:
            item.update(value=42, source_type='LAB_MEASURED')
        self.assertEqual(self.evaluate(evidence)['safety_state'], 'INCOMPLETE')

    def test_untrusted_new_clearance_does_not_hide_prior_emergency(self):
        old = {**synthetic_assessments()[0], 'value': 'EMERGENCY'}
        for changes in ({'verification': 'UNVERIFIED'},
                        {'source_timestamp': 'invalid'},
                        {'source_type': 'PATIENT_REPORTED'},
                        {'source_timestamp': '2027-01-01T00:00:00Z'}):
            with self.subTest(changes=changes):
                newer = {**old, 'evidence_id': 'new', 'value': 'CLEAR',
                         'source_timestamp': '2026-10-01T00:30:00Z', **changes}
                result = self.evaluate([old, newer])
                self.assertEqual(result['safety_state'], 'EMERGENCY')
                self.assertEqual(result['alerts'][0]['evidence_id'], old['evidence_id'])

    def test_verified_current_clearance_replaces_prior_assessment(self):
        old = {**synthetic_assessments()[0], 'value': 'EMERGENCY'}
        newer = {**old, 'evidence_id': 'new', 'value': 'CLEAR',
                 'source_timestamp': '2026-10-01T00:30:00Z'}
        self.assertEqual(self.evaluate([old, newer])['alerts'], [])

    def test_legacy_replay_keeps_v1_selection_semantics(self):
        old = {**synthetic_assessments()[0], 'value': 'EMERGENCY'}
        newer = {**old, 'evidence_id': 'new', 'value': 'CLEAR', 'verification': 'UNVERIFIED',
                 'source_timestamp': '2026-10-01T00:30:00Z'}
        self.assertEqual(self.evaluate([old, newer], preserve_unresolved_alerts=False)['alerts'], [])
