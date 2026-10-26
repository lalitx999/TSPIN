"""
Unit & Governance Tests for LINE OA Caregiver Hub (Level 2).
Verifies:
1. Caregiver 1:N Relationship (1 LINE user managing multiple patients)
2. Duplicate Binding Prevention (unique constraint)
3. Patient Linking Token Expiry & Nonce Validation
4. Clinical Review Item Level 1: Nurse Authorization
5. Clinical Review Item Level 2: Doctor-Only Restriction & EMR History Commit
"""

import json
from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError
from django.core.exceptions import PermissionDenied
from accounts.models import User, AuditLog
from patients.models import (
    Patient,
    PatientLinkingToken,
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
    PatientHistory,
)


class LineOACaregiverHubTests(TestCase):
    def setUp(self):
        # สร้างบุคลากรทางการแพทย์ (Doctor & Nurse)
        self.doctor = User.objects.create_user(
            username='dr_line_test',
            email='dr_line@tspi.com',
            password='Password123!',
            role='doctor',
            first_name='นายแพทย์ธีรภัทร',
            last_name='เมดิคอล'
        )
        self.nurse = User.objects.create_user(
            username='nurse_line_test',
            email='nurse_line@tspi.com',
            password='Password123!',
            role='nurse',
            first_name='พยาบาลพรทิพย์',
            last_name='ใจดี'
        )

        # สร้างผู้ป่วย 3 ราย (คุณพ่อ, คุณแม่, ลูกสาว)
        self.father = Patient.objects.create(
            hn='HN-FATHER-01',
            first_name='ประเสริฐ',
            last_name='วงศ์สว่าง',
            gender='M',
            birth_date=date(1960, 1, 10),
            phone='0811112222'
        )
        self.mother = Patient.objects.create(
            hn='HN-MOTHER-02',
            first_name='สมใจ',
            last_name='วงศ์สว่าง',
            gender='F',
            birth_date=date(1965, 3, 15),
            phone='0822223333'
        )
        self.child = Patient.objects.create(
            hn='HN-CHILD-03',
            first_name='น้องขวัญ',
            last_name='วงศ์สว่าง',
            gender='F',
            birth_date=date(2015, 8, 20),
            phone='0833334444'
        )

        # ผู้ติดต่อ LINE (ลูกสาว/ผู้ดูแลหลัก)
        self.line_user = LineUser.objects.create(
            line_user_id='U1234567890abcdef1234567890abcdef',
            display_name='แอนนี่ วงศ์สว่าง (Caregiver)'
        )

    def test_caregiver_1_to_n_binding(self):
        """
        1. Caregiver Model (1:N):
        ผู้ติดต่อ LINE 1 คน สามารถผูกเพื่อดูแลคนไข้ได้หลายราย (พ่อ, แม่, ลูก)
        โดยระบบแยกบริบทของคนไข้แต่ละรายอย่างชัดเจน
        """
        # ผูกกับคุณพ่อ (Role: FATHER)
        binding_father = LinePatientBinding.objects.create(
            line_user=self.line_user,
            patient=self.father,
            role=LinePatientBinding.RoleChoices.FATHER,
            status=LinePatientBinding.StatusChoices.ACTIVE,
            verified_method='LIFF_HN_OTP',
            verified_at=timezone.now()
        )

        # ผูกกับคุณแม่ (Role: MOTHER)
        binding_mother = LinePatientBinding.objects.create(
            line_user=self.line_user,
            patient=self.mother,
            role=LinePatientBinding.RoleChoices.MOTHER,
            status=LinePatientBinding.StatusChoices.ACTIVE,
            verified_method='LIFF_HN_OTP',
            verified_at=timezone.now()
        )

        # ผูกกับลูกสาว (Role: CHILD)
        binding_child = LinePatientBinding.objects.create(
            line_user=self.line_user,
            patient=self.child,
            role=LinePatientBinding.RoleChoices.CHILD,
            status=LinePatientBinding.StatusChoices.ACTIVE,
            verified_method='STAFF_IN_PERSON',
            verified_at=timezone.now()
        )

        # ตรวจสอบ 1 LINE Contact ผูกได้ 3 คนไข้
        self.assertEqual(self.line_user.patient_bindings.count(), 3)
        self.assertEqual(self.father.line_bindings.first().line_user, self.line_user)
        self.assertEqual(binding_father.role, 'FATHER')
        self.assertEqual(binding_mother.role, 'MOTHER')
        self.assertEqual(binding_child.role, 'CHILD')

    def test_duplicate_binding_prevention(self):
        """
        2. ป้องกันการผูกบัญชีซ้ำซ้อน:
        line_user เดิม กับ patient เดิม ไม่สามารถสร้าง binding ซ้ำได้ (Unique Constraint)
        """
        LinePatientBinding.objects.create(
            line_user=self.line_user,
            patient=self.father,
            role=LinePatientBinding.RoleChoices.FATHER,
            status=LinePatientBinding.StatusChoices.ACTIVE
        )

        with self.assertRaises(IntegrityError):
            LinePatientBinding.objects.create(
                line_user=self.line_user,
                patient=self.father,
                role=LinePatientBinding.RoleChoices.CAREGIVER,
                status=LinePatientBinding.StatusChoices.ACTIVE
            )

    def test_token_expiry_validation(self):
        """
        3. ตรวจสอบอายุโทเค็นการเชื่อมโยงบัญชี:
        - โทเค็นที่หมดอายุ (> 15 นาที) หรือถูกใช้แล้ว ต้องไม่สามารถใช้งานได้
        """
        # โทเค็นใหม่ยังไม่หมดอายุ
        valid_token = PatientLinkingToken.create_token(self.father, expires_in_minutes=15)
        self.assertTrue(valid_token.is_valid)

        # โทเค็นที่หมดอายุแล้ว
        expired_token = PatientLinkingToken.objects.create(
            patient=self.father,
            token='expired_token_12345',
            nonce='nonce12345',
            expires_at=timezone.now() - timedelta(minutes=5),
            is_used=False
        )
        self.assertFalse(expired_token.is_valid)

        # โทเค็นที่ถูกใช้ไปแล้ว
        used_token = PatientLinkingToken.objects.create(
            patient=self.father,
            token='used_token_12345',
            nonce='nonce67890',
            expires_at=timezone.now() + timedelta(minutes=10),
            is_used=True
        )
        self.assertFalse(used_token.is_valid)

    def test_clinical_review_item_level1_nurse_approval(self):
        """
        4. การอนุมัติ Level 1 (Intake/Triage):
        พยาบาล (Nurse) มีสิทธิ์อนุมัติและบันทึกประวัติการคัดกรองลง EMR ได้
        """
        msg = CommunicationRecord.objects.create(
            line_message_id='msg_line_test_001',
            line_user=self.line_user,
            patient=self.father,
            direction='INCOMING',
            content='คุณพ่อมีอาการไอแห้ง 3 วัน วัดไข้ได้ 37.8 C',
            is_clinical_candidate=True
        )

        review_item = ClinicalReviewItem.objects.create(
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE,
            source_message=msg,
            patient=self.father,
            status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW
        )

        # พยาบาลกดอนุมัติ Level 1 Intake
        history = review_item.approve(
            reviewer_user=self.nurse,
            clinical_summary='คัดกรองอาการทางเดินหายใจเบื้องต้น ไข้ต่ำ ไอแห้ง 3 วัน',
            category='soap'
        )

        # ตรวจสอบสถานะและ Audit Trail
        review_item.refresh_from_db()
        self.assertEqual(review_item.status, 'APPROVED')
        self.assertEqual(review_item.reviewer, self.nurse)
        self.assertEqual(review_item.reviewer_role, 'nurse')
        self.assertIsNotNone(review_item.reviewed_at)
        self.assertIsNotNone(review_item.committed_history)

        # ตรวจสอบว่าถูกบันทึกลงเวชระเบียน EMR จริง
        self.assertEqual(history.patient, self.father)
        self.assertIn('พยาบาลพรทิพย์', history.assessment)

    def test_clinical_review_item_level2_doctor_only(self):
        """
        5. การอนุมัติ Level 2 (Diagnostic/Prescription):
        - พยาบาล (Nurse) ไม่มีสิทธิ์อนุมัติ (ต้องติด PermissionDenied)
        - เฉพาะแพทย์ (Doctor) เท่านั้นที่อนุมัติได้และมีผลผูกพันทางคลินิก
        """
        msg = CommunicationRecord.objects.create(
            line_message_id='msg_line_test_002',
            line_user=self.line_user,
            patient=self.father,
            direction='INCOMING',
            content='ส่งผลแล็บตรวจตับ ALT 65 U/L ขอปรับโมดูลบำรุงตับ',
            is_clinical_candidate=True
        )

        review_item = ClinicalReviewItem.objects.create(
            review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC,
            source_message=msg,
            patient=self.father,
            status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW
        )

        # พยาบาลพยายามกด Approve Level 2 Diagnostic -> ต้องโดนปฏิเสธทันที
        with self.assertRaises(PermissionDenied):
            review_item.approve(
                reviewer_user=self.nurse,
                clinical_summary='ปรับโมดูลตับ'
            )

        # แพทย์กด Approve Level 2 Diagnostic -> ผ่านฉลุย
        history = review_item.approve(
            reviewer_user=self.doctor,
            clinical_summary='วินิจฉัยภาวะตับอักเสบระยะเริ่มต้น แนะนำปรับแผนบำรุงตับโมดูล LIVOXY',
            category='lab'
        )

        review_item.refresh_from_db()
        self.assertEqual(review_item.status, 'APPROVED')
        self.assertEqual(review_item.reviewer, self.doctor)
        self.assertEqual(review_item.reviewer_role, 'doctor')
        self.assertEqual(history.doctor, self.doctor)
        self.assertEqual(history.patient, self.father)

    def test_liff_request_otp_success_and_audit(self):
        """
        6. Step 1 OTP Request:
        กรอก HN และเบอร์โทรที่ถูกต้อง -> ได้รับ token, masked phone และบันทึก AuditLog
        """
        payload = {
            'hn': self.father.hn,
            'phone': '0811112222',
            'role': 'FATHER',
            'line_user_id': self.line_user.line_user_id
        }

        resp = self.client.post(
            reverse('root_liff_request_otp_api'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('token', data)
        self.assertIn('081-xxx-2222', data['masked_phone'])

        # ตรวจสอบ AuditLog
        audit = AuditLog.objects.filter(action='LINE_OTP_REQUESTED').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes['hn'], self.father.hn)

    def test_liff_request_otp_phone_mismatch_fails(self):
        """
        7. Step 1 Phone Mismatch:
        กรอกเบอร์โทรผิด -> โดน Reject 400 และบันทึก LINE_BINDING_FAILED Audit
        """
        payload = {
            'hn': self.father.hn,
            'phone': '0999999999',  # เบอร์ผิด
            'role': 'FATHER',
            'line_user_id': self.line_user.line_user_id
        }

        resp = self.client.post(
            reverse('root_liff_request_otp_api'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data['status'], 'error')

        # ตรวจสอบ Failed AuditLog
        audit = AuditLog.objects.filter(action='LINE_BINDING_FAILED').first()
        self.assertIsNotNone(audit)
        self.assertIn('Phone mismatch', audit.changes['reason'])

    def test_liff_verify_otp_wrong_code_fails(self):
        """
        8. Step 2 Wrong OTP:
        ใส่รหัส OTP ผิด -> โดน Reject 400
        """
        token_obj, real_otp = PatientLinkingToken.create_otp_token(self.father)

        payload = {
            'token': token_obj.token,
            'otp': '000000',  # รหัสผิด
            'line_user_id': self.line_user.line_user_id,
            'display_name': 'แอนนี่',
            'role': 'FATHER'
        }

        resp = self.client.post(
            reverse('root_liff_verify_otp_api'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(token_obj.is_used)

    def test_liff_verify_otp_success_creates_binding_and_sets_active_patient(self):
        """
        9. Step 2 OTP Success:
        ใส่ OTP ถูกต้อง -> สร้าง LinePatientBinding ACTIVE, มาร์กโทเค็น used,
        และล็อกสำคัญ: LineUser.active_patient ต้องถูกเซ็ตหลัง Bind สำเร็จเท่านั้น
        """
        token_obj, real_otp = PatientLinkingToken.create_otp_token(self.father)

        payload = {
            'token': token_obj.token,
            'otp': real_otp,
            'line_user_id': self.line_user.line_user_id,
            'display_name': 'แอนนี่ วงศ์สว่าง',
            'picture_url': 'https://example.com/pic.jpg',
            'role': 'FATHER'
        }

        resp = self.client.post(
            reverse('root_liff_verify_otp_api'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')

        # ตรวจสอบ Token ถูกใช้แล้ว
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.is_used)

        # ตรวจสอบ LinePatientBinding ถูกสร้างเป็น ACTIVE
        binding = LinePatientBinding.objects.filter(
            line_user=self.line_user,
            patient=self.father
        ).first()
        self.assertIsNotNone(binding)
        self.assertEqual(binding.status, 'ACTIVE')
        self.assertEqual(binding.role, 'FATHER')
        self.assertEqual(binding.verified_method, 'LIFF_2STEP_OTP')

        # ล็อกข้อ 3: LineUser.active_patient ต้องชี้ไปที่คนไข้ที่เพิ่งผูกสำเร็จ
        self.line_user.refresh_from_db()
        self.assertEqual(self.line_user.active_patient, self.father)

        # ล็อกข้อ 4: ตรวจสอบ PDPA AuditLog LINE_BINDING_SUCCESS
        audit = AuditLog.objects.filter(action='LINE_BINDING_SUCCESS').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes['hn'], self.father.hn)
        self.assertEqual(audit.changes['role'], 'FATHER')
        self.assertEqual(audit.changes['verified_method'], 'LIFF_2STEP_OTP')

    def test_liff_staff_assisted_fallback_and_admin_approval(self):
        """
        10. Staff-Assisted Fallback (เมื่อคนไข้ไม่มี SMS หรือกดขอให้พยาบาลยืนยัน):
        - ส่งคำขอไปยัง /liff/api/request-staff-assisted/ -> สร้าง ClinicalReviewItem PENDING_REVIEW
        - พยาบาล/เจ้าหน้าที่ อนุมัติผ่าน Admin Action -> ทำการผูก LinePatientBinding สำเร็จ
        - ล็อก Invariant: line_user.active_patient ต้องถูกเซ็ตหลัง Bind สำเร็จ
        - ล็อก PDPA AuditLog: บันทึก LINE_BINDING_SUCCESS พร้อม verified_method='STAFF_ASSISTED'
        """
        token_obj, _ = PatientLinkingToken.create_otp_token(self.father)

        payload = {
            'token': token_obj.token,
            'line_user_id': self.line_user.line_user_id,
            'display_name': 'แอนนี่ ดูแลคุณพ่อ',
            'role': 'CHILD'
        }

        resp = self.client.post(
            reverse('root_liff_request_staff_assisted_api'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        review_item_id = data['review_item_id']

        review_item = ClinicalReviewItem.objects.get(pk=review_item_id)
        self.assertEqual(review_item.status, ClinicalReviewItem.StatusChoices.PENDING_REVIEW)
        self.assertEqual(review_item.patient, self.father)

        # พยาบาลทำการ Approve ผ่าน Admin Action
        from patients.admin import ClinicalReviewItemAdmin
        from django.contrib.admin.sites import AdminSite

        class MockRequest:
            def __init__(self, user):
                self.user = user
                self.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestStaffBrowser'}
            def _messages(self):
                return []

        admin_site = AdminSite()
        model_admin = ClinicalReviewItemAdmin(ClinicalReviewItem, admin_site)
        model_admin.message_user = lambda req, msg: None

        mock_request = MockRequest(self.nurse)
        qs = ClinicalReviewItem.objects.filter(pk=review_item_id)
        model_admin.approve_staff_assisted_binding(mock_request, qs)

        # ตรวจสอบว่า Review Item ถูก Approved แล้ว
        review_item.refresh_from_db()
        self.assertEqual(review_item.status, ClinicalReviewItem.StatusChoices.APPROVED)
        self.assertEqual(review_item.reviewer, self.nurse)

        # ตรวจสอบว่า LinePatientBinding ถูกสร้างเป็น ACTIVE
        binding = LinePatientBinding.objects.filter(
            line_user=self.line_user,
            patient=self.father
        ).first()
        self.assertIsNotNone(binding)
        self.assertEqual(binding.status, 'ACTIVE')
        self.assertEqual(binding.verified_method, 'STAFF_ASSISTED')

        # ตรวจสอบ Invariant 3: active_patient ถูกเซ็ตหลัง Bind
        self.line_user.refresh_from_db()
        self.assertEqual(self.line_user.active_patient, self.father)

        # ตรวจสอบ Invariant 4: PDPA AuditLog ถูกบันทึก
        audit = AuditLog.objects.filter(action='LINE_BINDING_SUCCESS', user=self.nurse).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes['verified_method'], 'STAFF_ASSISTED')
        self.assertEqual(audit.changes['hn'], self.father.hn)

