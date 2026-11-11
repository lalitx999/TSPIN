"""
Automated Unit Tests for Option C: Staff UI (Unified Inbox, Clinical Review Queue, Staff Dashboard).
Verifies:
1. Authentication & Role-Based Access Control (@clinical_staff_required, @doctor_only, 403 for patients)
2. Staff Dashboard stats and counts
3. Unified Inbox listing and manual review item generation
4. Level 1 Intake approval by Nurse and Doctor
5. Level 2 Diagnostic approval restricted to Doctor (PermissionDenied for Nurse)
6. Rejection with reason (no EMR generation)
7. Database-level Race Condition Guard (409 Conflict on concurrent approvals)
8. Real-time Polling API for Live Sync
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from patients.models import (
    Patient,
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
    PatientHistory,
)


class StaffUITests(TestCase):
    def setUp(self):
        self.client = Client()

        # ผู้ใช้งานประเภทต่างๆ สำหรับทดสอบ RBAC
        self.doctor = User.objects.create_user(
            username='doctor_somchai',
            email='somchai@tspi.com',
            password='Password123!',
            role=User.Role.DOCTOR,
            first_name='สมชาย',
            last_name='ใจดี'
        )

        self.nurse = User.objects.create_user(
            username='nurse_wanida',
            email='wanida@tspi.com',
            password='Password123!',
            role=User.Role.NURSE,
            first_name='วนิดา',
            last_name='รักษาดี'
        )

        self.patient_user = User.objects.create_user(
            username='patient_charlie',
            email='charlie@gmail.com',
            password='Password123!',
            role='patient',
            first_name='ชาลี',
            last_name='แซ่ลี้'
        )

        # ข้อมูลคนไข้และข้อความ LINE
        self.patient = Patient.objects.create(
            hn='HN-STAFF-001',
            first_name='ประสิทธิ์',
            last_name='มีชัย',
            phone='0812345678'
        )

        self.line_user = LineUser.objects.create(
            line_user_id='U_STAFF_LINE_TEST_123',
            display_name='ประสิทธิ์ LINE',
            active_patient=self.patient
        )

        self.binding = LinePatientBinding.objects.create(
            line_user=self.line_user,
            patient=self.patient,
            role=LinePatientBinding.RoleChoices.SELF,
            status=LinePatientBinding.StatusChoices.ACTIVE,
            verified_method='LIFF_2STEP_OTP'
        )

        self.comm_msg = CommunicationRecord.objects.create(
            line_message_id='msg_staff_test_001',
            line_user=self.line_user,
            patient=self.patient,
            direction=CommunicationRecord.DirectionChoices.INCOMING,
            message_type=CommunicationRecord.MessageTypeChoices.TEXT,
            content='มีอาการไข้ต่ำๆ และไอแห้งมา 2 วัน',
            is_clinical_candidate=True
        )

    def test_unauthenticated_staff_redirects_to_login(self):
        """1. ผู้ใช้ที่ไม่ได้ Login เข้าหน้า /staff/inbox/ ต้องถูก redirect ไปหน้า login"""
        resp = self.client.get(reverse('patients:staff_inbox'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/doctor/login/', resp.url)

    def test_patient_role_forbidden_403(self):
        """2. ผู้ใช้ที่เป็นคนไข้ (Role: patient) เข้าหน้า Staff ต้องติด 403 Forbidden"""
        self.client.force_login(self.patient_user)
        resp = self.client.get(reverse('patients:staff_review_queue'))
        self.assertEqual(resp.status_code, 403)

    def test_nurse_can_access_inbox_and_dashboard(self):
        """3. พยาบาล (Role: nurse) สามารถเข้าใช้งานหน้า Dashboard และ Inbox ได้"""
        self.client.force_login(self.nurse)
        resp1 = self.client.get(reverse('patients:staff_dashboard'))
        self.assertEqual(resp1.status_code, 200)

        resp2 = self.client.get(reverse('patients:staff_inbox'))
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, 'ประสิทธิ์ LINE')

    def test_nurse_can_approve_level1_intake(self):
        """4. พยาบาล สามารถอนุมัติเคส Level 1 Intake ได้ และข้อมูลถูกบันทึกลง EMR PatientHistory"""
        self.client.force_login(self.nurse)

        item = ClinicalReviewItem.objects.create(
            patient=self.patient,
            source_message=self.comm_msg,
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE,
            status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
            review_notes='คัดกรองอาการไข้'
        )

        resp = self.client.post(
            reverse('patients:api_approve_review_item', kwargs={'item_id': item.pk}),
            data={'subjective': 'ไข้ต่ำ 2 วัน', 'objective': '', 'assessment': 'ไข้ต่ำ ไม่มีอาการรุนแรง', 'plan': 'ดื่มน้ำ พักผ่อน นัดติดตาม', 'reviewed': '1'}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')

        # ตรวจสอบสถานะในฐานข้อมูล
        item.refresh_from_db()
        self.assertEqual(item.status, ClinicalReviewItem.StatusChoices.APPROVED)
        self.assertEqual(item.reviewer, self.nurse)
        self.assertEqual(item.reviewer_role, 'nurse')
        self.assertIsNotNone(item.committed_history)

        # ตรวจสอบว่าถูกสร้างเป็น PatientHistory ใน EMR จริง
        # บันทึกตาม SOAP ที่ผู้ตรวจเขียนเท่านั้น ไม่มีข้อความสำเร็จรูป
        history = item.committed_history
        self.assertEqual(history.patient, self.patient)
        self.assertEqual(history.doctor, self.nurse)
        self.assertEqual(history.assessment, 'ไข้ต่ำ ไม่มีอาการรุนแรง')
        self.assertNotIn('ผ่านการตรวจทานและรับรองโดย', history.assessment)

    def test_nurse_cannot_approve_level2_diagnostic_permission_denied(self):
        """5. พยาบาล พยายามอนุมัติเคส Level 2 Diagnostic (แพทย์เท่านั้น) -> ต้องติด 403 Forbidden"""
        self.client.force_login(self.nurse)

        urgent_msg = CommunicationRecord.objects.create(
            line_message_id='msg_urgent_test_002',
            line_user=self.line_user,
            patient=self.patient,
            content='มีอาการแน่นหน้าอกรุนแรง หายใจไม่ออก',
            is_clinical_candidate=True
        )

        item = ClinicalReviewItem.objects.create(
            patient=self.patient,
            source_message=urgent_msg,
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC,
            status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
            review_notes='ตรวจพบอาการวิกฤต'
        )

        resp = self.client.post(
            reverse('patients:api_approve_review_item', kwargs={'item_id': item.pk}),
            data={'subjective': 'ไข้ต่ำ 2 วัน', 'objective': '', 'assessment': 'ไข้ต่ำ ไม่มีอาการรุนแรง', 'plan': 'ดื่มน้ำ พักผ่อน นัดติดตาม', 'reviewed': '1'}
        )

        # ต้องติดสิทธิ์ 403
        self.assertEqual(resp.status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.status, ClinicalReviewItem.StatusChoices.PENDING_REVIEW)
        self.assertIsNone(item.committed_history)

    def test_doctor_can_approve_level2_diagnostic(self):
        """6. แพทย์ สามารถอนุมัติเคส Level 2 Diagnostic ได้สมบูรณ์"""
        self.client.force_login(self.doctor)

        urgent_msg = CommunicationRecord.objects.create(
            line_message_id='msg_urgent_test_003',
            line_user=self.line_user,
            patient=self.patient,
            content='มีอาการแน่นหน้าอก หายใจไม่ออก',
            is_clinical_candidate=True
        )

        item = ClinicalReviewItem.objects.create(
            patient=self.patient,
            source_message=urgent_msg,
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC,
            status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW
        )

        resp = self.client.post(
            reverse('patients:api_approve_review_item', kwargs={'item_id': item.pk}),
            data={'subjective': 'ไข้ต่ำ 2 วัน', 'objective': '', 'assessment': 'ไข้ต่ำ ไม่มีอาการรุนแรง', 'plan': 'ดื่มน้ำ พักผ่อน นัดติดตาม', 'reviewed': '1'}
        )

        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, ClinicalReviewItem.StatusChoices.APPROVED)
        self.assertEqual(item.reviewer, self.doctor)
        self.assertEqual(item.reviewer_role, 'doctor')
        self.assertEqual(item.committed_history.doctor, self.doctor)

    def test_reject_review_item_with_reason(self):
        """7. การปฏิเสธคำขอ: เปลี่ยนสถานะเป็น REJECTED พร้อมบันทึกเหตุผล ไม่สร้าง EMR Record"""
        self.client.force_login(self.nurse)

        item = ClinicalReviewItem.objects.create(
            patient=self.patient,
            source_message=self.comm_msg,
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE,
            status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW
        )

        resp = self.client.post(
            reverse('patients:api_reject_review_item', kwargs={'item_id': item.pk}),
            data={'reason': 'ข้อความไม่เกี่ยวกับอาการทางการแพทย์ ถามเรื่องที่จอดรถ'}
        )

        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, ClinicalReviewItem.StatusChoices.REJECTED)
        self.assertEqual(item.reviewer, self.nurse)
        self.assertIn('ถามเรื่องที่จอดรถ', item.rejection_reason)
        self.assertIsNone(item.committed_history)

    def test_race_condition_guard_second_approval_fails(self):
        """8. Race Condition Guard: หากมีคนกด Approve ไปแล้ว การกดซ้ำต้องได้ 409 Conflict"""
        self.client.force_login(self.doctor)

        item = ClinicalReviewItem.objects.create(
            patient=self.patient,
            source_message=self.comm_msg,
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE,
            status=ClinicalReviewItem.StatusChoices.APPROVED,  # ถูกอนุมัติไปแล้ว
            reviewer=self.doctor,
            reviewed_at=timezone.now()
        )

        resp = self.client.post(
            reverse('patients:api_approve_review_item', kwargs={'item_id': item.pk}),
            data={'subjective': 'ไข้ต่ำ 2 วัน', 'objective': '', 'assessment': 'ไข้ต่ำ ไม่มีอาการรุนแรง', 'plan': 'ดื่มน้ำ พักผ่อน นัดติดตาม', 'reviewed': '1'}
        )

        self.assertEqual(resp.status_code, 409)
        self.assertIn('ได้รับการประมวลผลแล้วโดยผู้อื่น', resp.json()['message'])

    def test_review_queue_polling_api(self):
        """9. Real-time Polling API: ส่งคืนสถิติจำนวนเคสรอตรวจทานอย่างถูกต้อง"""
        self.client.force_login(self.nurse)

        ClinicalReviewItem.objects.create(
            patient=self.patient,
            source_message=self.comm_msg,
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE,
            status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW
        )

        resp = self.client.get(reverse('patients:api_review_queue_poll'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertGreaterEqual(data['pending_level1'], 1)
        self.assertIn('timestamp', data)

    def test_create_review_item_from_inbox_message(self):
        """10. สร้าง ClinicalReviewItem จาก Inbox ด้วยตนเอง"""
        self.client.force_login(self.nurse)

        general_msg = CommunicationRecord.objects.create(
            line_message_id='msg_manual_create_001',
            line_user=self.line_user,
            patient=self.patient,
            content='อยากปรึกษาเรื่องผลเลือดที่ตรวจคราวก่อน',
            is_clinical_candidate=False
        )

        resp = self.client.post(
            reverse('patients:api_create_review_from_message'),
            data={
                'message_id': general_msg.pk,
                'review_type': ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE
            }
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        review_id = data['review_item_id']

        # ตรวจสอบว่าถูกสร้างขึ้นในคิวตรวจทานจริง
        review = ClinicalReviewItem.objects.get(pk=review_id)
        self.assertEqual(review.status, ClinicalReviewItem.StatusChoices.PENDING_REVIEW)
        self.assertEqual(review.patient, self.patient)
        general_msg.refresh_from_db()
        self.assertTrue(general_msg.is_clinical_candidate)


class ReviewHubTests(TestCase):
    """กล่องงานรอตรวจทาน: รวมงานทุกประเภท, บันทึกต้องเขียน SOAP + ยืนยัน, ข้อความด่วนเป็นของแพทย์, ไม่ซ้ำกับแชทบอท"""

    def setUp(self):
        from clinical.models import Box
        self.nurse = User.objects.create_user(username='nurse_hub', password='Password123!', role=User.Role.NURSE)
        self.doctor = User.objects.create_user(username='doc_hub', password='Password123!', role=User.Role.DOCTOR)
        self.patient = Patient.objects.create(hn='HN-HUB-1', first_name='สมใจ', last_name='ดีงาม', phone='0811111111')
        self.line_user = LineUser.objects.create(line_user_id='U_HUB_1', display_name='สมใจ', active_patient=self.patient)
        self.msg = CommunicationRecord.objects.create(line_message_id='hub_msg_1', line_user=self.line_user, patient=self.patient,
                                                      content='ปวดท้องมาก', is_clinical_candidate=True)
        self.item = ClinicalReviewItem.objects.create(patient=self.patient, source_message=self.msg,
                                                      review_notes='ตรวจพบคีย์เวิร์ด: ปวด\n[+ข้อความต่อเนื่อง]: ท้องเสียด้วย (คำสำคัญ: ท้องเสีย)')
        self.urgent_msg = CommunicationRecord.objects.create(line_message_id='hub_msg_2', line_user=self.line_user,
                                                             patient=self.patient, content='แน่นหน้าอก', is_clinical_candidate=True)
        self.urgent = ClinicalReviewItem.objects.create(patient=self.patient, source_message=self.urgent_msg,
                                                        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC)
        self.box = Box.objects.create(patient=self.patient, source=Box.Source.LINE, status=Box.Status.DONE,
                                      contents={'messages': [{'text': 'ปวดหัว'}], 'has_symptoms': True},
                                      last_activity_at=timezone.now())

    def test_hub_lists_chats_messages_with_grouped_texts(self):
        self.client.force_login(self.nurse)
        resp = self.client.get(reverse('patients:staff_review_queue'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['counts']['chats'], 1)
        self.assertEqual(resp.context['counts']['messages'], 2)
        item = next(i for i in resp.context['message_items'] if i.pk == self.item.pk)
        self.assertEqual(item.texts, ['ปวดท้องมาก', 'ท้องเสียด้วย'])
        self.assertContains(resp, reverse('clinical:intake_detail', args=[self.box.id]))
        self.assertContains(resp, 'รอแพทย์ตัดสิน')  # พยาบาลเห็นข้อความด่วนแต่ตัดสินเองไม่ได้
        poll = self.client.get(reverse('patients:api_review_queue_poll')).json()
        self.assertEqual(poll['hub_total'], 3)

    def test_approve_requires_review_tick_and_subjective(self):
        self.client.force_login(self.nurse)
        url = reverse('patients:api_approve_review_item', kwargs={'item_id': self.item.pk})
        self.assertEqual(self.client.post(url, {'subjective': 'ปวดท้อง'}).status_code, 400)
        self.assertEqual(self.client.post(url, {'subjective': '', 'reviewed': '1'}).status_code, 400)
        self.assertFalse(PatientHistory.objects.exists())

    def test_only_doctor_can_dismiss_urgent_message(self):
        url = reverse('patients:api_reject_review_item', kwargs={'item_id': self.urgent.pk})
        self.client.force_login(self.nurse)
        self.assertEqual(self.client.post(url, {'reason': 'ไม่เกี่ยว'}).status_code, 403)
        self.urgent.refresh_from_db()
        self.assertEqual(self.urgent.status, ClinicalReviewItem.StatusChoices.PENDING_REVIEW)
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.post(url, {'reason': 'ไม่เกี่ยว'}).status_code, 200)

    def test_symptom_message_while_bot_on_goes_to_chat_only(self):
        from patients.views_line_internal import ingest_line_event
        self.line_user.bot_enabled = True
        self.line_user.bot_last_active_at = timezone.now()
        self.line_user.save()
        result, _ = ingest_line_event({'type': 'message', 'source': {'userId': 'U_HUB_1'},
                                       'message': {'id': 'hub_bot_on_1', 'type': 'text', 'text': 'มีไข้สูง ปวดหัวมาก'}})
        self.assertTrue(result['routed_to_chat'])
        self.assertIsNone(result['review_item_id'])
        self.assertFalse(ClinicalReviewItem.objects.filter(source_message__line_message_id='hub_bot_on_1').exists())
