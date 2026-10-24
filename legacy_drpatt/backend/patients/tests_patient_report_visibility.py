"""No real patient data. Test JSON paths that can bypass a PDF-only gate."""
from copy import deepcopy
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Patient
from .serializers import PatientSerializer


class PatientReportVisibilityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='synthetic-owner')
        self.staff = User.objects.create_user(username='synthetic-staff', is_staff=True)
        self.extra = {'generated_reports': [{'id': 'draft', 'report': 'SYNTHETIC PRIVATE DRAFT'}],
                      'latest_precision_insight': 'SYNTHETIC UNREVIEWED INSIGHT', 'weight': 60}
        self.patient = Patient.objects.create(legacy_id='TEST-VISIBILITY', hn='TEST-VISIBILITY',
            first_name='Synthetic', last_name='Only', id_card=self.owner.username,
            extra_data=deepcopy(self.extra))
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.path = f'/api/patients/{self.patient.pk}/'

    def test_owner_detail_hides_internal_reports_without_mutating_storage(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['extra_data'], {'weight': 60})
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.extra_data, self.extra)

    def test_owner_list_does_not_expose_drafts(self):
        response = self.client.get('/api/patients/?no_pagination=true')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('SYNTHETIC PRIVATE DRAFT', response.content.decode())
        self.assertNotIn('SYNTHETIC UNREVIEWED INSIGHT', response.content.decode())

    def test_staff_retains_review_access(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(self.path).data['extra_data'], self.extra)

    def test_missing_request_context_does_not_expose_internal_reports(self):
        self.assertEqual(PatientSerializer(self.patient).data['extra_data'], {'weight': 60})

    def test_owner_cannot_inject_or_erase_clinical_metadata(self):
        for value in ({}, {'generated_reports': [{'state': 'PATIENT_RELEASED'}]}):
            response = self.client.patch(self.path, {'extra_data': value}, format='json')
            self.assertEqual(response.status_code, 400)
            self.patient.refresh_from_db()
            self.assertEqual(self.patient.extra_data, self.extra)

    def test_other_patient_cannot_read_detail(self):
        outsider = User.objects.create_user(username='synthetic-outsider')
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(self.path).status_code, 404)

    def test_top_level_report_alias_cannot_bypass_metadata_guard(self):
        for field in ('generated_reports', 'latest_precision_insight'):
            response = self.client.patch(self.path, {field: 'injected'}, format='json')
            self.assertEqual(response.status_code, 400)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.extra_data, self.extra)
