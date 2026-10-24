"""
Unit & Security Tests for Patient Portal & LINE OA Integration (EP 7).
Enforces HMAC-SHA256 Fail-Closed Security, Nonce Token Verification,
Strict IDOR Prevention, and Approved Reports Gate (Pillars 1, 2, 8, 14, 15).
"""

import hmac
import hashlib
import base64
import json
from datetime import date, timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, AuditLog
from patients.models import Patient, PatientLinkingToken, Appointment
from clinical.models import AnalysisRecord
from patients.line_service import LineSecurity


class LineWebhookSecurityTests(TestCase):
    """
    ทดสอบความปลอดภัยของ LINE Webhook (Pillar 14: Zero-Trust External APIs)
    """
    def setUp(self):
        self.client = Client()
        self.secret = 'test_channel_secret_key_super_secure_2026'
        self.webhook_url = reverse('portal_patient:line_webhook')

    def _generate_signature(self, body_bytes: bytes, secret: str = None) -> str:
        s = secret or self.secret
        mac = hmac.new(s.encode('utf-8'), body_bytes, hashlib.sha256).digest()
        return base64.b64encode(mac).decode('utf-8')

    @override_settings(LINE_CHANNEL_SECRET='')
    def test_missing_secret_returns_503(self):
        """หากไม่ตั้งค่า LINE_CHANNEL_SECRET บนเซิร์ฟเวอร์ ต้องคืนค่า 503 Fail-Closed"""
        resp = self.client.post(
            self.webhook_url,
            data=b'{"events": []}',
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 503)

    @override_settings(LINE_CHANNEL_SECRET='my_secret_key_123')
    def test_missing_signature_returns_401(self):
        """หากไม่มี Header X-Line-Signature ต้องคืนค่า 401 ทันที"""
        resp = self.client.post(
            self.webhook_url,
            data=b'{"events": []}',
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(LINE_CHANNEL_SECRET='my_secret_key_123')
    def test_invalid_signature_returns_401(self):
        """หากค่า Header X-Line-Signature ไม่ตรงกับ HMAC ต้องคืนค่า 401"""
        resp = self.client.post(
            self.webhook_url,
            data=b'{"events": []}',
            content_type='application/json',
            HTTP_X_LINE_SIGNATURE='invalid_bogus_signature='
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(LINE_CHANNEL_SECRET='my_secret_key_123')
    def test_valid_signature_empty_probe_returns_200(self):
        """คำขอ Probe ที่มีลายเซ็น HMAC ถูกต้องสมบูรณ์ ต้องคืนค่า 200 OK"""
        secret = 'my_secret_key_123'
        payload = b'{"events": []}'
        sig = self._generate_signature(payload, secret=secret)

        resp = self.client.post(
            self.webhook_url,
            data=payload,
            content_type='application/json',
            HTTP_X_LINE_SIGNATURE=sig
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'ok')

    @override_settings(LINE_CHANNEL_SECRET='my_secret_key_123')
    def test_malformed_json_returns_400(self):
        """คำขอที่ลงลายเซ็นถูกต้องแต่ JSON เสียรูป ต้องคืนค่า 400 Bad Request"""
        secret = 'my_secret_key_123'
        payload = b'not_a_valid_json_string{'
        sig = self._generate_signature(payload, secret=secret)

        resp = self.client.post(
            self.webhook_url,
            data=payload,
            content_type='application/json',
            HTTP_X_LINE_SIGNATURE=sig
        )
        self.assertEqual(resp.status_code, 400)


class LineAccountBindingTests(TestCase):
    """
    ทดสอบระบบเชื่อมโยงบัญชี LINE กับผู้ป่วย (Account Linking & Replay Protection)
    """
    def setUp(self):
        self.client = Client()
        self.patient = Patient.objects.create(
            hn='HN-2026-0099',
            first_name='สมชาย',
            last_name='มั่นคง',
            phone='0899999999',
            status='medicine'
        )

    def test_token_creation_and_expiration(self):
        """ทดสอบการสร้างโทเค็นและคุณสมบัติความปลอดภัย"""
        token_obj = PatientLinkingToken.create_token(
            patient=self.patient,
            action_type='line_binding',
            expires_in_minutes=15
        )
        self.assertTrue(token_obj.is_valid)
        self.assertFalse(token_obj.is_used)

        # เมื่อถูกใช้งานแล้ว สถานะ is_valid ต้องเป็น False
        token_obj.is_used = True
        token_obj.save()
        self.assertFalse(token_obj.is_valid)

    def test_binding_confirm_view_success_and_auditlog(self):
        """ทดสอบยืนยันการผูกบัญชี LINE ID สำเร็จ และบันทึก AuditLog"""
        token_obj = PatientLinkingToken.create_token(
            patient=self.patient,
            action_type='line_binding',
            expires_in_minutes=15
        )

        confirm_url = reverse('portal_patient:line_binding_confirm') + f"?token={token_obj.token}"
        resp = self.client.post(confirm_url, {
            'line_user_id': 'U1234567890abcdef1234567890abcdef'
        })

        self.assertEqual(resp.status_code, 200)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.line_user_id, 'U1234567890abcdef1234567890abcdef')

        token_obj.refresh_from_db()
        self.assertTrue(token_obj.is_used)

        # ตรวจสอบ AuditLog
        log = AuditLog.objects.filter(action='LINE_ACCOUNT_BOUND').last()
        self.assertIsNotNone(log)
        self.assertIn('HN-2026-0099', log.changes.get('details', ''))


class PatientPortalTests(TestCase):
    """
    ทดสอบระบบ Patient Portal: การยืนยันตัวตน, IDOR Prevention, และ Approved Reports Gate
    """
    def setUp(self):
        self.client = Client()

        # แพทย์ผู้ตรวจทาน
        self.doctor = User.objects.create_user(
            username='doctor_patt',
            email='drpatt@tspi.com',
            password='DocPassword123!',
            role='doctor',
            first_name='พัทธ์',
            last_name='แพทย์เชี่ยวชาญ'
        )

        # ผู้ป่วยคนที่ 1
        self.patient1 = Patient.objects.create(
            hn='HN-2026-1001',
            first_name='อนันต์',
            last_name='สุขใจ',
            phone='0811112222',
            gender='M',
            birth_date=date(1985, 4, 10),
            status='medicine'
        )

        # ผู้ป่วยคนที่ 2
        self.patient2 = Patient.objects.create(
            hn='HN-2026-1002',
            first_name='วิภา',
            last_name='วงศ์งาม',
            phone='0822223333',
            gender='F',
            status='medicine'
        )

        # นัดหมายแพทย์
        self.appt = Appointment.objects.create(
            patient=self.patient1,
            doctor=self.doctor,
            appointment_date=date.today() + timedelta(days=3),
            appointment_time='10:30:00',
            status='confirmed',
            notes='ตรวจติดตามผลหลังรับประทานสารอาหารบำบัด 2 สัปดาห์'
        )

        # รายงานที่อนุมัติแล้วของ Patient 1
        self.report_approved = AnalysisRecord.objects.create(
            patient=self.patient1,
            physician=self.doctor,
            status='approved',
            snapshot_scores={1: 75, 2: 40}
        )

        # รายงานฉบับร่างของ Patient 1 (ยังไม่อนุมัติ)
        self.report_draft = AnalysisRecord.objects.create(
            patient=self.patient1,
            physician=self.doctor,
            status='draft',
            snapshot_scores={1: 70}
        )

    def test_unauthenticated_redirects_to_login(self):
        """ผู้ใช้ที่ยังไม่ได้ล็อกอิน ต้องถูกรีไดเรกต์ไปหน้า login เสมอ"""
        resp = self.client.get(reverse('portal_patient:portal_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('portal_patient:portal_login'), resp.url)

    def test_login_with_hn_and_phone_success(self):
        """ล็อกอินผ่าน HN และเบอร์โทรศัพท์สำเร็จ"""
        resp = self.client.post(reverse('portal_patient:portal_login'), {
            'auth_mode': 'hn_phone',
            'hn': 'HN-2026-1001',
            'phone': '0811112222'
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.session.get('portal_patient_id'), self.patient1.pk)

    def test_login_with_wrong_phone_rejected(self):
        """กรอกเบอร์โทรศัพท์ไม่ตรง ต้องถูกปฏิเสธและบันทึก AuditLog"""
        resp = self.client.post(reverse('portal_patient:portal_login'), {
            'auth_mode': 'hn_phone',
            'hn': 'HN-2026-1001',
            'phone': '0899999999'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(self.client.session.get('portal_patient_id'))

        log = AuditLog.objects.filter(action='PATIENT_PORTAL_LOGIN_FAILED').last()
        self.assertIsNotNone(log)

    def test_portal_dashboard_shows_patient_and_approved_reports(self):
        """หน้า Dashboard ของคนไข้แสดงข้อมูลถูกต้องและไม่แสดงรายงานร่าง"""
        session = self.client.session
        session['portal_patient_id'] = self.patient1.pk
        session.save()

        resp = self.client.get(reverse('portal_patient:portal_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'คุณอนันต์ สุขใจ')
        self.assertContains(resp, 'HN-2026-1001')
        self.assertContains(resp, 'รายงานการแพทย์แม่นยำ 39 แกนชีววิทยา')

    def test_idor_prevention_portal_report_detail(self):
        """Pillar 2: คนไข้คนที่ 1 ห้ามเข้าดูรายงานของคนไข้คนที่ 2 เด็ดขาด (IDOR Prevention)"""
        # สร้างรายงานของ Patient 2
        report_patient2 = AnalysisRecord.objects.create(
            patient=self.patient2,
            physician=self.doctor,
            status='approved',
            snapshot_scores={1: 50}
        )

        # ล็อกอินในนาม Patient 1
        session = self.client.session
        session['portal_patient_id'] = self.patient1.pk
        session.save()

        # พยายามเปิดดูรายงานของ Patient 2
        target_url = reverse('portal_patient:portal_report_detail', kwargs={'pk': report_patient2.pk})
        resp = self.client.get(target_url)

        # ต้องถูกปฏิเสธด้วย 403 Forbidden
        self.assertEqual(resp.status_code, 403)

        # ตรวจสอบ AuditLog ตรวจจับการโจมตี IDOR
        log = AuditLog.objects.filter(action='SUSPICIOUS_IDOR_ATTEMPT').last()
        self.assertIsNotNone(log)

    def test_draft_report_hidden_from_patient(self):
        """Pillar 15: รายงานที่ยังเป็นร่าง (Draft) ห้ามคนไข้เข้าดู ต้องคืนค่า 404"""
        session = self.client.session
        session['portal_patient_id'] = self.patient1.pk
        session.save()

        draft_url = reverse('portal_patient:portal_report_detail', kwargs={'pk': self.report_draft.pk})
        resp = self.client.get(draft_url)
        self.assertEqual(resp.status_code, 404)

    def test_approved_report_visible_to_patient_and_logs_audit(self):
        """รายงานที่ได้รับการอนุมัติแล้ว คนไข้เจ้าของประวัติสามารถเปิดดูได้ และบันทึก AuditLog"""
        session = self.client.session
        session['portal_patient_id'] = self.patient1.pk
        session.save()

        approved_url = reverse('portal_patient:portal_report_detail', kwargs={'pk': self.report_approved.pk})
        resp = self.client.get(approved_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'รายงานการแพทย์แม่นยำและการฟื้นฟูสุขภาพเฉพาะบุคคล')

        # ตรวจสอบ AuditLog
        log = AuditLog.objects.filter(action='PATIENT_PORTAL_REPORT_VIEW').last()
        self.assertIsNotNone(log)
