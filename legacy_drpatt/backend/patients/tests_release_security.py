"""Regression tests for legacy self-attested physician authorization."""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AnalysisRecord, AnalysisReportRelease, Patient, PatientBiologicalRecord


class LegacyReleaseSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='synthetic-reviewer', is_staff=True)
        patient = Patient.objects.create(legacy_id='TEST-RELEASE-SECURITY', hn='TEST-RELEASE',
                                         first_name='Synthetic', last_name='Only')
        self.patient = patient
        source = PatientBiologicalRecord.objects.create(patient=patient)
        self.analysis = AnalysisRecord.objects.create(patient=patient, source_record=source,
            inputs_hash='synthetic-release', ledger={'scoring_contracts': {'patient_release_eligible': True}})
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.path = '/api/ai/report-release-transition/'

    def transition(self, state, **extra):
        return self.client.post(self.path, {'analysis_record_id': self.analysis.pk,
            'edition': 'PATIENT', 'target_state': state, **extra}, format='json')

    def test_draft_and_review_remain_available_but_flag_cannot_approve(self):
        self.assertEqual(self.transition('AI_DRAFT').status_code, 201)
        self.assertEqual(self.transition('PHYSICIAN_REVIEWED').status_code, 201)
        response = self.transition('PHYSICIAN_APPROVED', is_physician_signoff=True)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'VERIFIED_PHYSICIAN_SIGNOFF_REQUIRED')
        self.assertEqual(AnalysisReportRelease.objects.count(), 2)

    def test_admin_and_physician_group_are_not_licence_verification(self):
        self.user.is_superuser = True
        self.user.save()
        self.user.groups.add(Group.objects.create(name='Physician'))
        for state in ('PHYSICIAN_APPROVED', 'PATIENT_RELEASED'):
            self.assertEqual(self.transition(state, is_physician_signoff=True).status_code, 409)
        self.assertFalse(AnalysisReportRelease.objects.exists())

    def test_invalid_id_is_400_not_500(self):
        for value in ('TSPI-123', True, None, {}, [], '9' * 100):
            with self.subTest(value=value):
                self.assertEqual(self.transition('AI_DRAFT', analysis_record_id=value).status_code, 400)

    def test_nonstaff_cannot_create_review(self):
        self.user.is_staff = False
        self.user.save()
        self.assertEqual(self.transition('AI_DRAFT').status_code, 403)

    def test_repeated_transition_does_not_append_duplicate(self):
        self.assertEqual(self.transition('AI_DRAFT').status_code, 201)
        self.assertEqual(self.transition('AI_DRAFT').status_code, 400)
        self.assertEqual(AnalysisReportRelease.objects.count(), 1)

    def store_report(self, edition):
        self.patient.extra_data = {'generated_reports': [{'id': 'test-report', 'reportType': edition,
            'analysisRecordId': self.analysis.pk, 'report': []}]}
        self.patient.save()
        return f'/api/ai/patients/{self.patient.pk}/reports/test-report/pdf/'

    def test_other_authenticated_user_cannot_read_saved_pdf(self):
        path = self.store_report('physician')
        outsider = User.objects.create_user(username='synthetic-outsider')
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(path).status_code, 403)

    def test_owner_cannot_read_clinician_only_editions(self):
        owner = User.objects.create_user(username='synthetic-owner')
        self.patient.id_card = owner.username
        self.patient.save()
        self.client.force_authenticate(owner)
        for edition in ('physician', 'multi-omics'):
            self.assertEqual(self.client.get(self.store_report(edition)).status_code, 403)

    def test_legacy_released_status_does_not_authorize_patient_pdf(self):
        path = self.store_report('patient')
        AnalysisReportRelease.objects.create(analysis_record=self.analysis, edition='PATIENT',
                                             state='PATIENT_RELEASED', acted_by=self.user)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'VERIFIED_PHYSICIAN_SIGNOFF_REQUIRED')
        self.assertEqual(AnalysisReportRelease.objects.count(), 1)

    def test_nonclinical_user_cannot_generate_dossier(self):
        self.user.is_staff = False
        self.user.save()
        response = self.client.get(f'/api/ai/generate-clinical-pdf/?patient={self.patient.pk}')
        self.assertEqual(response.status_code, 403)

    def test_unknown_edition_cannot_bypass_release_check(self):
        self.assertEqual(self.client.get(self.store_report('PATIENT')).status_code, 400)
