from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from . import tests_safety_service as fixtures
from .analysis_inputs import prepare_analysis_inputs
from .models import SafetyAssessment
from .registry_governance import transition_registry
from .safety_history import read_safety_assessment, verify_safety_integrity
from .safety_service import record_safety_assessment, preview_safety


class SafetyHistoryTests(TestCase):
    def setUp(self):
        fixtures.SafetyPreviewTests.setUp(self)
        self.author.user_permissions.add(*Permission.objects.filter(content_type__app_label='patients',
            codename__in=['add_safetyassessment', 'view_safetyassessment']))
        self.author = User.objects.get(pk=self.author.pk)
        self.manifest = prepare_analysis_inputs(patient_id=self.patient.pk, actor=self.author,
            unit_registry_id=self.safety_units.pk, selection=self.selection)

    def record(self, **overrides):
        args = {'patient_id': self.patient.pk, 'actor': self.author, 'unit_registry_id': self.safety_units.pk,
                'selection': self.selection, 'policy_id': 'test-policy',
                'expected_manifest_hash': self.manifest['manifest_hash']}
        args.update(overrides)
        return record_safety_assessment(**args)

    def read(self, result):
        return read_safety_assessment(patient_id=self.patient.pk, actor=self.author,
                                     assessment_id=result['safety_assessment_id'])

    def test_snapshot_contains_original_inputs_and_policy(self):
        result = self.record()
        history = self.read(result)
        self.assertEqual(history['snapshot']['manifest'], self.manifest['manifest'])
        self.assertEqual(history['snapshot']['policy'], self.policy)
        self.assertEqual(history['replay']['status'], 'MATCH')
        self.assertTrue(history['historical_only'])
        self.assertFalse(history['clinical_use_authorized'])

    def test_stale_preflight_is_recorded_but_never_cleared(self):
        result = self.record(expected_manifest_hash='0' * 64)
        self.assertEqual(result['result']['safety_state'], 'INCOMPLETE')
        self.assertEqual(self.read(result)['replay']['status'], 'MATCH')

    def test_replay_uses_original_assessment_time(self):
        result = self.record()
        later = timezone.now() + timedelta(days=30)
        with patch('patients.safety_service.timezone.now', return_value=later):
            current = preview_safety(patient_id=self.patient.pk, actor=self.author,
                unit_registry_id=self.safety_units.pk, selection=self.selection, policy_id='test-policy')
            history = self.read(result)
        self.assertEqual(current['safety_state'], 'INCOMPLETE')
        self.assertEqual(history['snapshot']['result']['safety_state'], 'PARTIAL')
        self.assertEqual(history['replay']['status'], 'MATCH')

    def test_retirement_does_not_rewrite_history(self):
        result = self.record()
        transition_registry(registry_id=self.safety_registry.pk, actor=self.reviewer,
                            state='RETIRED', reason='Synthetic retirement')
        self.assertEqual(self.read(result)['replay']['status'], 'MATCH')
        with self.assertRaises(ValidationError):
            self.record()

    def test_history_mutation_detected(self):
        result = self.record()
        assessment = SafetyAssessment.objects.get(pk=result['safety_assessment_id'])
        assessment.snapshot['result']['safety_state'] = 'PASS'
        with self.assertRaises(ValidationError):
            verify_safety_integrity(assessment)

    def test_append_only_model(self):
        result = self.record()
        row = SafetyAssessment.objects.get(pk=result['safety_assessment_id'])
        with self.assertRaises(ValidationError):
            row.save()
        with self.assertRaises(ValidationError):
            SafetyAssessment.objects.filter(pk=row.pk).update(snapshot={})
        with self.assertRaises(ValidationError):
            row.delete()

    def test_write_failure_not_silently_ignored(self):
        with patch('patients.safety_service.SafetyAssessment.objects.create', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):
                self.record()
        self.assertFalse(SafetyAssessment.objects.exists())

    def test_permission_is_required_for_recording(self):
        with self.assertRaises(PermissionDenied):
            self.record(actor=self.reviewer)

    def test_api_creates_snapshot_not_clearance(self):
        client = APIClient()
        client.force_authenticate(self.author)
        response = client.post(f'/api/patients/{self.patient.pk}/safety-assessments/', {
            'unit_registry_id': str(self.safety_units.pk), 'selection': self.selection,
            'policy_id': 'test-policy', 'expected_manifest_hash': self.manifest['manifest_hash'],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['clinical_use_authorized'])
        path = f'/api/patients/{self.patient.pk}/safety-assessments/{response.data["safety_assessment_id"]}/'
        self.assertEqual(client.get(path).data['replay']['status'], 'MATCH')
        client.force_authenticate(self.reviewer)
        self.assertEqual(client.get(path).status_code, 403)
