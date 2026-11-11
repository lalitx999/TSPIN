"""
คิวคนไข้วันนี้ (/doctor/pre-visit/): ใช้ข้อมูลจริงเท่านั้น และปุ่มเริ่มตรวจพาไปฟอร์มบันทึกการตรวจ
"""

from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, User
from clinical.models import BiologicalRecord, Box
from patients.models import Appointment, Patient, PatientHistory


class PreVisitQueueTests(TestCase):
    def setUp(self):
        self.nurse = User.objects.create_user(username='nurse_pv', password='NursePass2026!x', role=User.Role.NURSE)
        self.doctor = User.objects.create_user(username='doc_pv', password='DocPass2026!x', role=User.Role.DOCTOR)
        self.patient = Patient.objects.create(hn='HN-PV-1', first_name='วันดี', last_name='มีสุข', phone='0811111111')
        self.today = timezone.localdate()
        self.appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, appointment_date=self.today,
                                               appointment_time=time(10, 0), notes='ติดตามผล')
        self.client.force_login(self.nurse)
        self.url = reverse('patients:doctor_pre_visit')

    def test_missing_data_is_shown_as_missing_never_as_fake_values(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.context['patient'], self.patient)
        for fake in ('ปฏิเสธการแพ้ยาและอาหาร', 'ไม่มีการใช้ยาปฏิชีวนะประจำ', 'มีอาการผื่นคันเรื้อรัง', 'STEP 01'):
            self.assertNotContains(resp, fake)
        self.assertContains(resp, 'ยังไม่ได้บันทึกประวัติแพ้ยา')
        self.assertContains(resp, 'ยังไม่ได้บันทึกอาการสำคัญ')
        self.assertContains(resp, 'ยังไม่เคยประเมิน 39 แกน')

    def test_real_allergy_last_visit_line_chat_and_axes_are_shown(self):
        self.patient.allergies = 'แพ้เพนิซิลลิน'
        self.patient.line_user_id = 'U_PV_1'
        self.patient.save()
        PatientHistory.objects.create(patient=self.patient, doctor=self.doctor, assessment='ประเมินครั้งก่อน',
                                      plan='นัดติดตาม', vitals={'bp_systolic': 140, 'bp_diastolic': 90})
        Box.objects.create(patient=self.patient, source=Box.Source.LINE, status=Box.Status.DONE,
                           contents={'messages': [{'text': 'x'}], 'red_flag': True}, last_activity_at=timezone.now())
        BiologicalRecord.objects.create(patient=self.patient, axis_5=82, axis_1=40)
        resp = self.client.get(self.url)
        self.assertContains(resp, 'แพ้เพนิซิลลิน')
        self.assertContains(resp, 'BP 140/90')
        self.assertContains(resp, 'ประเมินครั้งก่อน')
        self.assertContains(resp, 'ฉุกเฉิน')
        axes = resp.context['brief']['abnormal_axes']
        self.assertEqual([a['id'] for a in axes], [5])
        self.assertEqual(axes[0]['name'], 'Glucose–Insulin Regulation')

    def test_queue_lists_the_day_and_opening_from_calendar_shows_that_day(self):
        later = self.today + timedelta(days=3)
        other = Appointment.objects.create(patient=self.patient, doctor=self.doctor, appointment_date=later, appointment_time=time(9, 0))
        resp = self.client.get(self.url, {'appointment_id': other.pk})
        self.assertEqual(resp.context['day'], later)
        self.assertEqual([a.pk for a in resp.context['queue']], [other.pk])
        self.assertNotContains(resp, reverse('patients:previsit_start', args=[other.pk]))  # เริ่มตรวจได้เฉพาะวันนี้

    def test_walk_in_patient_without_appointment(self):
        walk_in = Patient.objects.create(hn='HN-PV-2', first_name='เดินมา', last_name='เอง', phone='0822222222')
        resp = self.client.get(self.url, {'patient_id': walk_in.pk})
        self.assertEqual(resp.context['patient'], walk_in)
        self.assertIsNone(resp.context['appointment'])
        self.assertContains(resp, f"{reverse('patients:patient_detail', args=[walk_in.pk])}?visit=1")

    def test_start_marks_arrived_and_opens_visit_form(self):
        resp = self.client.post(reverse('patients:previsit_start', args=[self.appt.pk]))
        self.assertRedirects(resp, f"{reverse('patients:patient_detail', args=[self.patient.pk])}?visit=1#new-soap",
                             fetch_redirect_response=False)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, 'completed')
        self.assertTrue(AuditLog.objects.filter(action='APPOINTMENT_STATUS_CHANGED', changes__via='pre_visit_start').exists())
        page = self.client.get(reverse('patients:patient_detail', args=[self.patient.pk]), {'visit': '1'})
        self.assertTrue(page.context['open_visit'])

    def test_start_refuses_cancelled_or_other_day(self):
        self.appt.status = 'cancelled'
        self.appt.save()
        self.client.post(reverse('patients:previsit_start', args=[self.appt.pk]))
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, 'cancelled')
        future = Appointment.objects.create(patient=self.patient, doctor=self.doctor,
                                            appointment_date=self.today + timedelta(days=1), appointment_time=time(9, 0))
        self.client.post(reverse('patients:previsit_start', args=[future.pk]))
        future.refresh_from_db()
        self.assertEqual(future.status, 'scheduled')

    def test_doctor_can_filter_own_queue(self):
        other_doc = User.objects.create_user(username='doc_pv2', password='DocPass2026!x', role=User.Role.DOCTOR)
        Appointment.objects.create(patient=self.patient, doctor=other_doc, appointment_date=self.today, appointment_time=time(11, 0))
        self.client.force_login(self.doctor)
        self.assertEqual(len(self.client.get(self.url).context['queue']), 2)
        self.assertEqual(len(self.client.get(self.url, {'mine': '1'}).context['queue']), 1)
