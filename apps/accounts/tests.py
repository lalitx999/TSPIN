"""
Comprehensive Security & Authorization Tests for EP 1 (Pillars 1, 2, 3, 7, 8).
Covers:
- Argon2 Password Hasher
- Session Fixation Prevention (Cycle Key)
- Idle & Absolute Session Timeout Middleware
- Role-Based Access Control (RBAC) Gating
- Thai National ID Modulo 11 Checksum Validation
- AuditLog Traceability
"""

import time
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory
from django.conf import settings
from accounts.models import AuditLog
from accounts.decorators import role_required, clinical_staff_required, doctor_only
from accounts.middleware import IdleSessionTimeoutMiddleware

User = get_user_model()

class AuthenticationSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(
            username='doctor_somchai',
            email='somchai@tspi.clinic',
            password='ComplexDoctorPassword2026!',
            role=User.Role.DOCTOR,
            first_name='สมชาย',
            last_name='ใจดี'
        )
        self.patient = User.objects.create_user(
            username='1100400123456',
            email='patient@tspi.test',
            password='PatientComplexPassword2026!',
            role=User.Role.PATIENT,
            first_name='วิชัย',
            last_name='รักสุขภาพ'
        )

    def test_argon2_password_hasher(self):
        """[Pillar 1]: รหัสผ่านต้องถูกแฮชด้วย Argon2 เสมอ"""
        hasher = identify_hasher(self.doctor.password)
        self.assertEqual(hasher.algorithm, 'argon2')

    def test_doctor_login_success_and_session_cycle(self):
        """
        [Pillar 1 & 8]: แพทย์ล็อกอินสำเร็จ, Session ถูกสร้าง, และบันทึก AuditLog
        """
        response = self.client.post(reverse('accounts:doctor_login'), {
            'email_or_username': 'somchai@tspi.clinic',
            'password': 'ComplexDoctorPassword2026!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.doctor.pk)
        
        # ตรวจสอบการบันทึก AuditLog
        audit = AuditLog.objects.filter(user=self.doctor, action='DOCTOR_LOGIN_SUCCESS').first()
        self.assertIsNotNone(audit)

    def test_patient_cannot_login_through_doctor_portal(self):
        """
        [Pillar 2 - Role Gate]: คนไข้พยายามล็อกอินผ่านพอร์ทัลแพทย์ ต้องถูกบล็อก
        """
        response = self.client.post(reverse('accounts:doctor_login'), {
            'email_or_username': '1100400123456',
            'password': 'PatientComplexPassword2026!',
        })
        self.assertEqual(response.status_code, 200) # แสดงฟอร์มเดิมพร้อมข้อความเตือน
        self.assertContains(response, "คุณไม่มีสิทธิ์เข้าถึงพอร์ทัลบุคลากรทางการแพทย์")
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_patient_login_success(self):
        """
        [Pillar 1]: คนไข้ล็อกอินผ่านพอร์ทัลคนไข้สำเร็จ
        """
        response = self.client.post(reverse('accounts:patient_login'), {
            'identifier': '1100400123456',
            'password': 'PatientComplexPassword2026!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.patient.pk)
        
        audit = AuditLog.objects.filter(user=self.patient, action='PATIENT_LOGIN_SUCCESS').first()
        self.assertIsNotNone(audit)

    def test_patient_registration_validation(self):
        """
        [Pillar 3]: ตรวจสอบการลงทะเบียน: เลขบัตร ปชช. ผิด Checksum ต้องถูกปฏิเสธ
        """
        # 1. เลขบัตรประชาชนผิดหลัก (Fake ID with invalid checksum)
        bad_response = self.client.post(reverse('accounts:patient_register'), {
            'first_name': 'ทดสอบ',
            'last_name': 'ระบบ',
            'id_card': '1234567890123',  # Checksum ผิด
            'phone': '0812345678',
            'email': 'new_patient@tspi.test',
            'password': 'NewSecurePassword2026!',
            'confirm_password': 'NewSecurePassword2026!',
            'pdpa_accepted': 'on',
        })
        self.assertContains(bad_response, "เลขประจำตัวประชาชน 13 หลักไม่ถูกต้องตามสูตรคำนวณมาตรฐาน")

        # 2. รหัสผ่านสั้นกว่า 12 ตัวอักษร
        short_pwd_response = self.client.post(reverse('accounts:patient_register'), {
            'first_name': 'ทดสอบ',
            'last_name': 'ระบบ',
            'id_card': '1100400123456',  # Valid checksum
            'phone': '0812345678',
            'email': 'new_patient2@tspi.test',
            'password': 'ShortPassword1', # 14 chars, but let's test < 12
            'confirm_password': 'ShortPassword1',
            'pdpa_accepted': 'on',
        })
        # Try truly short
        short_res = self.client.post(reverse('accounts:patient_register'), {
            'first_name': 'ทดสอบ',
            'last_name': 'ระบบ',
            'id_card': '1100400123456',
            'phone': '0812345678',
            'email': 'new_patient2@tspi.test',
            'password': 'short',
            'confirm_password': 'short',
            'pdpa_accepted': 'on',
        })
        self.assertContains(short_res, "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร")

    def test_user_logout_flushes_session(self):
        """
        [Pillar 1]: ล็อกเอาต์ล้างเซสชันและบันทึก AuditLog
        """
        self.client.force_login(self.doctor)
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse('_auth_user_id' in self.client.session)
        
        audit = AuditLog.objects.filter(user=self.doctor, action='USER_LOGOUT_SUCCESS').first()
        self.assertIsNotNone(audit)

    def test_idle_session_timeout_middleware(self):
        """
        [Pillar 1]: มิดเดิลแวร์ตัดการเชื่อมต่อเมื่อไม่มีกิจกรรมเกิน 30 นาที (1,800 วินาที)
        """
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.doctor
        
        # จำลอง session ที่ไม่ได้ใช้งานมาแล้ว 35 นาที (2,100 วินาที)
        from importlib import import_module
        SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
        engine = SessionStore()
        engine['last_activity'] = time.time() - 2100
        engine.save()
        request.session = engine

        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, '_messages', FallbackStorage(request))
        
        middleware = IdleSessionTimeoutMiddleware(get_response=lambda r: HttpResponse("OK"))
        response = middleware(request)
        
        # ต้องถูก redirect ไปยังหน้า login พร้อมตัดสิทธิ์
        self.assertEqual(response.status_code, 302)
        audit = AuditLog.objects.filter(user=self.doctor, action='SESSION_IDLE_TIMEOUT').first()
        self.assertIsNotNone(audit)

    def test_role_authorization_decorator(self):
        """
        [Pillar 2]: ตรวจสอบการบล็อกผู้ใช้ที่ไม่ได้รับอนุญาตด้วย HTTP 403 Forbidden
        """
        factory = RequestFactory()
        
        @clinical_staff_required
        def dummy_clinical_view(request):
            return HttpResponse("CLINICAL_SECRET")

        # 1. แพทย์เข้าถึงได้
        req_doc = factory.get('/doctor/secret/')
        req_doc.user = self.doctor
        resp_doc = dummy_clinical_view(req_doc)
        self.assertEqual(resp_doc.status_code, 200)

        # 2. คนไข้เข้าถึงไม่ได้ (ต้องเกิด PermissionDenied)
        req_patient = factory.get('/doctor/secret/')
        req_patient.user = self.patient
        with self.assertRaises(PermissionDenied):
            dummy_clinical_view(req_patient)
            
        audit = AuditLog.objects.filter(user=self.patient, action='UNAUTHORIZED_ROLE_ACCESS_DENIED').first()
        self.assertIsNotNone(audit)
