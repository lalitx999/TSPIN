"""
Unit & Security Tests for TSPI 39 Biological Axes Framework & Visualizer (EP 4).
Validates Ontologies, Deterministic Domain Scoring, RBAC 403, and AuditLog Trail (Pillars 2, 8).
"""

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, AuditLog
from patients.models import Patient
from clinical.models import BiologicalRecord, AnalysisRecord
from clinical.engine import TspiClinicalEngine


class ClinicalAxesEngineTests(TestCase):
    def setUp(self):
        # Create Doctor user
        self.doctor = User.objects.create_user(
            username='dr_axes',
            email='dr_axes@tspi.com',
            password='Password12345!',
            role='doctor',
            first_name='หมอวิชาญ',
            last_name='ชำนาญการ'
        )

        # Create Patient user (non-clinical)
        self.patient_user = User.objects.create_user(
            username='pt_axes',
            email='pt_axes@tspi.com',
            password='Password12345!',
            role='patient',
            first_name='คนไข้ทดสอบ',
            last_name='ระบบ'
        )

        # Create Patient Record
        self.patient = Patient.objects.create(
            hn='HN-AXES-001',
            first_name='วีระ',
            last_name='กล้าหาญ',
            gender='M',
            phone='0899999999'
        )

        self.client = Client()

    def test_engine_loads_all_39_axes_and_12_domains(self):
        """ทดสอบ Engine โหลดข้อมูลครบ 39 แกน 12 โดเมน และนิยามแกน 11, 12 ถูกต้องตามหลังบ้าน"""
        all_axes = TspiClinicalEngine.get_all_axes()
        self.assertEqual(len(all_axes), 39)

        domains = TspiClinicalEngine.get_domains_with_axes()
        self.assertEqual(len(domains), 12)

        # ตรวจสอบ Single Source of Truth: Axis 11 และ Axis 12
        axis_11 = TspiClinicalEngine.get_axis_by_id(11)
        self.assertIsNotNone(axis_11)
        self.assertIn("DNA Repair", axis_11['name'])

        axis_12 = TspiClinicalEngine.get_axis_by_id(12)
        self.assertIsNotNone(axis_12)
        self.assertIn("Epigenetic", axis_12['name'])

    def test_biological_record_model_methods(self):
        """ทดสอบ Model BiologicalRecord: to_radar_list() และ get_dysfunctional_axes()"""
        record = BiologicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            is_baseline=True,
            axis_1=85,  # High Inflammation
            axis_5=75,  # High Insulin resistance
            axis_8=30,  # Optimal mitochondria
        )

        radar_list = record.to_radar_list()
        self.assertEqual(len(radar_list), 39)
        self.assertEqual(radar_list[0], 85)  # Axis 1
        self.assertEqual(radar_list[4], 75)  # Axis 5
        self.assertEqual(radar_list[7], 30)  # Axis 8

        # ตรวจสอบการคัดกรองแกนวิกฤต (>= 60)
        dysfunctional = record.get_dysfunctional_axes(threshold=60)
        self.assertTrue(any(d['axis_id'] == 1 for d in dysfunctional))
        self.assertTrue(any(d['axis_id'] == 5 for d in dysfunctional))
        self.assertFalse(any(d['axis_id'] == 8 for d in dysfunctional))

    def test_domain_score_averaging(self):
        """ทดสอบการคำนวณคะแนนเฉลี่ยระดับ 12 โดเมน"""
        sample_scores = {i: 50 for i in range(1, 40)}
        sample_scores[1] = 80
        sample_scores[2] = 80
        sample_scores[3] = 80
        sample_scores[4] = 80  # Domain 1 (Axes 1-4) เฉลี่ย = 80

        dom_scores = TspiClinicalEngine.calculate_domain_scores(sample_scores)
        self.assertEqual(len(dom_scores), 12)
        self.assertEqual(dom_scores[0]['domain_id'], 1)
        self.assertEqual(dom_scores[0]['average_score'], 80.0)

    def test_rbac_blocking_for_patient_role(self):
        """Pillar 2: คนไข้ทั่วไปต้องถูกบล็อกด้วย 403 Forbidden ไม่ให้เข้าดูเครื่องมือวิเคราะห์แพทย์"""
        self.client.force_login(self.patient_user)

        resp = self.client.get(reverse('clinical:axes_explorer'))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get(reverse('clinical:axis_graph'))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get(reverse('clinical:axis_timeline'))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get(reverse('clinical:therapeutic_matrix'))
        self.assertEqual(resp.status_code, 403)

    def test_doctor_access_and_auditlog(self):
        """Pillar 8: แพทย์เข้าดูและระบบบันทึก AuditLog อัตโนมัติ"""
        self.client.force_login(self.doctor)

        # เข้าหน้า Explorer
        resp = self.client.get(reverse('clinical:axes_explorer'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Systemic Inflammatory Load")
        self.assertContains(resp, "DNA Repair")

        # เข้าหน้า Graph / Topology
        resp = self.client.get(reverse('clinical:axis_graph') + f'?patient_id={self.patient.pk}')
        self.assertEqual(resp.status_code, 200)

        # ตรวจสอบ AuditLog บันทึกการเข้าดู Graph
        audit = AuditLog.objects.filter(
            action="AXIS_GRAPH_VIEW",
            user=self.doctor
        ).first()
        self.assertIsNotNone(audit)

    def test_htmx_update_axis_score(self):
        """ทดสอบการอัปเดตคะแนนแกนรายตัวผ่าน HTMX endpoint"""
        self.client.force_login(self.doctor)

        url = reverse('clinical:update_score_htmx', args=[self.patient.pk])
        resp = self.client.post(url, data={'axis_id': '11', 'score': '88'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "88 / 100")

        # ตรวจสอบค่าในฐานข้อมูล
        record = self.patient.biological_records.first()
        self.assertIsNotNone(record)
        self.assertEqual(record.axis_11, 88)
