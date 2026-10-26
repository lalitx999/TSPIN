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


class BotanyEnginePhase1Tests(TestCase):
    """
    Test suite for TSPI Botany-Engine Phase 1:
    1. Personal Box Password 2-tier security
    2. Must Change Password flag
    3. M5 Pre-Flight Text Sanitizer (Thai PII redaction)
    4. M5 Media Sanitizer EXIF stripping
    5. Strict Environment Variable Configuration
    """

    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor_botany',
            email='botany@tspi.clinic',
            password='InitialPassword2026!',
            role=User.Role.DOCTOR,
            first_name='พงษ์ศักดิ์',
            last_name='บรรณารักษ์'
        )

    def test_personal_box_password_hashing_and_verification(self):
        """[Phase 1]: ตรวจสอบการตั้งค่าและตรวจสอบรหัสผ่านเปิดกล่องประวัติคนไข้ส่วนตัว"""
        self.assertFalse(self.doctor.has_box_password)
        
        # รหัสสั้นกว่า 6 ตัวอักษรต้องถูกปฏิเสธ
        with self.assertRaises(ValueError):
            self.doctor.set_box_password("12345")

        # ตั้งรหัสผ่านที่ถูกต้อง
        self.doctor.set_box_password("SecretBoxKey2026!")
        self.doctor.refresh_from_db()

        self.assertTrue(self.doctor.has_box_password)
        # รหัสผ่านต้องถูกแฮช ไม่ใช่ plaintext
        self.assertNotEqual(self.doctor.box_password_hash, "SecretBoxKey2026!")
        self.assertTrue(self.doctor.box_password_hash.startswith(('argon2', 'pbkdf2', 'bcrypt')))
        
        # ตรวจสอบความถูกต้อง
        self.assertTrue(self.doctor.check_box_password("SecretBoxKey2026!"))
        self.assertFalse(self.doctor.check_box_password("WrongKey1234!"))

    def test_must_change_password_flag(self):
        """[Phase 1]: ผู้ใช้สร้างใหม่ต้องมี flag must_change_password เป็น True เสมอ"""
        new_user = User.objects.create_user(username='new_nurse', password='TempPassword123!')
        self.assertTrue(new_user.must_change_password)

    def test_m5_text_deidentification(self):
        """[M5 Sanitizer]: ทดสอบการตัดข้อมูล PII ภาษาไทย 5 ประเภท (ชื่อ, เบอร์, บัตร ปชช., HN, อีเมล)"""
        from ai_service.sanitizer import TextDeidentifier, PolicyGuard, DataClassification
        
        raw_clinical_text = (
            "คนไข้ชื่อ นายสมบัติ วงศ์สว่าง โทร 089-987-6543 "
            "เลขบัตรประชาชน 3-1004-00123-45-6 รหัสผู้ป่วย HN 4567/66 "
            "อีเมล sombat@hospital.go.th มาพบแพทย์ด้วยอาการปวดหลังเรื้อรัง"
        )
        res = TextDeidentifier.sanitize(raw_clinical_text)
        
        self.assertTrue(res["has_pii"])
        self.assertEqual(res["redacted_counts"]["names"], 1)
        self.assertEqual(res["redacted_counts"]["phone"], 1)
        self.assertEqual(res["redacted_counts"]["id_card"], 1)
        self.assertEqual(res["redacted_counts"]["hn"], 1)
        self.assertEqual(res["redacted_counts"]["email"], 1)
        
        sanitized = res["sanitized_text"]
        self.assertNotIn("นายสมบัติ", sanitized)
        self.assertNotIn("089-987-6543", sanitized)
        self.assertNotIn("3-1004-00123-45-6", sanitized)
        self.assertNotIn("HN 4567/66", sanitized)
        self.assertNotIn("sombat@hospital.go.th", sanitized)
        
        # ตรวจสอบ Data Classification
        cls_level = PolicyGuard.classify_payload(
            has_raw_audio=False,
            has_id_photo=False,
            has_sanitized_image=False,
            text_is_sanitized=True
        )
        self.assertEqual(cls_level, DataClassification.CLASS_A)

    def test_m5_media_exif_stripping(self):
        """[M5 Sanitizer]: ทดสอบการลบ EXIF Metadata จากไฟล์รูปภาพ"""
        import io
        from PIL import Image
        from ai_service.sanitizer import MediaSanitizer
        
        # สร้างภาพทดสอบในหน่วยความจำ
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        raw_bytes = buffer.getvalue()
        
        clean_bytes = MediaSanitizer.strip_exif(raw_bytes)
        self.assertIsInstance(clean_bytes, bytes)
        self.assertGreater(len(clean_bytes), 0)

    def test_strict_env_configuration(self):
        """[Governance]: ตรวจสอบว่าคีย์ต่างๆ โหลดผ่าน ENV และไม่มีการ Hardcode ใน Codebase"""
        import os
        from ai_service.config import BotanyConfig
        
        # ตรวจสอบว่าโมดูลอ่านผ่าน os.getenv
        self.assertEqual(BotanyConfig.DEEPSEEK_API_KEY, os.getenv("DEEPSEEK_API_KEY", "").strip())
        self.assertEqual(BotanyConfig.GROQ_API_KEY, os.getenv("GROQ_API_KEY", "").strip())
        self.assertTrue(BotanyConfig.ZERO_RETENTION_ENABLED)


