"""Synthetic staff auth regressions: role provisioning is never public sign-up."""
from unittest.mock import patch
from io import StringIO
import json
from django.core.management import call_command
from django.core.cache import cache
from django.test import override_settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from .models import AuditLog


class StaffAccountSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.staff = User.objects.create_user(username='synthetic-staff', email='staff@example.test',
            password='synthetic-password', is_staff=True)

    def tearDown(self):
        cache.clear()

    @override_settings(STAFF_LOGIN_ACCOUNT_LIMIT_PER_MINUTE=2)
    def test_account_limit_and_retry_after_do_not_depend_on_email_case(self):
        self.assertEqual(self.login(password='wrong').status_code, 401)
        self.assertEqual(self.login(email=self.staff.email.upper(), password='wrong').status_code, 401)
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
        self.assertFalse(AuditLog.objects.filter(action='DOCTOR_LOGIN_SUCCESS').exists())

    @override_settings(STAFF_LOGIN_IP_LIMIT_PER_MINUTE=2)
    def test_forged_forwarded_addresses_do_not_bypass_peer_limit(self):
        for i in range(2):
            self.assertEqual(self.client.post('/api/auth/doctor/login/',
                {'email': f'unknown{i}@example.test', 'password': 'wrong'},
                format='json', HTTP_X_FORWARDED_FOR=f'192.0.2.{i}').status_code, 401)
        response = self.client.post('/api/auth/doctor/login/',
            {'email': self.staff.email, 'password': 'synthetic-password'},
            format='json', HTTP_X_FORWARDED_FOR='192.0.2.99')
        self.assertEqual(response.status_code, 429)

    def test_cache_outage_fails_closed(self):
        with patch('django.core.cache.backends.locmem.LocMemCache.add', side_effect=RuntimeError):
            response = self.login()
        self.assertEqual(response.status_code, 429)

    def test_deployment_check_flags_unverified_local_cache(self):
        from accounts.checks import staff_login_deployment_checks
        self.assertIn('accounts.W001', [issue.id for issue in staff_login_deployment_checks(None)])

    @override_settings(STAFF_LOGIN_CACHE_ALIAS='missing', STAFF_LOGIN_ACCOUNT_LIMIT_PER_MINUTE=0)
    def test_deployment_check_rejects_missing_cache_and_disabled_limit(self):
        from accounts.checks import staff_login_deployment_checks
        codes = [issue.id for issue in staff_login_deployment_checks(None)]
        self.assertIn('accounts.E001', codes)
        self.assertIn('accounts.E002', codes)

    def login(self, **changes):
        return self.client.post('/api/auth/doctor/login/',
            {'email': self.staff.email, 'password': 'synthetic-password', **changes}, format='json')

    def test_public_registration_never_creates_staff_or_tokens(self):
        before = User.objects.count()
        for body in ({'name': 'Test', 'email': 'new@example.test', 'password': 'test'},
                     {'is_staff': True, 'is_superuser': True}, [], None):
            response = self.client.post('/api/auth/doctor/register/', body, format='json')
            self.assertEqual(response.status_code, 403)
            self.assertNotIn('tokens', response.data)
        self.assertEqual(User.objects.count(), before)

    def test_existing_staff_login_no_legacy_query_credential_logging_or_mutation(self):
        password_hash = self.staff.password
        with CaptureQueriesContext(connection) as queries, patch('builtins.print') as output:
            response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data['tokens'])
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertFalse(any('public.admin' in q['sql'] for q in queries))
        output.assert_not_called()
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.password, password_hash)
        self.assertEqual(AuditLog.objects.filter(action='DOCTOR_LOGIN_SUCCESS').count(), 1)

    def test_nonstaff_inactive_unknown_and_wrong_password_have_same_failure(self):
        baseline = self.login(password='wrong')
        self.assertEqual(baseline.status_code, 401)
        self.assertEqual(self.login(email='missing@example.test').data, baseline.data)
        for field in ('is_active', 'is_staff'):
            setattr(self.staff, field, False)
            self.staff.save()
            response = self.login()
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.data, baseline.data)
            setattr(self.staff, field, True)
        self.staff.save()
        self.assertFalse(AuditLog.objects.filter(action='DOCTOR_LOGIN_SUCCESS').exists())

    def test_ambiguous_email_never_selects_first_account(self):
        User.objects.create_user(username='other', email=self.staff.email.upper(),
                                 password='synthetic-password', is_staff=True)
        self.assertEqual(self.login().status_code, 401)

    def test_malformed_login_cannot_raise_server_errors(self):
        for body in ([], {'email': []}, {'email': self.staff.email, 'password': []},
                     {'email': self.staff.email, 'password': 'p', 'is_staff': True}):
            self.assertEqual(self.client.post('/api/auth/doctor/login/', body, format='json').status_code, 400)

    def test_profile_cannot_change_identity_or_privilege(self):
        self.client.force_authenticate(self.staff)
        for body in ({'email': 'other@example.test'}, {'is_staff': True}, {'is_superuser': True},
                     {'first_name': []}, {'password': 'new'}):
            self.assertEqual(self.client.patch('/api/auth/doctor/me/', body, format='json').status_code, 400)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, 'staff@example.test')
        self.assertEqual(self.client.patch('/api/auth/doctor/me/', {'first_name': 'Synthetic'}, format='json').status_code, 200)

    def test_inactive_force_authenticated_user_is_rejected(self):
        self.staff.is_active = False
        self.staff.save()
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get('/api/auth/doctor/me/').status_code, 403)

    def test_staff_inventory_is_read_only_and_never_discloses_credentials(self):
        AuditLog.objects.create(actor_id=self.staff.username, target_id=str(self.staff.pk),
                                action='DOCTOR_REGISTRATION_SUCCESS', layer='AUTH')
        original = User.objects.values().get(pk=self.staff.pk)
        output = StringIO()
        call_command('audit_staff_provisioning', stdout=output)
        report = json.loads(output.getvalue())
        self.assertTrue(report['read_only'])
        self.assertTrue(report['accounts'][0]['public_signup_recorded'])
        self.assertTrue(report['accounts'][0]['review_required'])
        self.assertFalse(report['accounts'][0]['provisioning_verified'])
        self.assertNotIn(self.staff.email, output.getvalue())
        self.assertNotIn(self.staff.password, output.getvalue())
        self.assertEqual(User.objects.values().get(pk=self.staff.pk), original)

    def test_absent_signup_audit_does_not_certify_staff(self):
        output = StringIO()
        call_command('audit_staff_provisioning', stdout=output)
        account = json.loads(output.getvalue())['accounts'][0]
        self.assertFalse(account['public_signup_recorded'])
        self.assertFalse(account['provisioning_verified'])
        self.assertTrue(account['review_required'])
