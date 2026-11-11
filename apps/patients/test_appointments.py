"""
ปฏิทินนัดหมาย: แสดงทั้งเดือน, สร้างนัดต้องเลือกแพทย์ / ห้ามนัดย้อนหลัง / ห้ามชนคิว, เปลี่ยนสถานะ, เวลาที่ไม่ว่าง
"""

import json
from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, User
from patients.models import Appointment, Patient


class AppointmentCalendarTests(TestCase):
    def setUp(self):
        self.nurse = User.objects.create_user(username='nurse_cal', password='NursePass2026!x', role=User.Role.NURSE)
        self.doctor = User.objects.create_user(username='doc_cal', password='DocPass2026!x', role=User.Role.DOCTOR,
                                               first_name='สมศักดิ์', last_name='ใจดี')
        self.other_doctor = User.objects.create_user(username='doc_cal2', password='DocPass2026!x', role=User.Role.DOCTOR)
        self.patient = Patient.objects.create(hn='HN-CAL-1', first_name='มานี', last_name='มีนา', phone='0811111111', gender='F')
        self.patient2 = Patient.objects.create(hn='HN-CAL-2', first_name='ชูใจ', last_name='ดีมาก', phone='0822222222', gender='M')
        self.client.force_login(self.nurse)
        self.tomorrow = timezone.localdate() + timedelta(days=1)

    def create(self, **overrides):
        data = {'patient_id': self.patient.pk, 'doctor_id': self.doctor.pk,
                'appointment_date': self.tomorrow.isoformat(), 'appointment_time': '10:30', 'notes': 'ตรวจแล็บ'}
        data.update(overrides)
        return self.client.post(reverse('patients:appointment_create'), data)

    def test_month_page_shows_thai_buddhist_month_and_appointments(self):
        Appointment.objects.create(patient=self.patient, doctor=self.doctor, appointment_date=self.tomorrow,
                                   appointment_time=time(9, 0), status='confirmed')
        month = self.tomorrow.strftime('%Y-%m')
        resp = self.client.get(reverse('patients:doctor_appointments'), {'month': month, 'day': self.tomorrow.isoformat()})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, str(self.tomorrow.year + 543))
        data = resp.context['calendar_data']
        self.assertEqual(data['selected'], self.tomorrow.isoformat())
        self.assertEqual(data['appointments'][0]['patient']['hn'], 'HN-CAL-1')
        self.assertEqual(data['appointments'][0]['doctor'], 'สมศักดิ์ ใจดี')
        self.assertEqual(len(data['weeks'][0]), 7)

    def test_bad_month_param_falls_back_to_this_month(self):
        resp = self.client.get(reverse('patients:doctor_appointments'), {'month': 'abc'})
        self.assertEqual(resp.context['month_value'], timezone.localdate().strftime('%Y-%m'))

    def test_create_uses_chosen_doctor_not_the_nurse(self):
        resp = self.create()
        self.assertTrue(resp.json()['ok'])
        appt = Appointment.objects.get()
        self.assertEqual(appt.doctor, self.doctor)
        self.assertEqual(appt.status, 'scheduled')
        self.assertTrue(AuditLog.objects.filter(action='APPOINTMENT_CREATED', object_id=str(appt.pk)).exists())

    def test_create_requires_doctor_patient_date_and_time(self):
        resp = self.client.post(reverse('patients:appointment_create'), {})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(set(resp.json()['fields']), {'patient_id', 'doctor_id', 'appointment_date', 'appointment_time'})
        nurse_as_doctor = self.create(doctor_id=self.nurse.pk)
        self.assertIn('ไม่พบแพทย์ที่เลือก', nurse_as_doctor.json()['errors'])
        self.assertFalse(Appointment.objects.exists())

    def test_cannot_book_in_the_past(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        resp = self.create(appointment_date=yesterday.isoformat())
        self.assertEqual(resp.status_code, 400)
        self.assertIn('ย้อนหลัง', resp.json()['errors'][0])

    def test_doctor_and_patient_double_booking_blocked_but_cancelled_slot_reusable(self):
        self.assertTrue(self.create().json()['ok'])
        clash = self.create(patient_id=self.patient2.pk)
        self.assertIn('มีนัดเวลานี้แล้ว', clash.json()['errors'][0])
        same_patient = self.create(doctor_id=self.other_doctor.pk)
        self.assertIn('คนไข้รายนี้มีนัด', same_patient.json()['errors'][0])
        Appointment.objects.update(status='cancelled')
        self.assertTrue(self.create(patient_id=self.patient2.pk).json()['ok'])

    def test_status_change_rules(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, appointment_date=self.tomorrow,
                                          appointment_time=time(9, 0))
        url = reverse('patients:appointment_status', args=[appt.pk])
        ok = self.client.post(url, {'status': 'confirmed'})
        self.assertEqual(ok.json()['appointment']['status_label'], 'ยืนยันแล้ว')
        self.assertEqual(self.client.post(url, {'status': 'bogus'}).status_code, 400)
        future_done = self.client.post(url, {'status': 'completed'})
        self.assertEqual(future_done.status_code, 400)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'confirmed')
        log = AuditLog.objects.get(action='APPOINTMENT_STATUS_CHANGED')
        self.assertEqual(log.changes, {'from': 'scheduled', 'to': 'confirmed', 'patient_hn': 'HN-CAL-1'})

    def test_taken_slots_per_doctor_ignore_cancelled(self):
        Appointment.objects.create(patient=self.patient, doctor=self.doctor, appointment_date=self.tomorrow, appointment_time=time(9, 0))
        Appointment.objects.create(patient=self.patient2, doctor=self.doctor, appointment_date=self.tomorrow,
                                   appointment_time=time(11, 0), status='cancelled')
        resp = self.client.get(reverse('patients:appointment_taken'),
                               {'date': self.tomorrow.isoformat(), 'doctor': self.doctor.pk, 'patient': self.patient.pk})
        self.assertEqual(resp.json(), {'taken': ['09:00'], 'patient_times': ['09:00']})

    def test_patient_search_matches_full_name_and_returns_gender_code(self):
        resp = self.client.get(reverse('patients:api_patient_search'), {'q': 'มานี มีนา'})
        results = resp.json()['results']
        self.assertEqual([r['hn'] for r in results], ['HN-CAL-1'])
        self.assertEqual(results[0]['gender_code'], 'F')

    def test_dashboard_today_count_ignores_cancelled(self):
        today = timezone.localdate()
        Appointment.objects.create(patient=self.patient, doctor=self.doctor, appointment_date=today, appointment_time=time(23, 0))
        Appointment.objects.create(patient=self.patient2, doctor=self.doctor, appointment_date=today,
                                   appointment_time=time(23, 30), status='cancelled')
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.get(reverse('patients:dashboard')).context['today_appointments'], 1)
