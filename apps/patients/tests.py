"""
Unit & Security Tests for Patient EMR & Clinical Records (EP 3).
Validates RBAC Access (Pillar 2), Live HTMX Search, SOAP Notes & BMI, and AuditLog (Pillar 8).
"""

import os
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, AuditLog
from patients.models import Patient, PatientHistory
from patients.forms import PatientForm, PatientHistorySOAPForm


class PatientEMRTests(TestCase):
    def setUp(self):
        # Create Clinical Staff (Doctor)
        self.doctor = User.objects.create_user(
            username='dr_test',
            email='dr_test@tspi.com',
            password='Password12345!',
            role='doctor',
            first_name='สมชาย',
            last_name='ใจดี'
        )
        
        # Create Non-clinical Patient User
        self.patient_user = User.objects.create_user(
            username='patient_test',
            email='patient_test@tspi.com',
            password='Password12345!',
            role='patient',
            first_name='สมศรี',
            last_name='รักดี'
        )

        # Create Sample Patients
        self.patient1 = Patient.objects.create(
            hn='HN-2026-0001',
            first_name='มานะ',
            last_name='อดทน',
            nickname='นะ',
            gender='M',
            birth_date=date(1990, 5, 15),
            blood_type='O+',
            phone='0811111111',
            status='urgent',
            allergies='Penicillin'
        )

        self.patient2 = Patient.objects.create(
            hn='HN-2026-0002',
            first_name='ชูใจ',
            last_name='สดใส',
            gender='F',
            birth_date=date(1995, 10, 20),
            blood_type='A+',
            phone='0822222222',
            status='medicine'
        )

        self.client = Client()

    def test_patient_model_properties(self):
        """ทดสอบ properties ของ Patient: full_name และ age calculation"""
        self.assertEqual(self.patient1.full_name, "มานะ อดทน")
        today = date.today()
        expected_age = today.year - 1990 - ((today.month, today.day) < (5, 15))
        self.assertEqual(self.patient1.age, expected_age)

    def test_soap_form_bmi_calculation(self):
        """ทดสอบการคำนวณ BMI อัตโนมัติใน PatientHistorySOAPForm"""
        form_data = {
            'bp_systolic': 120,
            'bp_diastolic': 80,
            'pulse': 72,
            'temperature': 36.6,
            'weight_kg': 70.0,
            'height_cm': 175.0,
            'spo2': 99,
            'subjective': 'รู้สึกอ่อนเพลียเล็กน้อย',
            'objective': 'ความดันปกติ ชีพจรปกติ',
            'assessment': 'Mitochondrial dysfunction suspicion',
            'plan': 'สั่ง CoQ10 200mg/day'
        }
        form = PatientHistorySOAPForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        history = form.save(commit=False)
        history.patient = self.patient1
        history.doctor = self.doctor
        history.save()

        # BMI = 70 / (1.75 * 1.75) = 22.86 -> 22.9
        self.assertEqual(history.vitals.get('bmi'), 22.9)
        self.assertEqual(history.vitals.get('bp_systolic'), 120)

    def test_rbac_access_control(self):
        """Pillar 2: คนไข้ทั่วไป (patient role) ต้องถูกบล็อกด้วย 403 Forbidden ทุกหน้าคลินิก"""
        self.client.force_login(self.patient_user)
        
        # Test Doctor Dashboard
        resp = self.client.get(reverse('patients:dashboard'))
        self.assertEqual(resp.status_code, 403)

        # Test Patient Roster
        resp = self.client.get(reverse('patients:patient_list'))
        self.assertEqual(resp.status_code, 403)

        # Test Patient Detail EMR
        resp = self.client.get(reverse('patients:patient_detail', args=[self.patient1.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_doctor_access_and_auditlog_logging(self):
        """Pillar 8: แพทย์เข้าดู EMR ได้ 200 OK และระบบต้องบันทึก AuditLog"""
        self.client.force_login(self.doctor)

        # เข้าหน้ารายชื่อคนไข้
        resp = self.client.get(reverse('patients:patient_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HN-2026-0001")
        self.assertContains(resp, "มานะ อดทน")

        # เข้าหน้าแฟ้มคนไข้ (EMR Detail)
        detail_url = reverse('patients:patient_detail', args=[self.patient1.pk])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "มานะ อดทน")
        self.assertContains(resp, "Penicillin")

        # ตรวจสอบ AuditLog
        audit = AuditLog.objects.filter(
            action="EMR_PATIENT_VIEW",
            object_id=str(self.patient1.pk),
            user=self.doctor
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes.get('hn'), "HN-2026-0001")

    def test_htmx_live_search(self):
        """ทดสอบการค้นหาคนไข้แบบ HTMX Live Search (คืน Partial HTML)"""
        self.client.force_login(self.doctor)

        # ค้นหาด้วยชื่อ 'มานะ' ผ่าน HTMX
        resp = self.client.get(
            reverse('patients:patient_list') + '?q=มานะ',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HN-2026-0001")
        self.assertNotContains(resp, "HN-2026-0002")
        # ต้องไม่คืน template หลัก (base wrapper)
        self.assertNotContains(resp, "<!DOCTYPE html>")

    def test_htmx_status_filter(self):
        """ทดสอบการกรองสถานะคนไข้ (urgent) ผ่าน HTMX"""
        self.client.force_login(self.doctor)

        resp = self.client.get(
            reverse('patients:patient_list') + '?status=urgent',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HN-2026-0001")
        self.assertNotContains(resp, "HN-2026-0002")

    def test_soap_note_creation_htmx(self):
        """ทดสอบการเพิ่ม SOAP Note ผ่าน HTMX และการบันทึก AuditLog"""
        self.client.force_login(self.doctor)

        soap_url = reverse('patients:patient_add_soap', args=[self.patient1.pk])
        post_data = {
            'subjective': 'ปวดศีรษะเรื้อรัง',
            'objective': 'BP 130/85',
            'assessment': 'Hypothalamic-Pituitary axis stress',
            'plan': 'แนะนำฝึกการหายใจและแมกนีเซียม',
            'bp_systolic': 130,
            'bp_diastolic': 85,
        }

        resp = self.client.post(soap_url, data=post_data, HTTP_HX_REQUEST='true')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ปวดศีรษะเรื้อรัง")
        self.assertContains(resp, "BP: 130/85")

        # ตรวจสอบในฐานข้อมูล
        note = PatientHistory.objects.filter(patient=self.patient1).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.doctor, self.doctor)
        self.assertEqual(note.vitals.get('bp_systolic'), 130)

        # ตรวจสอบ AuditLog
        audit = AuditLog.objects.filter(
            action="SOAP_NOTE_RECORDED",
            user=self.doctor,
            object_id=str(note.pk)
        ).first()
        self.assertIsNotNone(audit)


class InvalidateSyncArtifactsCommandTests(TestCase):
    """คะแนน/สถานะที่ sync เดาขึ้นเองต้องถูกยกเลิก แต่ห้ามแตะข้อมูลที่แพทย์บันทึกจริง"""

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from clinical.models import BiologicalRecord
        from patients.management.commands.invalidate_sync_artifacts import SYNC_BASELINE_NOTE

        self.legacy = Patient.objects.create(hn='HN-LEG-1', first_name='a', last_name='b', status='urgent', extra_data={'legacy_id': 1})
        self.touched = Patient.objects.create(hn='HN-LEG-2', first_name='c', last_name='d', status='urgent', extra_data={'legacy_id': 2})
        Patient.objects.filter(pk=self.touched.pk).update(updated_at=timezone.now() + timedelta(days=1))
        self.native = Patient.objects.create(hn='HN-NEW-1', first_name='e', last_name='f', status='urgent')

        self.fake = BiologicalRecord.objects.create(patient=self.legacy, is_baseline=True, notes=SYNC_BASELINE_NOTE, axis_1=88)
        self.real = BiologicalRecord.objects.create(patient=self.legacy, is_baseline=True, notes='แพทย์ประเมินจริง', axis_1=70)

    def test_dry_run_changes_nothing(self):
        from django.core.management import call_command
        from clinical.models import BiologicalRecord
        call_command('invalidate_sync_artifacts', stdout=open(os.devnull, 'w'))
        self.assertEqual(BiologicalRecord.objects.count(), 2)
        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.status, 'urgent')

    def test_apply_hides_only_synthetic_records_and_untouched_legacy_status(self):
        from django.core.management import call_command
        from clinical.models import BiologicalRecord
        from accounts.models import AuditLog
        call_command('invalidate_sync_artifacts', apply=True, stdout=open(os.devnull, 'w'))

        self.assertEqual(list(BiologicalRecord.objects.values_list('pk', flat=True)), [self.real.pk])
        fake = BiologicalRecord.all_objects.get(pk=self.fake.pk)
        self.assertTrue(fake.is_deleted)
        self.assertIn('sync_real_patients', fake.invalidation_reason)

        for p in (self.legacy, self.touched, self.native):
            p.refresh_from_db()
        self.assertEqual(self.legacy.status, 'pending')
        self.assertEqual(self.touched.status, 'urgent')
        self.assertEqual(self.native.status, 'urgent')
        self.assertTrue(AuditLog.objects.filter(action='SYNC_ARTIFACTS_INVALIDATED').exists())


class DoctorPortalPageRegressionTests(TestCase):
    """หน้าที่เคยพัง: audit 500 เมื่อมี log ไม่มีผู้ใช้, layout ของ staff/boxes หาย"""

    def setUp(self):
        self.doctor = User.objects.create_user(username='dr_reg', password='DoctorPass2026!x', role=User.Role.DOCTOR)
        self.client.force_login(self.doctor)

    def test_audit_page_renders_with_anonymous_log(self):
        AuditLog.objects.create(user=None, action='LOGIN_FAILED', model='User', object_id='x')
        resp = self.client.get('/doctor/audit/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'ผู้ใช้ไม่ระบุตัวตน')

    def test_staff_and_box_pages_keep_doctor_layout_styles(self):
        for url in ('/staff/inbox/', '/staff/review-queue/', '/clinical/boxes/'):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertContains(resp, '.doctor-sidebar', msg_prefix=url)


class PatientPortalDataIsolationTests(TestCase):
    """บัญชีผู้ป่วยต้องเห็นเฉพาะข้อมูลของตัวเอง และไม่เห็นคะแนนที่ไม่ได้มาจากการประเมินจริง"""

    def setUp(self):
        from clinical.models import AnalysisRecord
        self.other = Patient.objects.create(hn='HN-OTHER-1', first_name='คนอื่น', last_name='ในระบบ')
        doctor = User.objects.create_user(username='dr_iso', password='DoctorPass2026!x', role=User.Role.DOCTOR)
        AnalysisRecord.objects.create(patient=self.other, physician=doctor, status='approved', snapshot_scores={})
        self.unlinked_user = User.objects.create_user(username='pt_unlinked', password='PatientPass2026!x', role=User.Role.PATIENT)
        self.client.force_login(self.unlinked_user)

    def test_unlinked_account_never_sees_another_patient(self):
        for url in ('/patient/axes-result/', '/patient/digital-twin/', '/patient/history/', '/patient/download/'):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertNotContains(resp, 'HN-OTHER-1', msg_prefix=url)
            self.assertNotContains(resp, 'คนอื่น', msg_prefix=url)

    def test_unassessed_axes_show_no_scores(self):
        resp = self.client.get('/patient/axes-result/')
        self.assertContains(resp, 'ยังไม่ประเมิน')
        self.assertNotContains(resp, '50/100')
