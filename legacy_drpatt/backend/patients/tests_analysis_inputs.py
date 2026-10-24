"""Canonical preflight integration, using synthetic records and no scoring/LLM calls."""
from datetime import date
from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from rest_framework.test import APIClient

from .analysis_inputs import prepare_analysis_inputs
from .evidence_service import append_evidence
from .models import AnalysisRecord, PatientBiologicalRecord, Patient
from .registry_governance import create_registry, transition_registry
from .unit_registry import create_unit_registry, transition_unit_registry


class AnalysisInputPreviewTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='preflight-author', is_staff=True)
        self.reviewer = User.objects.create_user(username='preflight-reviewer')
        self.author.user_permissions.add(*Permission.objects.filter(content_type__app_label='patients',
            codename__in=['add_canonicalunitregistry', 'add_governedregistry', 'add_clinicalevidencerevision',
                         'verify_clinicalevidence', 'view_governedregistry', 'view_clinicalevidencerevision']))
        self.reviewer.user_permissions.add(*Permission.objects.filter(content_type__app_label='patients',
            codename__in=['approve_unitregistry', 'approve_governedregistry']))
        self.unit = create_unit_registry(actor=self.author, version='test-v1', units={'C1': 'test-unit'})
        transition_unit_registry(registry_id=self.unit.pk, actor=self.reviewer,
                                 state='APPROVED', reason='Synthetic fixture')
        self.ontology = create_registry(actor=self.author, kind='ONTOLOGY', version='test-v1',
            content={'entries': [{'id': 'C1', 'label': 'Synthetic', 'source_ids': ['test-source']}], 'dependencies': {}})
        transition_registry(registry_id=self.ontology.pk, actor=self.reviewer,
                            state='APPROVED', reason='Synthetic fixture')
        self.patient = Patient.objects.create(hn='TEST-PREFLIGHT', first_name='Synthetic', last_name='Only',
                                              birth_date=date(1990, 1, 1), gender='M')
        self.source = {'patient_id': str(self.patient.pk), 'hn': self.patient.hn,
            'concept_id': 'C1', 'source_id': 'lab-1', 'source_type': 'LAB_MEASURED',
            'source_timestamp': '2026-10-01T00:00:00Z', 'consent_scope': 'CARE',
            'value': 12, 'unit': 'test-unit'}

    def append(self, **kwargs):
        return append_evidence(patient_id=self.patient.pk, actor=self.author, registry_id=self.unit.pk,
                               source=kwargs.pop('source', self.source), **kwargs)

    def preview(self, **kwargs):
        return prepare_analysis_inputs(patient_id=self.patient.pk, actor=self.author,
            unit_registry_id=self.unit.pk, selection={'ONTOLOGY': str(self.ontology.pk)}, **kwargs)

    def test_preview_reproducible_but_not_authorization(self):
        self.append(verify=True)
        first = self.preview()
        self.assertEqual(first['status'], 'INPUT_PREVIEW_VALIDATED')
        self.assertEqual(first, self.preview(expected_manifest_hash=first['manifest_hash']))
        self.assertFalse(first['clinical_use_authorized'])
        self.assertFalse(AnalysisRecord.objects.exists())
        self.assertFalse(PatientBiologicalRecord.objects.exists())

    def test_no_data_is_blocked(self):
        preview = self.preview()
        self.assertEqual(preview['status'], 'BLOCKED')
        self.assertIn('NO_ACTIVE_EVIDENCE', [issue['code'] for issue in preview['issues']])

    def test_unverified_evidence_blocks_preview(self):
        self.append()
        preview = self.preview()
        self.assertEqual(preview['status'], 'BLOCKED')
        self.assertIn('EVIDENCE_REQUIRES_VERIFICATION', [issue['code'] for issue in preview['issues']])

    def test_correction_invalidates_open_preview(self):
        old, _ = self.append(verify=True)
        first = self.preview()
        self.append(verify=True, supersedes=old.pk, correction_reason='Synthetic correction',
                    source={**self.source, 'value': 13})
        after = self.preview(expected_manifest_hash=first['manifest_hash'])
        self.assertEqual(after['status'], 'BLOCKED')
        self.assertNotEqual(after['manifest_hash'], first['manifest_hash'])
        self.assertIn('STALE_ANALYSIS_INPUT', [issue['code'] for issue in after['issues']])

    def test_demographic_edit_invalidates_open_preview(self):
        self.append(verify=True)
        first = self.preview()
        self.patient.first_name = 'Corrected synthetic name'
        self.patient.save()
        after = self.preview(expected_manifest_hash=first['manifest_hash'])
        self.assertEqual(after['status'], 'BLOCKED')
        self.assertNotEqual(after['manifest_hash'], first['manifest_hash'])

    def test_missing_demographic_fields_block_preview(self):
        self.append(verify=True)
        self.patient.birth_date = None
        self.patient.save()
        preview = self.preview()
        self.assertEqual(preview['status'], 'BLOCKED')
        self.assertIn('PATIENT_IDENTITY_INCOMPLETE', [issue['code'] for issue in preview['issues']])

    def test_evidence_concept_must_exist_in_ontology(self):
        self.append(verify=True)
        other = create_registry(actor=self.author, kind='ONTOLOGY', version='test-empty',
                                content={'entries': [], 'dependencies': {}})
        transition_registry(registry_id=other.pk, actor=self.reviewer, state='APPROVED', reason='Test')
        self.ontology = other
        preview = self.preview()
        self.assertEqual(preview['status'], 'BLOCKED')
        self.assertIn('EVIDENCE_CONCEPT_NOT_IN_ONTOLOGY', [issue['code'] for issue in preview['issues']])

    def test_service_checks_patient_scope_even_with_view_permissions(self):
        outsider = User.objects.create_user(username='unrelated-patient')
        outsider.user_permissions.add(*Permission.objects.filter(content_type__app_label='patients',
            codename__in=['view_clinicalevidencerevision', 'view_governedregistry']))
        with self.assertRaises(PermissionDenied):
            prepare_analysis_inputs(patient_id=self.patient.pk, actor=outsider,
                unit_registry_id=self.unit.pk, selection={'ONTOLOGY': str(self.ontology.pk)})

    def test_api_reports_stale_state_without_writing_analysis(self):
        self.append(verify=True)
        client = APIClient()
        client.force_authenticate(self.author)
        response = client.post(f'/api/patients/{self.patient.pk}/analysis-input-preview/',
            {'unit_registry_id': str(self.unit.pk), 'selection': {'ONTOLOGY': str(self.ontology.pk)},
             'expected_manifest_hash': '0' * 64}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data['clinical_use_authorized'])
        self.assertFalse(AnalysisRecord.objects.exists())

    def test_api_rejects_client_evidence_payload(self):
        client = APIClient()
        client.force_authenticate(self.author)
        response = client.post(f'/api/patients/{self.patient.pk}/analysis-input-preview/',
            {'unit_registry_id': str(self.unit.pk), 'selection': {'ONTOLOGY': str(self.ontology.pk)},
             'evidence': [{'verification': 'VERIFIED'}]}, format='json')
        self.assertEqual(response.status_code, 400)
