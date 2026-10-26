"""
Tests for AI Intake Chat Persistence, Fallback Form, Dynamic 39 Axes, and Digital Twin (Phase 3).
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from patients.models import Patient, PatientHistory
from clinical.models import BiologicalRecord

User = get_user_model()


class PatientAIIntakePersistenceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='pt_intake_test',
            email='pt_intake@example.com',
            password='TestPassword2026!',
            role=User.Role.PATIENT
        )
        self.patient = Patient.objects.create(
            hn='HN2610999',
            first_name='กิตติพงษ์',
            last_name='ใจรักษา',
            email='pt_intake@example.com',
            phone='0889998888',
            user=self.user
        )
        self.client.force_login(self.user)

    def test_ai_intake_page_renders_200(self):
        """หน้า AI Intake ต้องโหลดได้ปกติ (HTTP 200)"""
        response = self.client.get(reverse('portal_patient:patient_ai_intake'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal_patient/ai_intake.html')

    def test_ai_intake_chat_api_persists_symptoms_to_postgres(self):
        """Phase 3: ยิงข้อความอาการเข้า AI Intake Chat API ต้องบันทึกลง PostgreSQL จริง"""
        response = self.client.post(
            reverse('portal_patient:ai_intake_chat_api'),
            {'message': 'มีผื่นคันขึ้นที่ข้อศอกและรู้สึกแน่นท้องหลังทานอาหาร'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('ผื่นคัน', data['reply'])

        # Verify DB persistence
        self.patient.refresh_from_db()
        self.assertIn('ผื่นคัน', self.patient.chief_complaint)
        self.assertIn('intake_messages', self.patient.extra_data)
        self.assertEqual(len(self.patient.extra_data['intake_messages']), 2)
        self.assertEqual(self.patient.extra_data['intake_messages'][0]['sender'], 'user')
        self.assertEqual(self.patient.extra_data['intake_messages'][1]['sender'], 'ai')

    def test_ai_intake_chat_completion_creates_patient_history_note(self):
        """เมื่อบทสนทนาจบลง (Complete) ต้องสร้าง PatientHistory (SOAP Note) อัตโนมัติ"""
        response = self.client.post(
            reverse('portal_patient:ai_intake_chat_api'),
            {'message': 'บอกอาการครบแล้วครับ ขอบคุณครับ'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_completed'])

        # Check PatientHistory created
        history_entry = PatientHistory.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(history_entry)
        self.assertIn("AI Anamnesis Intake", history_entry.subjective)

    def test_ai_intake_fallback_api_saves_manual_symptoms(self):
        """Gotcha 4: ฟอร์ม Fallback กรอกอาการเอง ต้องบันทึกเข้า DB และสร้าง PatientHistory ทันที"""
        response = self.client.post(
            reverse('portal_patient:ai_intake_fallback_api'),
            {'manual_notes': 'ส่งอาการโดยตรง: มีอาการเวียนศีรษะและอ่อนเพลียเรื้อรัง'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        self.patient.refresh_from_db()
        self.assertIn('เวียนศีรษะ', self.patient.chief_complaint)
        history_entry = PatientHistory.objects.filter(patient=self.patient, subjective__contains='เวียนศีรษะ').first()
        self.assertIsNotNone(history_entry)


    def test_axes_result_view_renders_all_39_axes_from_database(self):
        """Phase 3: หน้าผลคะแนนต้องมีครบ 39 แกนชีววิทยา ดึงจาก DB โดยไม่มี Mock"""
        # Create BiologicalRecord with custom scores
        bio = BiologicalRecord.objects.create(
            patient=self.patient,
            axis_1=85, # Inflammatory Load (Critical)
            axis_15=72, # Liver Detox (Critical)
            axis_17=65, # Gut Barrier (Warning)
        )

        response = self.client.get(reverse('portal_patient:patient_axes_result'))
        self.assertEqual(response.status_code, 200)
        axes_data = response.context['axes_data']
        self.assertEqual(len(axes_data), 39)
        self.assertEqual(axes_data[0]['number'], 1)
        self.assertEqual(axes_data[0]['score'], 85)
        self.assertEqual(axes_data[0]['status'], 'critical')

    def test_digital_twin_computes_organ_alerts_from_real_scores(self):
        """Phase 3: Digital Twin คำนวณความผิดปกติของอวัยวะจากคะแนนจริง"""
        bio = BiologicalRecord.objects.create(
            patient=self.patient,
            axis_1=85, # Immune
            axis_15=78, # Liver
            axis_17=65, # Gut
        )

        response = self.client.get(reverse('portal_patient:patient_digital_twin'))
        self.assertEqual(response.status_code, 200)
        alerts = response.context['organ_alerts']
        organ_names = [a['organ'] for a in alerts]
        self.assertTrue(any('ตับ' in name for name in organ_names))
        self.assertTrue(any('ลำไส้' in name for name in organ_names))
        self.assertTrue(any('ภูมิคุ้มกัน' in name for name in organ_names))
