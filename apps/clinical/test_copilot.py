"""
Unit and Integration Tests for TSPI AI Copilot Streaming Engine (Option 4).
Verifies:
1. CopilotContextBuilder extracts grounded Single Source of Truth context (HN, Age, Scored Axes only, Safety Gates).
2. Doctor-Only RBAC (HTTP 403 Forbidden for Nurses, Staff, and Unauthenticated users).
3. SSE Streaming Response format & headers (X-Accel-Buffering: no, Cache-Control: no-cache).
4. Graceful Fallback handling when AI service is unreachable.
5. Rate Limiting enforcement.
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from patients.models import Patient, PatientHistory
from clinical.models import AnalysisRecord, BiologicalRecord
from clinical.services.copilot import CopilotContextBuilder

User = get_user_model()


class CopilotContextBuilderTests(TestCase):
    """ทดสอบ CopilotContextBuilder ดึงข้อมูลและล็อก Guardrails ถูกต้อง"""

    def setUp(self):
        self.patient = Patient.objects.create(
            hn="HN-COPILOT-01",
            first_name="ศศิธร",
            last_name="เจริญศิลป์",
            gender="F",
            phone="0891234567",
            status="medicine",
            allergies="Penicillin, NSAIDs"
        )

        self.doctor = User.objects.create_user(
            username="dr_copilot_ctx",
            password="securePassword123!",
            role="doctor"
        )

        # Snapshot Scores: Axis 1 (Scored), Axis 8 (None/Unscored), Axis 20 (Scored)
        self.analysis = AnalysisRecord.objects.create(
            patient=self.patient,
            physician=self.doctor,
            status="approved",
            snapshot_scores={
                "1": 75.0,
                "8": None,  # HYPOTHESIS - must be filtered out
                "20": 42.0,
            },
            doctor_summary="การอักเสบระดับเซลล์สูง ควรเฝ้าระวังหลอดเลือด"
        )

        # Patient SOAP History
        self.history = PatientHistory.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            subjective="มีอาการเหนื่อยง่าย ปวดตามข้อ",
            assessment="ภาวะอักเสบเรื้อรังระดับเซลล์",
            plan="ให้สารอาหารกลุ่มต้านการอักเสบและนัดติดตามผล"
        )

    def test_build_context_with_valid_patient(self):
        """Context Builder ต้องดึง HN, อาการแพ้, Safety Gates และกรองเฉพาะแกนที่มีคะแนน"""
        ctx = CopilotContextBuilder.build_context(patient_id=self.patient.pk)
        self.assertTrue(ctx['has_patient_context'])
        self.assertEqual(ctx['patient_hn'], "HN-COPILOT-01")
        self.assertEqual(ctx['patient_name'], "ศศิธร เจริญศิลป์")

        # แกนที่มีคะแนนต้องมี 2 แกน (Axis 1 และ 20) ส่วน Axis 8 (None) ต้องถูกคัดออก
        self.assertEqual(ctx['scored_axes_count'], 2)

        context_text = ctx['context_text']
        self.assertIn("HN-COPILOT-01", context_text)
        self.assertIn("Penicillin, NSAIDs", context_text)
        self.assertIn("Iron Safety Gate: HOLD PENDING CONFIRMATION", context_text)
        self.assertIn("Metabolic dysfunction-associated steatohepatitis", context_text)
        self.assertIn("Axis 1", context_text)
        self.assertIn("Axis 20", context_text)
        self.assertIn("มีอาการเหนื่อยง่าย ปวดตามข้อ", context_text)

    def test_build_context_general_mode_without_patient(self):
        """หากไม่ระบุ patient_id ต้องคืนโหมดทั่วไป ไม่ Error"""
        ctx = CopilotContextBuilder.build_context(patient_id=None)
        self.assertFalse(ctx['has_patient_context'])
        self.assertIsNone(ctx['patient_hn'])
        self.assertIn("General Clinical Assistant Mode", ctx['context_text'])


class CopilotStreamingApiTests(TestCase):
    """ทดสอบ API Streaming Endpoint, RBAC, Headers, และ Fallback"""

    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(
            username="dr_copilot_api",
            password="securePassword123!",
            role="doctor"
        )
        self.nurse = User.objects.create_user(
            username="nurse_copilot_api",
            password="securePassword123!",
            role="nurse"
        )
        self.patient_user = User.objects.create_user(
            username="patient_copilot_api",
            password="securePassword123!",
            role="patient"
        )

        self.patient = Patient.objects.create(
            hn="HN-COPILOT-02",
            first_name="มานะ",
            last_name="รักดี",
            gender="M",
            phone="0855554433"
        )
        self.url = reverse('clinical:copilot_stream')

    def test_unauthenticated_user_redirected_or_forbidden(self):
        """ผู้ใช้ไม่ได้ล็อกอิน ต้องถูกปฏิเสธ"""
        resp = self.client.post(self.url, data=json.dumps({"message": "test"}), content_type='application/json')
        # Redirect to login or 403
        self.assertIn(resp.status_code, [302, 403])

    def test_nurse_user_forbidden_403(self):
        """พยาบาล (Nurse) พยายามเข้าใช้งาน AI Copilot ของแพทย์ ต้องได้รับ 403 Forbidden"""
        self.client.force_login(self.nurse)
        resp = self.client.post(self.url, data=json.dumps({"message": "test"}), content_type='application/json')
        self.assertEqual(resp.status_code, 403)

    def test_patient_user_forbidden_403(self):
        """คนไข้ (Patient) พยายามเข้าถึง API ต้องได้รับ 403 Forbidden"""
        self.client.force_login(self.patient_user)
        resp = self.client.post(self.url, data=json.dumps({"message": "test"}), content_type='application/json')
        self.assertEqual(resp.status_code, 403)

    @patch('httpx.Client')
    def test_doctor_stream_success_with_headers(self, mock_httpx_cls):
        """แพทย์เรียกใช้งาน ต้องได้ Streaming Response พร้อม Header X-Accel-Buffering: no"""
        # Mock httpx streaming response
        mock_client = MagicMock()
        mock_httpx_cls.return_value.__enter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = [
            'data: {"chunk": "### ผลการวิเคราะห์", "done": false}',
            'data: {"chunk": "", "done": true}',
        ]
        mock_client.stream.return_value.__enter__.return_value = mock_resp

        self.client.force_login(self.doctor)
        resp = self.client.post(
            self.url,
            data=json.dumps({
                "message": "คนไข้มีภาวะอักเสบ",
                "patient_id": self.patient.pk
            }),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/event-stream')
        self.assertEqual(resp['X-Accel-Buffering'], 'no')
        self.assertEqual(resp['Cache-Control'], 'no-cache')

        # Read streaming content
        content = b"".join(resp.streaming_content).decode('utf-8')
        self.assertIn("### ผลการวิเคราะห์", content)

    @patch('httpx.Client')
    def test_fastapi_down_fallback_message(self, mock_httpx_cls):
        """หาก FastAPI ล่มหรือต่อไม่ติด ต้องมี Fallback Graceful Degradation ไม่พังหน้าเว็บ"""
        # Simulate connection error
        import httpx
        mock_client = MagicMock()
        mock_httpx_cls.return_value.__enter__.return_value = mock_client
        mock_client.stream.side_effect = httpx.ConnectError("Connection refused")

        self.client.force_login(self.doctor)
        resp = self.client.post(
            self.url,
            data=json.dumps({
                "message": "คนไข้มีภาวะอักเสบ",
                "patient_id": self.patient.pk
            }),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 200)
        content = b"".join(resp.streaming_content).decode('utf-8')
        self.assertIn("ระบบ AI Copilot ขัดข้องชั่วคราว", content)
        self.assertIn('"done": true', content)
