from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Patient


class AccountIdentitySecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='0000000000001', email='shared@example.test', password='test-password')

    def patient(self, key, **kwargs):
        return Patient.objects.create(legacy_id=key, hn=key, first_name='Synthetic', last_name='Only', **kwargs)

    def login(self, **extra):
        return self.client.post('/api/auth/login/', {'citizenId': self.user.username,
            'password': 'test-password', **extra}, format='json')

    def test_registration_cannot_assert_line_identity(self):
        for field in ('line_user_id', 'lineUserId'):
            with self.subTest(field=field), patch('patients.views_line.push_line_message') as push:
                response = self.client.post('/api/auth/register/', {'IDcard': '0000000000002',
                    'password': 'test-password', field: 'U_UNVERIFIED'}, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data['code'], 'VERIFIED_ACCOUNT_LINK_REQUIRED')
                push.assert_not_called()
        self.assertFalse(User.objects.filter(username='0000000000002').exists())
        self.assertFalse(Patient.objects.exists())

    def test_matching_email_is_not_patient_ownership(self):
        self.patient('OTHER', id_card='0000000000003', email=self.user.email)
        self.assertEqual(self.login().status_code, 404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 404)

    def test_duplicate_patient_identity_does_not_choose_first(self):
        self.patient('FIRST', id_card=self.user.username)
        self.patient('SECOND', id_card=self.user.username)
        self.assertEqual(self.login().status_code, 404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 404)

    def test_unique_binding_preserves_normal_login(self):
        patient = self.patient('ONLY', id_card=self.user.username)
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['patient']['id'], patient.pk)
        self.assertIn('access', response.data['tokens'])

    def test_duplicate_email_login_is_rejected_but_id_login_works(self):
        self.patient('ONLY', id_card=self.user.username)
        User.objects.create_user(username='0000000000004', email=self.user.email, password='other-password')
        response = self.login(auth_method='email', email=self.user.email)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('tokens', response.data)
        self.assertEqual(self.login().status_code, 200)

    def test_repair_cannot_reset_existing_password_or_email(self):
        original_hash = self.user.password
        response = self.client.post('/api/auth/register/', {'IDcard': self.user.username,
            'password': 'attacker-password', 'email': 'attacker@example.test'}, format='json')
        self.assertEqual(response.status_code, 401)
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, original_hash)
        self.assertEqual(self.user.email, 'shared@example.test')
        self.assertFalse(Patient.objects.exists())

    def test_authenticated_repair_preserves_credentials_and_email(self):
        original_hash = self.user.password
        response = self.client.post('/api/auth/register/', {'IDcard': self.user.username,
            'password': 'test-password', 'email': 'ignored@example.test', 'fname': 'Synthetic'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, original_hash)
        self.assertEqual(self.user.email, 'shared@example.test')
        self.assertEqual(Patient.objects.get(id_card=self.user.username).email, self.user.email)

    def test_inactive_account_cannot_repair(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post('/api/auth/register/', {'IDcard': self.user.username,
            'password': 'test-password'}, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Patient.objects.exists())

    def test_client_selected_legacy_profile_cannot_be_claimed(self):
        patient = self.patient('LEGACY', id_card='0000000000009')
        for extra in ({'existing_doc_id': patient.pk}, {'is_activation_mode': True},
                      {'existing_doc_id': patient.pk, 'is_activation_mode': True}):
            response = self.client.post('/api/auth/register/', {'IDcard': '0000000000002',
                'password': 'test-password', **extra}, format='json')
            self.assertEqual(response.status_code, 403)
        patient.refresh_from_db()
        self.assertEqual(patient.id_card, '0000000000009')
        self.assertFalse(User.objects.filter(username='0000000000002').exists())

    def test_activation_does_not_disclose_profile_from_phone_and_name(self):
        with patch('accounts.views.Patient.objects.filter') as lookup:
            response = self.client.post('/api/auth/activate/',
                {'phone': '0000000000', 'name': 'Synthetic'}, format='json')
            self.assertEqual(response.status_code, 403)
            self.assertNotIn('patient', response.data)
            lookup.assert_not_called()

    def test_notification_registration_never_uses_shared_email_or_ambiguous_identity(self):
        other = self.patient('NOTIFICATION-OTHER', id_card='0000000000008', email=self.user.email)
        self.client.force_authenticate(self.user)
        path = '/api/auth/register-fcm-token/'
        self.assertEqual(self.client.post(path, {'fcm_token': 'synthetic-token'}, format='json').status_code, 404)
        other.refresh_from_db()
        self.assertNotIn('fcm_token', other.extra_data or {})
        self.patient('NOTIFICATION-A', id_card=self.user.username)
        self.patient('NOTIFICATION-B', id_card=self.user.username)
        self.assertEqual(self.client.post(path, {'fcm_token': 'synthetic-token'}, format='json').status_code, 404)

    def test_notification_registration_validates_type_and_preserves_unique_owner(self):
        patient = self.patient('NOTIFICATION-ONLY', id_card=self.user.username)
        self.client.force_authenticate(self.user)
        path = '/api/auth/register-fcm-token/'
        for token in ([], {}, None, ' ', 'x' * 4097):
            self.assertEqual(self.client.post(path, {'fcm_token': token}, format='json').status_code, 400)
        self.assertEqual(self.client.post(path, {'fcm_token': 'synthetic-token'}, format='json').status_code, 200)
        patient.refresh_from_db()
        self.assertEqual(patient.extra_data['fcm_token'], 'synthetic-token')
