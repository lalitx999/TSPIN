"""Synthetic EP1 acceptance cases; no patient data or database required."""

from copy import deepcopy
from unittest import TestCase

from patients.canonical_state import build_canonical_state


class CanonicalStateTests(TestCase):
    def evidence(self, **changes):
        record = {
            'evidence_id': 'ev-1', 'patient_id': 'synthetic-1', 'hn': 'TEST-1',
            'concept_id': 'test-analyte', 'source_id': 'lab-1',
            'source_type': 'LAB_MEASURED', 'source_timestamp': '2026-10-01T00:00:00Z',
            'recorded_at': '2026-10-01T01:00:00Z', 'entered_by': 'import-service',
            'verification': 'VERIFIED', 'verified_by': 'test-reviewer',
            'version': 1, 'consent_scope': 'CARE', 'value': 12, 'unit': 'test-unit',
        }
        record.update(changes)
        return record

    def build(self, *records):
        return build_canonical_state('synthetic-1', 'TEST-1', list(records),
                                     expected_units={'test-analyte': 'test-unit'})

    def assertBlocked(self, state, code):
        self.assertEqual(state['status'], 'BLOCKED')
        self.assertIn(code, [issue['code'] for issue in state['issues']])

    def test_valid_structure_is_not_medical_approval(self):
        state = self.build(self.evidence())
        self.assertEqual(state['status'], 'VALIDATED_STRUCTURE')
        self.assertNotIn('score', state)
        self.assertNotIn('approved', state)

    def test_at22_cross_patient_blocked(self):
        self.assertBlocked(self.build(self.evidence(hn='OTHER')), 'PATIENT_IDENTITY_MISMATCH')

    def test_at23_units_not_guessed(self):
        self.assertBlocked(self.build(self.evidence(unit='wrong-unit')), 'UNIT_MISMATCH')

    def test_at24_duplicate_import_once(self):
        state = self.build(self.evidence(), self.evidence(evidence_id='ev-2'))
        self.assertEqual(state['active_evidence_ids'], ['ev-1'])
        self.assertEqual(state['duplicate_evidence_ids'], ['ev-2'])

    def test_timezone_equivalent_import_is_duplicate(self):
        state = self.build(self.evidence(), self.evidence(
            evidence_id='ev-2', source_timestamp='2026-10-01T07:00:00+07:00'))
        self.assertEqual(state['active_evidence_ids'], ['ev-1'])

    def test_at02_conflicting_verified_sources_blocked(self):
        state = self.build(self.evidence(), self.evidence(
            evidence_id='ev-2', source_id='lab-2', value=13))
        self.assertBlocked(state, 'CONFLICTING_VERIFIED_SOURCES')

    def test_different_dates_not_a_conflict(self):
        state = self.build(self.evidence(), self.evidence(
            evidence_id='ev-2', source_id='lab-2', value=13,
            source_timestamp='2026-10-02T00:00:00Z'))
        self.assertEqual(state['status'], 'VALIDATED_STRUCTURE')

    def test_at25_correction_keeps_old_evidence_changes_hash(self):
        old = self.evidence()
        corrected = self.evidence(evidence_id='ev-2', supersedes='ev-1', version=2,
                                  value=13, correction_reason='Corrected source transcription',
                                  recorded_at='2026-10-02T00:00:00Z')
        before = self.build(old)
        after = self.build(old, corrected)
        self.assertEqual(after['status'], 'VALIDATED_STRUCTURE')
        self.assertEqual(after['active_evidence_ids'], ['ev-2'])
        self.assertEqual(len(after['evidence_history']), 2)
        self.assertNotEqual(before['state_hash'], after['state_hash'])

    def test_unverified_correction_blocked(self):
        state = self.build(self.evidence(), self.evidence(
            evidence_id='ev-2', supersedes='ev-1', version=2,
            verification='UNVERIFIED', correction_reason='proposal',
            recorded_at='2026-10-02T00:00:00Z'))
        self.assertBlocked(state, 'INVALID_CORRECTION')

    def test_correction_retires_duplicate_imports_of_parent(self):
        original = self.evidence()
        duplicate = self.evidence(evidence_id='ev-duplicate',
                                  source_timestamp='2026-10-01T07:00:00+07:00')
        corrected = self.evidence(evidence_id='ev-corrected', supersedes='ev-1', version=2,
                                  value=13, correction_reason='Source correction',
                                  recorded_at='2026-10-02T00:00:00Z')
        state = self.build(original, duplicate, corrected)
        self.assertEqual(state['status'], 'VALIDATED_STRUCTURE')
        self.assertEqual(state['active_evidence_ids'], ['ev-corrected'])
        self.assertEqual(len(state['evidence_history']), 3)
        self.assertEqual(state['state_hash'], self.build(corrected, duplicate, original)['state_hash'])

    def test_correction_does_not_retire_different_source(self):
        corrected = self.evidence(evidence_id='ev-corrected', supersedes='ev-1', version=2,
                                  value=13, correction_reason='Source correction',
                                  recorded_at='2026-10-02T00:00:00Z')
        state = self.build(self.evidence(), self.evidence(evidence_id='ev-other', source_id='lab-2'),
                           corrected)
        self.assertBlocked(state, 'CONFLICTING_VERIFIED_SOURCES')
        self.assertIn('ev-other', state['active_evidence_ids'])

    def test_missing_provenance_not_defaulted_to_verified(self):
        record = self.evidence()
        del record['verification']
        self.assertBlocked(self.build(record), 'MISSING_PROVENANCE')

    def test_missing_verifier_blocked(self):
        self.assertBlocked(self.build(self.evidence(verified_by='')), 'MISSING_VERIFIER')

    def test_nonfinite_value_blocked(self):
        self.assertBlocked(self.build(self.evidence(value=float('nan'))), 'INVALID_EVIDENCE_ENCODING')

    def test_unknown_concept_blocked(self):
        self.assertBlocked(self.build(self.evidence(concept_id='unknown')), 'UNKNOWN_CANONICAL_CONCEPT')

    def test_naive_timestamp_blocked(self):
        self.assertBlocked(self.build(self.evidence(source_timestamp='2026-10-01')),
                           'INVALID_EVIDENCE_ENCODING')

    def test_missing_evidence_cannot_pass(self):
        self.assertBlocked(self.build(), 'NO_ACTIVE_EVIDENCE')

    def test_at01_input_order_stable_and_mutation_isolated(self):
        first = self.evidence()
        second = self.evidence(evidence_id='ev-2', source_id='lab-2',
                               source_timestamp='2026-10-02T00:00:00Z')
        original = deepcopy(first)
        state = self.build(first, second)
        self.assertEqual(state['state_hash'], self.build(second, first)['state_hash'])
        state['evidence_history'][0]['value'] = 99
        self.assertEqual(first, original)
