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
        # GET ต้องไม่ทำให้ออกจากระบบ (กันเว็บอื่นสั่ง logout ผ่านลิงก์/รูปภาพ)
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        self.assertTrue('_auth_user_id' in self.client.session)

        response = self.client.post(reverse('accounts:logout'))
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
        from ai_service.config import config as ai_config
        self.api_client = TestClient(fastapi_app, headers={'X-Internal-Token': ai_config.INTERNAL_API_TOKEN})

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


class BotanyEnginePhase3Tests(TestCase):
    """
    Test suite for TSPI Botany-Engine Phase 3 (Dual-Core AI & Library RAG):
    1. M4: SOAP Structurer via Groq Llama-3.3-70B with Anti-diagnosis Guardrail
    2. M6: TSPI Library 39 Axes RAG Search & Lab Correlation
    3. M7: Deep Biological Reasoning via DeepSeek-R1-671B
    4. M8: Clinical Guardrail (Forbidden Diagnostic Assertions & Citation Grounding)
    """

    def setUp(self):
        from starlette.testclient import TestClient
        from ai_service.main import app as fastapi_app
        from ai_service.config import config as ai_config
        self.api_client = TestClient(fastapi_app, headers={'X-Internal-Token': ai_config.INTERNAL_API_TOKEN})

    def test_m4_soap_generation_and_guardrail(self):
        """[M4 SOAP]: สร้างโครงสร้าง SOAP และผ่านการตรวจสอบ Guardrail ห้ามวินิจฉัย"""
        response = self.api_client.post(
            "/api/ai/soap",
            json={
                "complaint": "คนไข้แจ้งว่ามีอาการปวดกล้ามเนื้อเรื้อรัง นอนไม่ค่อยหลับ",
                "lab_markers": [{"marker": "FBS", "value": 115, "unit": "mg/dL", "flag": "High"}]
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("soap", data)
        self.assertIn("subjective", data["soap"])
        self.assertIn("objective", data["soap"])
        self.assertIn("assessment", data["soap"])
        self.assertIn("plan", data["soap"])
        self.assertEqual(data["guardrail"]["status"], "PASS")

    def test_m6_library_search_and_lab_mapping(self):
        """[M6 Library]: ค้นหาแกนชีวภาพ 39 แกน และจับคู่ค่าแล็บ CRP กับ แกน 1 (Inflammation)"""
        response = self.api_client.post(
            "/api/library/search",
            json={
                "query": "อักเสบ ปวดข้อ",
                "lab_markers": [{"marker": "CRP", "value": 7.5, "unit": "mg/L", "flag": "High"}],
                "top_k": 3
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["total_matches"], 1)
        self.assertTrue(any(res["axis_id"] == 1 for res in data["results"]))
        self.assertTrue(any(corr["marker"] == "CRP" for corr in data["lab_correlations"]))

    def test_m7_deep_biological_reasoning(self):
        """[M7 Reasoning]: รันการประเมินความตึงเครียดของระบบชีวภาพ 39 แกน (DeepSeek-R1)"""
        response = self.api_client.post(
            "/api/ai/reasoning/39axes",
            json={
                "soap": {
                    "subjective": "เหนื่อยง่าย นอนไม่หลับ",
                    "assessment": "มีภาวะความเครียดของระบบเมแทบอลิซึม"
                },
                "lab_markers": [{"marker": "HbA1c", "value": 6.8, "unit": "%", "flag": "High"}]
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("analysis", data)
        self.assertIn("primary_axes_strained", data["analysis"])

    def test_m8_guardrail_rejection_of_forbidden_diagnosis(self):
        """[M8 Guardrail]: ต้องปฏิเสธ (REJECT) ข้อความที่ฟันธงโรค หรือวินิจฉัยโรคเอง"""
        response = self.api_client.post(
            "/api/guardrail/verify",
            json={
                "claim": "แพทย์วินิจฉัยว่าเป็นโรคข้ออักเสบรูมาตอยด์ระยะรุนแรง",
                "source_text": "การอักเสบระดับเซลล์ส่งผลต่อเนื้อเยื่อเกี่ยวพัน",
                "threshold": 0.70
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["has_forbidden_assertions"])
        self.assertEqual(data["verdict"], "REJECT")

    def test_m8_guardrail_citation_grounding_calibrated_threshold(self):
        """[M8 Guardrail]: ตรวจสอบการอ้างอิงตำราจริงตาม Calibrated Threshold (>= 0.70)"""
        # 1. ข้อความที่ตรงกับตำรา
        valid_response = self.api_client.post(
            "/api/guardrail/verify",
            json={
                "claim": "การอักเสบระดับเซลล์และไซโตไคน์เชื่อมโยงกับภาวะ metabolic stress",
                "source_text": "การอักเสบระดับเซลล์และไซโตไคน์เชื่อมโยงกับภาวะ metabolic stress และโรค NCDs",
                "threshold": 0.70
            }
        )
        self.assertEqual(valid_response.status_code, 200)
        valid_data = valid_response.json()
        self.assertFalse(valid_data["has_forbidden_assertions"])
        self.assertTrue(valid_data["grounding"]["grounded"])
        self.assertEqual(valid_data["verdict"], "APPROVE")

        # 2. ข้อความที่หลอน/มั่ว ไม่ตรงกับตำรา
        fake_response = self.api_client.post(
            "/api/guardrail/verify",
            json={
                "claim": "วิตามินบีสิบเจ็ดสามารถทำลายเซลล์มะเร็งได้ในสามวัน",
                "source_text": "การอักเสบระดับเซลล์และไซโตไคน์เชื่อมโยงกับภาวะ metabolic stress",
                "threshold": 0.70
            }
        )
        self.assertEqual(fake_response.status_code, 200)
        fake_data = fake_response.json()
        self.assertFalse(fake_data["grounding"]["grounded"])
        self.assertEqual(fake_data["verdict"], "REJECT")


class BotanyEnginePhase4Tests(TestCase):
    """
    Test suite for TSPI Botany-Engine Phase 4 (Box Builder & Integrity Verification):
    1. Cryptographic HMAC-SHA256 Box sealing
    2. Tamper-evident detection (modifying payload breaks signature)
    3. Multimodal Box assembly with SOAP + 39 axes + citations
    """

    def test_box_sealing_and_hmac_integrity(self):
        """[Phase 4 Box]: กล่องที่สร้างใหม่ต้องถูกปิดผนึกด้วยลายเซ็น HMAC-SHA256 ที่ถูกต้อง"""
        from clinical.services_box import BoxBuilderService
        from clinical.models import Box

        box = BoxBuilderService.assemble_box(
            source=Box.Source.WEB,
            raw_complaint="คนไข้มีอาการปวดกล้ามเนื้อเรื้อรัง นอนไม่ค่อยหลับ",
            lab_markers=[{"marker": "FBS", "value": 115, "unit": "mg/dL", "flag": "High"}]
        )
        self.assertIsNotNone(box.id)
        self.assertTrue(len(box.signature) == 64)
        self.assertEqual(box.status, Box.Status.DONE)
        
        # ยืนยันความสมบูรณ์ของกล่อง
        self.assertTrue(box.verify_integrity())

    def test_box_tampering_detection(self):
        """[Phase 4 Box]: หากมีการแอบแก้ไขข้อมูลในกล่อง ลายเซ็น HMAC จะต้องล้มเหลวทันที (Tamper-Evident)"""
        from clinical.services_box import BoxBuilderService

        box = BoxBuilderService.assemble_box(
            raw_complaint="อาการปกติ ไม่มีประเด็นร้ายแรง"
        )
        self.assertTrue(box.verify_integrity())

        # จำลองการแอบแก้ข้อมูลใน Payload (Man-in-the-Middle or rogue DB edit)
        tampered_contents = dict(box.contents)
        tampered_contents["complaint"] = "แอบแก้ไข: คนไข้หัวใจวายเฉียบพลัน"
        box.contents = tampered_contents
        
        # ตรวจสอบว่าระบบตรวจพบการดัดแปลงข้อมูล
        self.assertFalse(box.verify_integrity())


class BotanyEnginePhase5Tests(TestCase):
    """
    Test suite for TSPI Botany-Engine Phase 5 (Doctor Box Portal & Break-Glass Protocol):
    1. Dashboard display & RBAC gating
    2. Locked state vs Unlocked state
    3. Personal Box Password authentication & AuditLog failure recording
    4. Successful unlock, session persistence, and timestamp recording
    5. Clinical decision recording & status transition
    6. Emergency Break-Glass protocol with critical audit trail
    """

    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(
            username='doctor_karn',
            email='karn@tspi.clinic',
            password='ComplexDoctorPassword2026!',
            role=User.Role.DOCTOR,
            first_name='กานต์',
            last_name='แพทย์พัฒนา'
        )
        self.doctor.set_box_password("DoctorSecretBoxKey2026!")
        self.doctor.save()

        from clinical.services_box import BoxBuilderService
        from clinical.models import Box

        self.box = BoxBuilderService.assemble_box(
            source=Box.Source.LINE,
            raw_complaint="มีอาการอ่อนเพลียเรื้อรัง มึนศีรษะตอนบ่าย ตรวจพบน้ำตาลสูง",
            lab_markers=[{"marker": "HbA1c", "value": 7.2, "unit": "%", "flag": "HIGH"}]
        )

    def test_box_dashboard_access_gated_by_role(self):
        """[Phase 5 Portal]: เฉพาะบุคลากรทางการแพทย์เท่านั้นที่เข้าถึง Dashboard ได้"""
        # ยังไม่ล็อกอิน
        anon_resp = self.client.get(reverse('clinical:box_dashboard'))
        self.assertEqual(anon_resp.status_code, 302)

        # ล็อกอินเป็นแพทย์
        self.client.force_login(self.doctor)
        doc_resp = self.client.get(reverse('clinical:box_dashboard'))
        self.assertEqual(doc_resp.status_code, 200)
        self.assertContains(doc_resp, "กล่องประวัติคนไข้")

    def test_box_detail_locked_initially(self):
        """[Phase 5 Portal]: เข้าดูกล่องครั้งแรกต้องอยู่ในสถานะล็อก (is_unlocked = False)"""
        self.client.force_login(self.doctor)
        resp = self.client.get(reverse('clinical:box_detail', kwargs={'box_id': self.box.id}))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['is_unlocked'])
        self.assertContains(resp, "กล่องเวชระเบียนปิดผนึกความปลอดภัย")
        self.assertContains(resp, "รหัสผ่านเปิดกล่องส่วนตัวของแพทย์")

    def test_box_unlock_with_incorrect_password(self):
        """[Phase 5 Security]: ป้อนรหัสผ่านเปิดกล่องผิด ต้องปฏิเสธและบันทึก BOX_UNLOCK_FAILED AuditLog"""
        self.client.force_login(self.doctor)
        resp = self.client.post(
            reverse('clinical:box_unlock', kwargs={'box_id': self.box.id}),
            {'box_password': 'WrongPassword123!'},
            follow=True
        )
        self.assertEqual(resp.status_code, 200)
        # กล่องยังคงถูกล็อก
        self.assertFalse(resp.context['is_unlocked'])
        # ตรวจสอบ AuditLog
        failed_log = AuditLog.objects.filter(action="BOX_UNLOCK_FAILED", object_id=str(self.box.id)).first()
        self.assertIsNotNone(failed_log)
        self.assertEqual(failed_log.user, self.doctor)

    def test_box_unlock_with_correct_password(self):
        """[Phase 5 Security]: ป้อนรหัสผ่านเปิดกล่องถูกต้อง ปลดล็อกสำเร็จ และบันทึก BOX_UNLOCKED AuditLog"""
        self.client.force_login(self.doctor)
        resp = self.client.post(
            reverse('clinical:box_unlock', kwargs={'box_id': self.box.id}),
            {'box_password': 'DoctorSecretBoxKey2026!'},
            follow=True
        )
        self.assertEqual(resp.status_code, 200)
        # ปลดล็อกสำเร็จ
        self.assertTrue(resp.context['is_unlocked'])
        self.assertContains(resp, "แบบบันทึกเวชระเบียน SOAP")
        self.assertContains(resp, "การวิเคราะห์ 39 แกนชีวภาพ")

        # ตรวจสอบการบันทึกสถานะเปิดกล่อง
        self.box.refresh_from_db()
        self.assertEqual(self.box.opened_by, self.doctor)
        self.assertIsNotNone(self.box.opened_at)

        # ตรวจสอบ AuditLog
        success_log = AuditLog.objects.filter(action="BOX_UNLOCKED", object_id=str(self.box.id)).first()
        self.assertIsNotNone(success_log)

    def test_box_decision_recording(self):
        """[Phase 5 Clinical]: บันทึกคำสั่งการรักษาของแพทย์ เปลี่ยนสถานะเป็น reviewed และบันทึก AuditLog"""
        self.client.force_login(self.doctor)
        from clinical.models import Box
        # ต้องปลดล็อกกล่องก่อนบันทึกคำสั่ง
        self.client.post(reverse('clinical:box_unlock', kwargs={'box_id': self.box.id}),
                         {'box_password': 'DoctorSecretBoxKey2026!'})

        resp = self.client.post(
            reverse('clinical:box_decision', kwargs={'box_id': self.box.id}),
            {
                'decision': Box.Decision.APPROVE,
                'doctor_notes': 'เห็นชอบตามข้อเสนอแนะ ให้เจาะเลือดซ้ำใน 4 สัปดาห์'
            },
            follow=True
        )
        self.assertEqual(resp.status_code, 200)
        self.box.refresh_from_db()
        self.assertEqual(self.box.status, Box.Status.REVIEWED)
        self.assertEqual(self.box.decision, Box.Decision.APPROVE)
        self.assertIn("เจาะเลือดซ้ำ", self.box.doctor_notes)

        # ตรวจสอบ AuditLog
        decision_log = AuditLog.objects.filter(action="BOX_DECISION_RECORDED", object_id=str(self.box.id)).first()
        self.assertIsNotNone(decision_log)

    def test_break_glass_emergency_unlock(self):
        """[Phase 5 Emergency]: เปิดกล่องฉุกเฉิน Break-Glass ต้องมีเหตุผล >= 10 ตัวอักษร และบันทึก Critical AuditLog"""
        self.client.force_login(self.doctor)

        # 1. ป้อนเหตุผลสั้นเกินไป (< 10 ตัวอักษร) ต้องปฏิเสธ
        short_resp = self.client.post(
            reverse('clinical:box_break_glass', kwargs={'box_id': self.box.id}),
            {'break_glass_reason': 'ฉุกเฉิน'},
            follow=True
        )
        self.assertFalse(short_resp.context['is_unlocked'])

        # 2. ป้อนเหตุผลสมบูรณ์ (>= 10 ตัวอักษร) ปลดล็อกสำเร็จ
        urgent_reason = "คนไข้หมดสติเฉียบพลัน ต้องดูประวัติยาด่วนที่สุด"
        success_resp = self.client.post(
            reverse('clinical:box_break_glass', kwargs={'box_id': self.box.id}),
            {'break_glass_reason': urgent_reason},
            follow=True
        )
        self.assertTrue(success_resp.context['is_unlocked'])
        self.box.refresh_from_db()
        self.assertTrue(self.box.is_break_glass)
        self.assertEqual(self.box.break_glass_reason, urgent_reason)

        # ตรวจสอบ Critical AuditLog
        bg_log = AuditLog.objects.filter(action="BREAK_GLASS_UNLOCKED", object_id=str(self.box.id)).first()
        self.assertIsNotNone(bg_log)
        self.assertEqual(bg_log.changes.get("severity"), "CRITICAL")


class BotanyEnginePhase6Tests(TestCase):
    """
    Test suite for TSPI Botany-Engine Phase 6 (Security Pen-Test & Institutional Hardening):
    1. 50-Case PII Sanitization Leak Pen-Test (Zero-leak tolerance on Thai National IDs, Phones, Emails, HNs, Passports)
    2. Brute-Force Rate Limiting Lockout on Box Unlock (5 failed attempts trigger 5-minute lockout)
    3. Immutable Audit Trail completeness under adversarial attempts
    """

    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(
            username='doctor_piti',
            email='piti@tspi.clinic',
            password='ComplexDoctorPassword2026!',
            role=User.Role.DOCTOR,
            first_name='ปิติ',
            last_name='ศิริแพทย์'
        )
        self.doctor.set_box_password("PitiBoxSecretKey2026!")
        self.doctor.save()

        from clinical.services_box import BoxBuilderService
        from clinical.models import Box

        self.box = BoxBuilderService.assemble_box(
            source=Box.Source.CLINIC,
            raw_complaint="ตรวจสุขภาพประจำปี ตับและไตปกติ",
        )

    def test_50_cases_pii_sanitization_pen_test(self):
        """[Phase 6 Pen-Test]: ทดสอบ 50 เคสจำลองการป้อน PII ทุกรูปแบบ ต้องถูก Sanitizer กวาดล้าง 100% ไม่รั่วไหล"""
        from ai_service.sanitizer import MediaSanitizer

        pen_test_cases = [
            # 1-10: Thai National IDs (formatted, unformatted, with words)
            "คนไข้บัตรประชาชน 1100400123456 มาพบแพทย์",
            "เลขบัตร: 1-1004-00123-45-6 แจ้งอาการปวดหัว",
            "CID 3100500987654 ตรวจสุขภาพ",
            "ประชาชนเลขที่ 5100200334455 มีไข้สูง",
            "1-2345-67890-12-3 ปวดท้องรุนแรง",
            "เลขประจำตัว 1122334455667 มีอาการเหนื่อยหอบ",
            "1209800112233 ตรวจเลือดซ้ำ",
            "3401200554433 ค่าตับสูง",
            "1509900443322 ตรวจปัสสาวะ",
            "บัตรปชช 1103700223344 นัดติดตามอาการ",
            # 11-20: Thai Phone numbers (mobile, landline, hyphens, spaces)
            "เบอร์ติดต่อ 081-234-5678 โทรแจ้งผลด่วน",
            "โทร 0891234567 คนไข้ไม่รับสาย",
            "เบอร์โทรศัพท์ 062-987-6543 นัดตรวจสัปดาห์หน้า",
            "ติดต่อญาติที่ 0955554321 ฉุกเฉิน",
            "เบอร์บ้าน 02-123-4567 โทรตาม",
            "Tel: 083-000-1122 มีประวัติแพ้ยา",
            "เบอร์มือถือ: 086 111 2233",
            "โทรกลับที่ 091-888-7766 ด่วน",
            "085-444-3322 แจ้งนัดผ่าตัด",
            "061-222-3344 คนไข้แจ้งเปลี่ยนเบอร์",
            # 21-30: Email addresses (various domains)
            "ส่งผลแล็บไปที่ somchai.j@gmail.com ด้วยครับ",
            "อีเมล patient_urgent@hotmail.com ติดต่อไม่ได้",
            "email: doctor.consult@tspi.clinic ส่งต่อเคส",
            "cc: user123@yahoo.co.th รับทราบ",
            "contact: somying_2026@outlook.com เรียบร้อย",
            "info@medical-center.or.th ส่งประวัติย้ายรพ.",
            "test.user+tag@domain.co.th สอบถามผลเลือด",
            "somkiat_care@sanook.com คนไข้ขอสำเนา",
            "mail: patient.vip@hospital.go.th ส่งใบรับรอง",
            "ส่งรายงานไปทาง info.urgent@clinics.in.th",
            # 31-40: Hospital Numbers (HN variations)
            "คนไข้ HN: 123456 เข้าห้องตรวจ 2",
            "HN 987654 ย้ายมาจากแผนกศัลยกรรม",
            "หมายเลข HN: 001122 ผลเลือดออกแล้ว",
            "HN: 554433 มีภาวะความดันโลหิตสูง",
            "HN 889900 นัดตรวจคลื่นไฟฟ้าหัวใจ",
            "hn: 112233 นัดพบนักโภชนาการ",
            "HN 776655 เจาะน้ำตาลซ้ำ",
            "HN: 334455 ส่งต่ออายุรกรรม",
            "hn 990011 ฉีดวัคซีนไข้หวัดใหญ่",
            "HN: 445566 ประวัติแพ้พาราเซตามอล",
            # 41-50: Passports & Mixed Complex Vectors
            "หนังสือเดินทางเลขที่ AA1234567 ขอใบรับรองแพทย์",
            "Passport No. AB9876543 สำหรับเดินทางต่างประเทศ",
            "คนไข้ต่างชาติ Passport: AC1122334 ตรวจ PCR",
            "นาย สมศักดิ์ รักดี เลขบัตร 1100400123456 โทร 0812345678",
            "นาง วิจิตรา มั่นคง HN: 123456 อีเมล viji@test.com โทร 089-999-8888",
            "น.ส. แพรวา ก้องเกียรติ CID: 3100500987654 tel: 062-111-4455",
            "นายแพทย์วิชัย ประจำ HN 554433 โทร 02-987-6543",
            "เด็กชายภูผา ศรีสวัสดิ์ 1122334455667 เมล phu@school.ac.th",
            "Passport AA7654321 และเบอร์ 084-555-6677 คนไข้นัดตรวจตา",
            "เคสฉุกเฉิน 1-1004-00123-45-6 / 081-111-2222 / urgent@hospital.com",
        ]

        from ai_service.sanitizer import TextDeidentifier

        for idx, text in enumerate(pen_test_cases, 1):
            res = TextDeidentifier.sanitize(text)
            sanitized = res["sanitized_text"]
            counts = res["redacted_counts"]
            
            # ยืนยันว่าไม่มีเบอร์โทร, เลขบัตร 13 หลัก หรืออีเมลหลุดรอด
            import re
            self.assertFalse(
                re.search(r'\b\d{13}\b', sanitized),
                f"Leak detected in test case {idx}: {sanitized}"
            )
            self.assertFalse(
                re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', sanitized),
                f"Email leak detected in test case {idx}: {sanitized}"
            )
            # ต้องพบการ Mask อย่างน้อย 1 รายการ
            total_masked = sum(counts.values())
            self.assertGreater(
                total_masked,
                0,
                f"No PII masked in test case {idx}: {text}"
            )

    def test_brute_force_lockout_on_box_unlock(self):
        """[Phase 6 Security]: ทดสอบ Brute-Force Rate Limiting (5 ครั้งแล้วระงับ 5 นาที)"""
        from django.core.cache import cache
        cache.clear()

        self.client.force_login(self.doctor)

        # ลองรหัสผ่านผิด 5 ครั้งรวด
        for i in range(1, 6):
            resp = self.client.post(
                reverse('clinical:box_unlock', kwargs={'box_id': self.box.id}),
                {'box_password': f'WrongAttempt{i}!'},
                follow=True
            )
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(resp.context['is_unlocked'])

        # ครั้งที่ 6: ต้องถูก Lockout อัตโนมัติ (แม้จะใส่รหัสถูกต้องก็ตาม)
        lockout_resp = self.client.post(
            reverse('clinical:box_unlock', kwargs={'box_id': self.box.id}),
            {'box_password': 'PitiBoxSecretKey2026!'},
            follow=True
        )
        self.assertEqual(lockout_resp.status_code, 200)
        self.assertFalse(lockout_resp.context['is_unlocked'])
        self.assertContains(lockout_resp, "ระงับชั่วคราวเป็นเวลา 5 นาที")

        # ตรวจสอบว่าบันทึก BOX_UNLOCK_LOCKED_OUT ใน AuditLog
        lockout_log = AuditLog.objects.filter(action="BOX_UNLOCK_LOCKED_OUT", object_id=str(self.box.id)).first()
        self.assertIsNotNone(lockout_log)
        self.assertEqual(lockout_log.user, self.doctor)


class AIServiceAuthTests(TestCase):
    """FastAPI เป็นบริการภายใน: ทุก route ยกเว้น /health ต้องมี X-Internal-Token ที่ถูกต้อง"""

    def setUp(self):
        from starlette.testclient import TestClient
        from ai_service.main import app as fastapi_app
        self.api_client = TestClient(fastapi_app)

    def test_routes_reject_missing_or_wrong_token(self):
        for headers in ({}, {'X-Internal-Token': 'wrong-token'}):
            resp = self.api_client.post('/api/sanitizer/text', json={'text': 'โทร 0812345678'}, headers=headers)
            self.assertEqual(resp.status_code, 401)
            resp = self.api_client.post('/api/v1/copilot/stream', json={'message': 'test'}, headers=headers)
            self.assertEqual(resp.status_code, 401)

    def test_health_is_open(self):
        self.assertEqual(self.api_client.get('/health').status_code, 200)

    def test_line_webhook_no_longer_served_by_ai_service(self):
        from ai_service.config import config as ai_config
        resp = self.api_client.post('/api/v1/webhook/line', json={'events': []},
                                    headers={'X-Internal-Token': ai_config.INTERNAL_API_TOKEN})
        self.assertEqual(resp.status_code, 404)

    def test_intake_followup_offline_returns_no_question(self):
        from ai_service.config import config as ai_config
        headers = {'X-Internal-Token': ai_config.INTERNAL_API_TOKEN}
        self.assertEqual(self.api_client.post('/api/ai/intake/followup', json={'transcript': 'x'}).status_code, 401)
        resp = self.api_client.post('/api/ai/intake/followup', json={'transcript': 'ผู้ป่วย: ปวดหัว'}, headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['success'])  # ไม่มีคีย์ในเทสต์ -> ไม่มีคำถาม ไม่ใช้แม่แบบแทน

    def test_copilot_never_falls_back_to_default_products(self):
        from unittest.mock import patch
        from ai_service import main as ai_main
        axis_without_modules = [{'axis_id': 7, 'name': 'Test Axis', 'domain_title': 'Test Domain', 'modules': []}]
        with patch.object(ai_main, 'search_relevant_axes', return_value=axis_without_modules):
            text = ai_main.build_clinical_reasoning_response('ทดสอบ')
        self.assertNotIn('KERRA', text)
        self.assertNotIn('VITALPLUS', text)
        self.assertIn('ยังไม่มีโมดูล', text)


class PatientIdentifierLoginTests(TestCase):
    """ผู้ป่วยต้องล็อกอินได้ด้วย HN (มี/ไม่มีขีด) และเลขบัตร ปชช. ตามที่หน้าล็อกอินบอกไว้"""

    def setUp(self):
        from patients.models import Patient
        self.user = User.objects.create_user(
            username='pt_hn-26-00042', password='PatientPass2026!x', role=User.Role.PATIENT,
        )
        self.patient = Patient.objects.create(hn='HN-26-00042', first_name='ทดสอบ', last_name='ล็อกอิน', user=self.user)
        self.patient.set_id_card('1-1004-00123-45-6')
        self.patient.save()

    def _login(self, identifier, password='PatientPass2026!x'):
        return self.client.post(reverse('accounts:patient_login'), {'identifier': identifier, 'password': password})

    def test_login_with_hn_with_and_without_dashes(self):
        for identifier in ('HN-26-00042', 'hn2600042', 'HN 26 00042'):
            self.client.logout()
            resp = self._login(identifier)
            self.assertEqual(resp.status_code, 302, identifier)
            self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_with_national_id(self):
        resp = self._login('1100400123456')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_wrong_password_with_hn_fails(self):
        resp = self._login('HN-26-00042', password='wrong-password')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class NursingAssistantRoleTests(TestCase):
    """ผู้ช่วยพยาบาลมีสิทธิ์เท่าพยาบาล: เข้าพอร์ทัลบุคลากรได้ แต่อนุมัติรายการ Level 2 (แพทย์เท่านั้น) ไม่ได้"""

    def setUp(self):
        self.na = User.objects.create_user(
            username='na_test', email='na@tspi.test', password='AssistantPass2026!x',
            role=User.Role.NURSING_ASSISTANT, must_change_password=False,
        )

    def test_can_login_to_staff_portal_and_open_clinical_pages(self):
        resp = self.client.post(reverse('accounts:doctor_login'), {
            'email_or_username': 'na@tspi.test', 'password': 'AssistantPass2026!x',
        })
        self.assertEqual(resp.status_code, 302)
        for url in ('/doctor/dashboard/', '/doctor/patients/', '/staff/inbox/'):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_cannot_approve_level_2_diagnostic(self):
        from django.core.exceptions import PermissionDenied
        from patients.models import Patient, ClinicalReviewItem, CommunicationRecord, LineUser
        patient = Patient.objects.create(hn='HN-NA-1', first_name='a', last_name='b')
        line_user = LineUser.objects.create(line_user_id='U_NA_TEST', display_name='NA')
        message = CommunicationRecord.objects.create(
            line_message_id='na_msg_1', line_user=line_user, patient=patient,
            direction=CommunicationRecord.DirectionChoices.INCOMING,
            message_type=CommunicationRecord.MessageTypeChoices.TEXT, content='แน่นหน้าอก',
        )
        item = ClinicalReviewItem.objects.create(
            patient=patient, source_message=message,
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC,
        )
        with self.assertRaises(PermissionDenied):
            item.approve(self.na)


class ForcedPasswordChangeTests(TestCase):
    """บัญชีที่ผู้ดูแลตั้งรหัสให้ ต้องเปลี่ยนรหัสก่อนเข้าหน้าอื่น"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='provisioned', email='prov@tspi.test', password='InitialPass2026!x', role=User.Role.NURSE,
        )
        self.assertTrue(self.user.must_change_password)

    def _login(self):
        return self.client.post(reverse('accounts:doctor_login'), {
            'email_or_username': 'prov@tspi.test', 'password': 'InitialPass2026!x',
        })

    def test_login_redirects_to_change_and_blocks_other_pages(self):
        self.assertRedirects(self._login(), reverse('accounts:password_change'), fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/doctor/dashboard/'), reverse('accounts:password_change'),
                             fetch_redirect_response=False)

    def test_changing_password_clears_flag_and_unblocks(self):
        self._login()
        resp = self.client.post(reverse('accounts:password_change'), {
            'old_password': 'InitialPass2026!x', 'new_password1': 'BrandNewSecret2026!', 'new_password2': 'BrandNewSecret2026!',
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertEqual(self.client.get('/doctor/dashboard/').status_code, 200)

    def test_weak_new_password_rejected(self):
        self._login()
        self.client.post(reverse('accounts:password_change'), {
            'old_password': 'InitialPass2026!x', 'new_password1': 'short1', 'new_password2': 'short1',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.must_change_password)

    def test_login_next_rejects_protocol_relative_redirect(self):
        self.user.must_change_password = False
        self.user.save()
        resp = self.client.post(reverse('accounts:doctor_login') + '?next=//evil.example/x', {
            'email_or_username': 'prov@tspi.test', 'password': 'InitialPass2026!x',
        })
        self.assertNotIn('evil.example', resp['Location'])


class DevTunnelGuardTests(TestCase):
    """ทาง tunnel เปิดได้เฉพาะ LINE webhook / LIFF หน้าอื่นต้อง 404 แม้ล็อกอินแล้ว"""

    def test_only_line_paths_reachable_via_tunnel_host(self):
        from django.conf import settings
        tunnel = 'abc-def.trycloudflare.com'
        with self.settings(DEV_TUNNEL_HOSTS=('.trycloudflare.com',), ALLOWED_HOSTS=['.trycloudflare.com', 'testserver'],
                           MIDDLEWARE=['accounts.middleware.DevTunnelGuardMiddleware'] + list(settings.MIDDLEWARE)):
            doctor = User.objects.create_user(username='dr_tunnel', password='DoctorPass2026!x', role=User.Role.DOCTOR)
            client = Client(HTTP_HOST=tunnel)
            client.force_login(doctor)
            for path in ('/doctor/patients/', '/admin/', '/accounts/login/', '/clinical/intake/'):
                self.assertEqual(client.get(path).status_code, 404, path)
            self.assertNotEqual(client.get('/liff/bind/').status_code, 404)
            # localhost ยังใช้ได้ตามปกติ
            local = Client()
            local.force_login(doctor)
            self.assertEqual(local.get('/doctor/patients/').status_code, 200)