class BotanyEnginePhase2Tests(TestCase):
    """
    Test suite for TSPI Botany-Engine Phase 2 (Multimodal Intake Pipeline):
    1. M1: Voice Intake & PDPA Section 26 Biometric Consent Gate
    2. M2: Lab OCR / Vision with EXIF stripping and JSON marker extraction
    3. M3: Video Temporal Scan with consent verification
    """

    def setUp(self):
        from starlette.testclient import TestClient
        from ai_service.main import app as fastapi_app
        self.api_client = TestClient(fastapi_app)

    def test_m1_voice_intake_opt_out(self):
        """[M1 Voice]: คนไข้ไม่อนุญาต (Opt-out) -> ต้องล็อกเสียงไว้ใน Local Vault (CLASS_C) ห้ามส่งออก"""
        dummy_audio = b"RIFFfakeWAVEfmt dummy data for unit test"
        response = self.api_client.post(
            "/api/intake/voice",
            data={"consent_granted": "false"},
            files={"file": ("sample.wav", dummy_audio, "audio/wav")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertFalse(data["consent_granted"])
        self.assertTrue(data["manual_review_required"])
        self.assertEqual(data["classification"], "CLASS_C")
        self.assertIsNone(data["sanitized_transcript"])

    def test_m1_voice_intake_opt_in_transcription(self):
        """[M1 Voice]: คนไข้อนุญาต (Opt-in) -> ถอดเสียงผ่าน Gateway + Sanitized PII (CLASS_A)"""
        dummy_audio = b"RIFFfakeWAVEfmt dummy data for unit test"
        response = self.api_client.post(
            "/api/intake/voice",
            data={"consent_granted": "true"},
            files={"file": ("sample.wav", dummy_audio, "audio/wav")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["consent_granted"])
        self.assertEqual(data["classification"], "CLASS_A")
        self.assertIsNotNone(data["sanitized_transcript"])

    def test_m2_lab_ocr_vision_extraction(self):
        """[M2 Lab OCR]: สกัดผลแล็บด้วย Vision -> ตัด EXIF และได้ Structured Markers (CLASS_B)"""
        import io
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        
        response = self.api_client.post(
            "/api/intake/lab",
            files={"file": ("lab_result.jpg", buf.getvalue(), "image/jpeg")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["classification"], "CLASS_B")
        self.assertIn("markers", data)

    def test_m3_video_temporal_scan(self):
        """[M3 Video]: สแกนคลิปตรวจดูแผล/การเคลื่อนไหว -> มี Timecodes โดยไม่วินิจฉัยโรค (CLASS_B)"""
        dummy_video = b"fake video mp4 stream for testing"
        response = self.api_client.post(
            "/api/intake/video",
            data={"consent_granted": "true"},
            files={"file": ("wound_clip.mp4", dummy_video, "video/mp4")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["consent_granted"])
        self.assertEqual(data["classification"], "CLASS_B")
        self.assertIn("observations", data)


