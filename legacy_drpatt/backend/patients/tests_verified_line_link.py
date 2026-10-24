from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Patient, VerifiedLineBinding, AuditLog
from .verified_line_link import verify_line_access_token, LineVerificationUnavailable


class VerifiedLineLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='0000000000001', password='synthetic-password')
        self.patient = Patient.objects.create(legacy_id='TEST-VERIFIED-LINE', hn='TEST-LINK',
            id_card=self.user.username, first_name='Synthetic', last_name='Only')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.line_id = 'U' + 'a' * 32
        self.environment = patch.dict('os.environ', {'LINE_LOGIN_CHANNEL_ID': 'synthetic-channel'})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def post(self, **extra):
        return self.client.post('/api/line/verified-link/', {'password': 'synthetic-password',
            'access_token': 'synthetic-token', **extra}, format='json')

    def provider(self, **changes):
        return patch('patients.verified_line_link._line_json', side_effect=[
            {'client_id': 'synthetic-channel', 'expires_in': 60, 'scope': 'profile openid', **changes},
            {'userId': self.line_id}])

    def test_valid_link_and_retry_are_idempotent(self):
        with self.provider():
            response = self.post()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'LINKED')
        with self.provider():
            self.assertEqual(self.post().data['status'], 'ALREADY_LINKED')
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.line_user_id, self.line_id)
        self.assertEqual(VerifiedLineBinding.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='LINE_VERIFIED_LINKED').count(), 1)

    def test_wrong_password_does_not_call_line(self):
        with patch('patients.verified_line_link._line_json') as provider:
            self.assertEqual(self.post(password='wrong').status_code, 403)
            provider.assert_not_called()

    def test_wrong_channel_expired_or_missing_scope_rejected(self):
        for changes in ({'client_id': 'other'}, {'expires_in': 0}, {'expires_in': True}, {'scope': 'openid'}):
            with self.subTest(changes=changes), self.provider(**changes):
                self.assertEqual(self.post().status_code, 409)
        self.assertFalse(VerifiedLineBinding.objects.exists())

    def test_client_cannot_choose_patient_or_line_identity(self):
        with patch('patients.verified_line_link._line_json') as provider:
            self.assertEqual(self.post(lineUserId=self.line_id).status_code, 400)
            self.assertEqual(self.post(patient_id=self.patient.pk).status_code, 400)
            provider.assert_not_called()

    def test_other_patient_binding_is_not_transferred(self):
        other = Patient.objects.create(legacy_id='OTHER', hn='OTHER', first_name='Synthetic',
                                       last_name='Other', line_user_id=self.line_id)
        with self.provider():
            self.assertEqual(self.post().status_code, 409)
        other.refresh_from_db()
        self.assertEqual(other.line_user_id, self.line_id)
        self.assertFalse(VerifiedLineBinding.objects.exists())

    def test_audit_failure_rolls_back_binding(self):
        with self.provider(), patch('patients.verified_line_link.AuditLog.objects.create', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.post()
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.line_user_id)
        self.assertFalse(VerifiedLineBinding.objects.exists())

    def test_missing_configuration_is_unavailable(self):
        with patch.dict('os.environ', {'LINE_LOGIN_CHANNEL_ID': ''}):
            self.assertEqual(self.post().status_code, 503)

    def test_unauthenticated_request_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertIn(self.post().status_code, (401, 403))

    def test_provider_outage_does_not_create_binding(self):
        with patch('patients.verified_line_link._line_json', side_effect=LineVerificationUnavailable):
            self.assertEqual(self.post().status_code, 503)
        self.assertFalse(VerifiedLineBinding.objects.exists())

    def test_generic_profile_update_cannot_bypass_verified_link(self):
        response = self.client.patch(f'/api/patients/{self.patient.pk}/',
            {'line_user_id': self.line_id}, format='json')
        self.assertEqual(response.status_code, 400)
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.line_user_id)
