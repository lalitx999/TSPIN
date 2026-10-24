"""
Unit & Security Tests for AI Physician Assistant, Lab OCR, and Artifact Review Gate (EP 5).
Validates Deterministic Parsing, SSE Stream, RBAC 403, and Physician Approval Sign-off (Pillars 2, 8, 15).
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, AuditLog
from patients.models import Patient
from clinical.models import BiologicalRecord
from intelligence.models import AIConsultationSession, AgenticArtifact
from intelligence.services import DeterministicLabParser, ClinicalCopilotEngine, ClinicalSafetyChecker


class IntelligenceServicesTests(TestCase):
    def setUp(self):
        # Create Doctor
        self.doctor = User.objects.create_user(
            username='dr_ai',
            email='dr_ai@tspi.com',
            password='Password12345!',
            role='doctor',
            first_name='หมออัจฉริยะ',
            last_name='ปัญญา'
        )

        # Create Patient user
        self.patient_user = User.objects.create_user(
            username='pt_ai',
            email='pt_ai@tspi.com',
            password='Password12345!',
            role='patient',
            first_name='คนไข้',
            last_name='ทดสอบแล็บ'
        )

        # Create Patient Record
        self.patient = Patient.objects.create(
            hn='HN-AI-001',
            first_name='กิตติ',
            last_name='รักษาดี',
            gender='M',
            phone='0877777777',
            allergies='Sulfa, Aspirin'
        )

        self.client = Client()

    def test_deterministic_lab_parser(self):
        """ทดสอบการสกัดค่าแล็บอัตโนมัติและเชื่อมโยงสู่แกนชีวภาพ (Deterministic Lab OCR)"""
        lab_text = """
        Laboratory Test Results:
        Fasting Blood Sugar: 135 mg/dL
        HbA1c: 7.2 %
        hs-CRP: 4.5 mg/L
        Total Cholesterol: 260 mg/dL
        SGPT: 55 U/L
        """
        result = DeterministicLabParser.parse_text(lab_text)
        biomarkers = result['extracted_biomarkers']

        # ตรวจสอบค่าที่สกัดได้
        self.assertEqual(biomarkers['fbs']['value'], 135.0)
        self.assertTrue(biomarkers['fbs']['is_abnormal'])
        self.assertEqual(biomarkers['fbs']['target_axis'], 5)

        self.assertEqual(biomarkers['crp']['value'], 4.5)
        self.assertTrue(biomarkers['crp']['is_abnormal'])
        self.assertEqual(biomarkers['crp']['target_axis'], 1)

        # ตรวจสอบแกนเป้าหมายที่ได้รับผลกระทบ
        affected_scores = result['affected_axes_scores']
        self.assertIn(5, affected_scores)  # Axis 5
        self.assertIn(1, affected_scores)  # Axis 1
        self.assertGreaterEqual(affected_scores[5], 60)

    def test_safety_checker_flags_allergies_and_critical_scores(self):
        """Pillar 15: ตรวจสอบ Safety Boundary ตรวจจับการแพ้ยาและคะแนนวิกฤต"""
        proposed_data = {
            'affected_axes_scores': {1: 90, 5: 65}
        }
        safety = ClinicalSafetyChecker.verify_safety(self.patient, proposed_data)
        flags = safety['flags']

        # ต้องมี Allergy Alert
        self.assertTrue(any(f['type'] == 'ALLERGY_ALERT' for f in flags))
        # ต้องมี Critical Axis Dysfunction สำหรับ Axis 1 (score 90)
        self.assertTrue(any(f['type'] == 'CRITICAL_AXIS_DYSFUNCTION' for f in flags))

    def test_streaming_copilot_generator(self):
        """ทดสอบการสร้างคำปรึกษาแบบ Streaming SSE (ไม่มี error และมีเนื้อหาคำเตือน)"""
        generator = ClinicalCopilotEngine.generate_streaming_consultation(
            query="วิเคราะห์ความเสี่ยงเบาหวานและการอักเสบ",
            patient=self.patient
        )
        chunks = list(generator)
        self.assertTrue(len(chunks) > 0)
        full_text = "".join(chunks)
        self.assertIn("AI Clinical Copilot", full_text)
        self.assertIn("Pillar 15", full_text)

    def test_rbac_patient_blocked_with_403(self):
        """Pillar 2: คนไข้ทั่วไปต้องถูกบล็อกด้วย 403 Forbidden บนเครื่องมือ AI ทางการแพทย์"""
        self.client.force_login(self.patient_user)

        resp = self.client.get(reverse('intelligence:ai_physician'))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get(reverse('intelligence:lab_ocr'))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get(reverse('intelligence:artifact_review'))
        self.assertEqual(resp.status_code, 403)

    def test_doctor_ai_consultation_and_auditlog(self):
        """Pillar 8: แพทย์เข้าใช้ AI Physician ได้ 200 OK และระบบบันทึก AuditLog"""
        self.client.force_login(self.doctor)

        url = reverse('intelligence:ai_physician') + f'?patient_id={self.patient.pk}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "กิตติ รักษาดี")

        # ตรวจสอบ AuditLog
        audit = AuditLog.objects.filter(
            action="AI_PHYSICIAN_VIEW",
            user=self.doctor
        ).first()
        self.assertIsNotNone(audit)

    def test_artifact_review_approval_workflow(self):
        """Pillar 15: ตรวจสอบกระบวนการอนุมัติ Artifact และการนำคะแนนเข้าสู่ EMR จริง"""
        self.client.force_login(self.doctor)

        # 1. สร้าง Pending Artifact
        artifact = AgenticArtifact.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            artifact_type='lab_extraction',
            title='ผลตรวจแล็บเบาหวาน',
            proposed_data={'affected_axes_scores': {1: 85, 5: 80}},
            status='pending'
        )

        # 2. แพทย์กดอนุมัติ (Approve)
        action_url = reverse('intelligence:artifact_action', args=[artifact.pk])
        resp = self.client.post(action_url, data={'action': 'approve', 'doctor_notes': 'ยืนยันผลแล็บตรงกับคลินิก'})
        self.assertEqual(resp.status_code, 302)  # Redirect กลับหน้า Review

        # 3. ตรวจสอบสถานะ Artifact
        artifact.refresh_from_db()
        self.assertEqual(artifact.status, 'approved')
        self.assertEqual(artifact.doctor, self.doctor)

        # 4. ตรวจสอบว่าคะแนนถูกอัปเดตเข้า BiologicalRecord ของคนไข้จริง
        bio_rec = self.patient.biological_records.first()
        self.assertIsNotNone(bio_rec)
        self.assertEqual(bio_rec.axis_1, 85)
        self.assertEqual(bio_rec.axis_5, 80)

        # 5. ตรวจสอบ AuditLog
        audit = AuditLog.objects.filter(
            action="ARTIFACT_APPROVED_BY_PHYSICIAN",
            user=self.doctor,
            object_id=str(artifact.pk)
        ).first()
        self.assertIsNotNone(audit)
