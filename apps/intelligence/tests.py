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


class KnowledgeRagBrainAndReviewIntegrationTests(TestCase):
    """ทดสอบระบบ Knowledge RAG (พร้อมเพิ่มความรู้ภายนอก), TSPI Brain Engine (4 Stages) และ Artifact Review"""

    def setUp(self):
        self.doctor = User.objects.create_user(
            username='dr_rag',
            email='dr_rag@tspi.com',
            password='Password12345!',
            role='doctor',
            first_name='นพ.คลังความรู้',
            last_name='แพทย์แม่นยำ'
        )
        self.patient = Patient.objects.create(
            hn='HN-BRAIN-01',
            first_name='สมหมาย',
            last_name='สายสมดุล',
            gender='M',
            phone='0888888888',
            allergies='Penicillin'
        )
        # กำหนดคะแนน 39 แกนให้เข้าเงื่อนไข RULE_001: AXIS_1 > 70 AND AXIS_19 > 60
        BiologicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            axis_1=82,
            axis_19=74,
            axis_5=68
        )
        self.client = Client()
        self.client.force_login(self.doctor)

    def test_knowledge_rag_canonical_search_and_external_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from intelligence.models import KnowledgeDocument

        # 1. ค้นหาจากฐานข้อมูลจริง (281 โมดูล)
        resp = self.client.get(reverse('patients:doctor_knowledge_rag') + '?q=Curcuma')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'TSPI-CURCUMA-01')

        # 2. เพิ่มองค์ความรู้ภายนอกพร้อมแนบไฟล์ .txt
        txt_file = SimpleUploadedFile('berberine_study.txt', b'Berberine activates AMPK and lowers HbA1c.', content_type='text/plain')
        add_resp = self.client.post(reverse('patients:doctor_knowledge_rag_add'), data={
            'title': 'Berberine AMPK Clinical Trial 2026',
            'category': 'research',
            'source_name': 'PubMed #998877',
            'content': 'Summary of metabolic insulin sensitivity benefits.',
            'tags': 'AMPK, Berberine, Axis 5',
            'doc_file': txt_file,
        })
        self.assertEqual(add_resp.status_code, 302)
        doc = KnowledgeDocument.objects.filter(title='Berberine AMPK Clinical Trial 2026').first()
        self.assertIsNotNone(doc)
        self.assertIn('Berberine activates AMPK', doc.content)

        # 3. ค้นหาความรู้ใหม่ที่เพิ่มเข้าไปต้องพบทันที
        search_ext = self.client.get(reverse('patients:doctor_knowledge_rag') + '?q=Berberine')
        self.assertEqual(search_ext.status_code, 200)
        self.assertContains(search_ext, 'Berberine AMPK Clinical Trial 2026')

        # 4. AI Physician Copilot fallback ดึงความรู้ใหม่นี้ไปอ้างอิงด้วย
        import json
        raw_sse = "".join(ClinicalCopilotEngine.generate_streaming_consultation(
            query="สรุปผลของ Berberine ต่อ AMPK",
            patient=self.patient
        ))
        decoded_text = "".join(
            json.loads(line[5:].strip()).get('chunk', '')
            for line in raw_sse.splitlines()
            if line.startswith('data:')
        )
        self.assertIn('Berberine AMPK Clinical Trial 2026', decoded_text)

        # 5. ลบ/ซ่อนองค์ความรู้ที่เพิ่มเองได้
        del_resp = self.client.post(reverse('patients:doctor_knowledge_rag_delete', args=[doc.pk]))
        self.assertEqual(del_resp.status_code, 302)
        doc.refresh_from_db()
        self.assertFalse(doc.is_active)

    def test_tspi_brain_traceability_and_artifact_dispatch_flow(self):
        # 1. หน้า TSPI Brain แสดงรอยแยกจริงและ RULE_001 ถูก Trigger (AXIS_1=82 > 70, AXIS_19=74 > 60)
        resp = self.client.get(reverse('patients:doctor_tspi_brain') + f'?patient_id={self.patient.pk}')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Neuroinflammation Alert')
        self.assertContains(resp, 'เข้าเงื่อนไข (Triggered)')

        # 2. ส่งแผนโมดูลจาก TSPI Brain เข้า Artifact Review Gate
        disp_resp = self.client.post(reverse('patients:doctor_tspi_brain_dispatch', args=[self.patient.pk]))
        self.assertEqual(disp_resp.status_code, 302)

        artifact = AgenticArtifact.objects.filter(patient=self.patient, artifact_type='therapeutic_plan').first()
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.status, 'pending')

        # 3. หน้า Artifact Review Gate แสดงผลเป็นโครงสร้างคลินิก (ไม่มี <pre> ดิบ)
        rev_resp = self.client.get(reverse('intelligence:artifact_review') + '?type=therapeutic_plan')
        self.assertEqual(rev_resp.status_code, 200)
        self.assertContains(rev_resp, self.patient.full_name)
        self.assertNotContains(rev_resp, '<pre class=')

        # 4. แพทย์กดอนุมัติเข้า EMR
        app_resp = self.client.post(reverse('intelligence:artifact_action', args=[artifact.pk]), data={
            'action': 'approve',
            'doctor_notes': 'อนุมัติแผนบำบัด Phase 1'
        })
        self.assertEqual(app_resp.status_code, 302)
        self.patient.refresh_from_db()
        self.assertTrue(len(self.patient.extra_data.get('approved_protocols', [])) >= 1)
