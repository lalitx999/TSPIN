from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from . import tests_analysis_inputs as fixtures
from .evidence_service import append_evidence
from .registry_governance import create_registry, transition_registry
from .safety_service import preview_safety
from .tests_safety_contracts import synthetic_policy
from .unit_registry import create_unit_registry, transition_unit_registry


class SafetyPreviewTests(TestCase):
    def setUp(self):
        fixtures.AnalysisInputPreviewTests.setUp(self)
        self.policy = synthetic_policy()
        concepts = [r['concept_id'] for r in self.policy['requirements']]
        self.safety_units = create_unit_registry(actor=self.author, version='safety-test-units',
                                                 units={key: '' for key in concepts})
        transition_unit_registry(registry_id=self.safety_units.pk, actor=self.reviewer,
                                 state='APPROVED', reason='Synthetic test')
        self.safety_ontology = create_registry(actor=self.author, kind='ONTOLOGY', version='safety-test',
            content={'entries': [{'id': key, 'label': key, 'source_ids': ['synthetic-source']} for key in concepts],
                     'dependencies': {}})
        transition_registry(registry_id=self.safety_ontology.pk, actor=self.reviewer,
                            state='APPROVED', reason='Synthetic test')
        self.safety_registry = create_registry(actor=self.author, kind='SAFETY', version='safety-test',
            content={'entries': [{'id': 'test-policy', 'label': 'Synthetic policy',
                                 'source_ids': ['synthetic-source'], 'policy': self.policy}],
                     'dependencies': {'ONTOLOGY': {'id': str(self.safety_ontology.pk),
                                                  'content_hash': self.safety_ontology.content_hash}}})
        transition_registry(registry_id=self.safety_registry.pk, actor=self.reviewer,
                            state='APPROVED', reason='Synthetic test')
        self.selection = {'ONTOLOGY': str(self.safety_ontology.pk), 'SAFETY': str(self.safety_registry.pk)}
        for concept in concepts:
            append_evidence(patient_id=self.patient.pk, actor=self.author, registry_id=self.safety_units.pk,
                verify=True, source={**self.source, 'concept_id': concept, 'value': 'CLEAR', 'unit': '',
                                     'source_type': 'PHYSICIAN_OBSERVED', 'source_timestamp': timezone.now().isoformat()})

    def preview(self, **kwargs):
        return preview_safety(patient_id=self.patient.pk, actor=self.author, unit_registry_id=self.safety_units.pk,
                              selection=self.selection, policy_id='test-policy', **kwargs)

    def test_real_service_keeps_interaction_source_unavailable(self):
        result = self.preview()
        self.assertEqual(result['interaction_source_status'], 'UNAVAILABLE')
        self.assertEqual(result['safety_state'], 'PARTIAL')
        self.assertFalse(result['clinical_use_authorized'])

    def test_stale_manifest_does_not_become_clearance(self):
        result = self.preview(expected_manifest_hash='0' * 64)
        self.assertEqual(result['safety_state'], 'INCOMPLETE')
        self.assertIn('STALE_ANALYSIS_INPUT', [issue['code'] for issue in result['input_issues']])

    def test_retired_policy_is_rejected(self):
        transition_registry(registry_id=self.safety_registry.pk, actor=self.reviewer,
                            state='RETIRED', reason='Synthetic test retirement')
        with self.assertRaises(ValidationError):
            self.preview()

    def test_client_cannot_override_external_source_status(self):
        client = APIClient()
        client.force_authenticate(self.author)
        body = {'unit_registry_id': str(self.safety_units.pk), 'selection': self.selection,
                'policy_id': 'test-policy', 'interaction_source_status': 'AVAILABLE'}
        url = f'/api/patients/{self.patient.pk}/safety-preview/'
        self.assertEqual(client.post(url, body, format='json').status_code, 400)
        body.pop('interaction_source_status')
        response = client.post(url, body, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['clinical_use_authorized'])
