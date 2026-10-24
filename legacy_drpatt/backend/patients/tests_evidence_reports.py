from copy import deepcopy
from unittest import TestCase

from .evidence_reports import compose_evidence_drafts, validate_evidence_drafts, EDITIONS


def synthetic_manifest():
    return {'identity': {'patient_id': 'synthetic'}, 'canonical_state': {
        'status': 'VALIDATED_STRUCTURE', 'active_evidence_ids': ['e1'], 'evidence_history': [{
            'evidence_id': 'e1', 'concept_id': 'test', 'value': 1, 'unit': 'test-unit',
            'source_id': 'source', 'source_type': 'LAB_MEASURED', 'source_timestamp': '2026-10-01T00:00:00Z',
            'verification': 'VERIFIED', 'version': 1}]}}


class EvidenceReportTests(TestCase):
    def test_three_editions_share_exact_facts(self):
        manifest = synthetic_manifest()
        packet = compose_evidence_drafts(manifest)
        self.assertEqual(set(packet['editions']), set(EDITIONS))
        self.assertEqual(packet['editions']['PHYSICIAN']['facts'], packet['editions']['PATIENT']['facts'])
        self.assertEqual(packet['editions']['PATIENT']['facts'], packet['editions']['MULTI_OMICS']['facts'])
        self.assertFalse(validate_evidence_drafts(packet, manifest)['clinical_use_authorized'])

    def test_unsupported_claim_rejected(self):
        manifest = synthetic_manifest()
        packet = compose_evidence_drafts(manifest)
        packet['editions']['PATIENT']['recommendations'] = ['Invented recommendation']
        with self.assertRaises(ValueError):
            validate_evidence_drafts(packet, manifest)

    def test_cross_edition_value_change_rejected(self):
        manifest = synthetic_manifest()
        packet = compose_evidence_drafts(manifest)
        packet['editions']['MULTI_OMICS']['facts'][0]['value'] = 99
        with self.assertRaises(ValueError):
            validate_evidence_drafts(packet, manifest)

    def test_boolean_cannot_replace_numeric_one(self):
        manifest = synthetic_manifest()
        packet = compose_evidence_drafts(manifest)
        packet['editions']['PHYSICIAN']['facts'][0]['value'] = True
        with self.assertRaises(ValueError):
            validate_evidence_drafts(packet, manifest)

    def test_input_and_editions_do_not_share_mutable_references(self):
        manifest = synthetic_manifest()
        old = deepcopy(manifest)
        packet = compose_evidence_drafts(manifest)
        packet['editions']['PATIENT']['facts'][0]['value'] = 99
        self.assertEqual(manifest, old)
        self.assertEqual(packet['editions']['PHYSICIAN']['facts'][0]['value'], 1)

    def test_blocked_manifest_cannot_be_composed(self):
        manifest = synthetic_manifest()
        manifest['canonical_state']['status'] = 'BLOCKED'
        with self.assertRaises(ValueError):
            compose_evidence_drafts(manifest)
