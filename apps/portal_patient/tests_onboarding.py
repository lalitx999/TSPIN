"""
Tests for Patient Onboarding Wizard & Identity Flow (Phase 2).
Verifies:
- Wizard renders HTTP 200
- Lookup with valid Thai ID returns masked name & masked ID (Zero unmasked leaks)
- Anti-leak verification (Generic 404 message for unknown IDs)
- Rate-limiting verification (5 lookups/min limit returns 429)
- New patient registration creates real Patient in PostgreSQL and logs in
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from patients.models import Patient
from accounts.models import AuditLog


class PatientOnboardingTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

        # Create an existing patient for lookup tests
        self.existing_patient = Patient(
            hn="HN2610001",
            first_name="สมชาย",
            last_name="สุขสมบูรณ์",
            phone="0819876543",
            email="somchai@example.com",
            gender="M"
        )
        self.existing_patient.set_id_card("1100400987654")
        self.existing_patient.save()

    def test_onboarding_wizard_renders_200(self):
        """หน้า Onboarding Wizard ต้องแสดงผลได้ปกติ (HTTP 200)"""
        response = self.client.get(reverse('portal_patient:onboarding'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal_patient/onboarding/wizard.html')
        self.assertContains(response, "Smart Patient Onboarding")

    def test_onboarding_lookup_existing_patient_returns_masked_data(self):
        """ค้นหาคนไข้เดิมด้วยเลข 13 หลัก ต้องได้ข้อมูลแบบ Masked เพื่อความปลอดภัยตาม PDPA"""
        response = self.client.post(
            reverse('portal_patient:onboarding_lookup_api'),
            {'nationality': 'TH', 'identifier': '1100400987654'},
            HTTP_X_FORWARDED_FOR='192.168.1.100'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['masked_name'], 'คุณ ส*** ส***')
        self.assertEqual(data['masked_id'], '1-xxxx-xxxxx-65-4')
        self.assertEqual(data['masked_phone'], '081-xxx-xx43')
        self.assertEqual(data['hn'], 'HN2610001')

        # Verify AuditLog was recorded
        log_entry = AuditLog.objects.filter(action='PATIENT_LOOKUP').first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.object_id, str(self.existing_patient.pk))

    def test_onboarding_lookup_not_found_returns_generic_anti_leak_message(self):
        """Gotcha 2: ค้นหาเลขบัตรที่ไม่พบ ห้ามตอบว่า 'ไม่พบเลขบัตรนี้' ต้องตอบข้อความกลางๆ"""
        response = self.client.post(
            reverse('portal_patient:onboarding_lookup_api'),
            {'nationality': 'TH', 'identifier': '9999999999999'},
            HTTP_X_FORWARDED_FOR='192.168.1.101'
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn("ไม่พบข้อมูลประวัติเวชระเบียน", data['message'])

    def test_onboarding_lookup_rate_limiting_blocks_after_5_attempts(self):
        """Gotcha 2: ยิงค้นหาเกิน 5 ครั้งต่อนาทีต่อ IP ต้องติด Rate Limit HTTP 429"""
        ip = '192.168.1.200'
        for i in range(5):
            resp = self.client.post(
                reverse('portal_patient:onboarding_lookup_api'),
                {'nationality': 'TH', 'identifier': f'110040000000{i}'},
                HTTP_X_FORWARDED_FOR=ip
            )
            # First 5 attempts return 404
            self.assertEqual(resp.status_code, 404)

        # 6th attempt should be blocked with 429
        blocked_resp = self.client.post(
            reverse('portal_patient:onboarding_lookup_api'),
            {'nationality': 'TH', 'identifier': '1100400000006'},
            HTTP_X_FORWARDED_FOR=ip
        )
        self.assertEqual(blocked_resp.status_code, 429)
        self.assertIn("คุณทำรายการเกินจำนวนครั้งที่กำหนด", blocked_resp.json()['message'])

    def test_onboarding_new_patient_registration_flow(self):
        """Gotcha 3: ลงทะเบียนคนไข้ใหม่ ต้องบันทึก Patient ลง PostgreSQL จริง และ Auto-login"""
        response = self.client.post(
            reverse('portal_patient:onboarding_new_patient_api'),
            {
                'first_name': 'วรรณพร',
                'last_name': 'ใจดี',
                'phone': '0891234567',
                'email': 'wannaporn@example.com',
                'birth_date': '1995-05-15',
                'gender': 'F',
                'nationality': 'TH',
                'id_card': '1234567890123',
                'password': 'SecurePatientPass2026!'
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['hn'].startswith('HN'))
        self.assertEqual(data['redirect_url'], '/portal/ai-intake/')

        # Verify database record exists
        created_patient = Patient.objects.filter(phone='0891234567').first()
        self.assertIsNotNone(created_patient)
        self.assertEqual(created_patient.first_name, 'วรรณพร')
        self.assertEqual(created_patient.last_name, 'ใจดี')
        self.assertIsNotNone(created_patient.user)
        self.assertTrue(created_patient.user.check_password('SecurePatientPass2026!'))
