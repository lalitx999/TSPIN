"""
LINE OA × TSPI Clinical Platform Level 2: Patient Identity & Conversation Hub Models.
Enforces Caregiver 1:N Relationship, Unified Communication Record,
and Clinical Review Queue Gate before EMR Entry (Human-in-the-loop).
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import SoftDeleteModel


class LineUser(models.Model):
    """
    ผู้ติดต่อผ่าน LINE Official Account (ผู้ป่วย หรือ ผู้ดูแล Caregiver)
    รองรับ Option B: OneToOneField กับ User (Auth) โดย null=True สำหรับผู้ป่วยทั่วไป
    """
    line_user_id = models.CharField(max_length=64, unique=True, db_index=True, help_text="LINE User ID (Uxxxxxxxx)")
    display_name = models.CharField(max_length=255, blank=True, help_text="LINE Display Name")
    picture_url = models.URLField(max_length=1000, blank=True, help_text="URL รูปโปรไฟล์จาก LINE")
    status_message = models.CharField(max_length=500, blank=True)

    # Active Patient Context: ผู้ดูแลกำลังสนทนาในบริบทของคนไข้ท่านใดอยู่
    active_patient = models.ForeignKey(
        'patients.Patient',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="คนไข้ที่กำลังเป็น Active Context ในการสนทนาปัจจุบัน"
    )

    # Option B: เชื่อมต่อบัญชีผู้ใช้ระบบ (เช่น แพทย์ พยาบาล หรือ คนไข้ที่ล็อกอิน Portal)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='line_profile',
        help_text="บัญชีผู้ใช้ระบบ (ถ้ามี เช่น บุคลากรทางการแพทย์ หรือคนไข้ Portal)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'patients'
        db_table = 'emr_line_users'
        ordering = ['-last_seen_at']

    def __str__(self):
        return f"LineUser({self.display_name or self.line_user_id[:8]})"

    @property
    def is_clinician_or_staff(self) -> bool:
        return self.user is not None and getattr(self.user, 'role', '') in ['doctor', 'nurse', 'nursing_assistant', 'staff', 'admin']


class LinePatientBinding(SoftDeleteModel):
    """
    ความสัมพันธ์ 1:N ระหว่างบัญชี LINE กับผู้ป่วยในระบบ EMR (Caregiver Model)
    อนุญาตให้ผู้ดูแล 1 คน ดูแลคนไข้ได้หลายราย (เช่น พ่อ, แม่, ลูก) โดยไม่ปะปนกัน
    """
    class RoleChoices(models.TextChoices):
        SELF = 'SELF', 'ตนเอง (Patient Self)'
        FATHER = 'FATHER', 'บิดา (Father)'
        MOTHER = 'MOTHER', 'มารดา (Mother)'
        CHILD = 'CHILD', 'บุตร/ธิดา (Child)'
        SPOUSE = 'SPOUSE', 'คู่สมรส (Spouse)'
        LEGAL_GUARDIAN = 'LEGAL_GUARDIAN', 'ผู้ปกครอง/ผู้พิทักษ์ตามกฎหมาย (Legal Guardian)'
        CAREGIVER = 'CAREGIVER', 'ผู้ดูแลหลัก (Primary Caregiver)'
        OTHER = 'OTHER', 'อื่นๆ (Other)'

    class StatusChoices(models.TextChoices):
        PENDING_VERIFICATION = 'PENDING_VERIFICATION', 'รอการยืนยันตัวตน'
        ACTIVE = 'ACTIVE', 'เปิดใช้งาน (Active)'
        SUSPENDED = 'SUSPENDED', 'ระงับชั่วคราว (Suspended)'
        REVOKED = 'REVOKED', 'ยกเลิกการเชื่อมต่อ (Revoked)'

    line_user = models.ForeignKey(
        LineUser,
        on_delete=models.CASCADE,
        related_name='patient_bindings',
        help_text="บัญชีผู้ติดต่อ LINE"
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='line_bindings',
        help_text="ผู้ป่วยในเวชระเบียน EMR"
    )
    role = models.CharField(
        max_length=30,
        choices=RoleChoices.choices,
        default=RoleChoices.SELF,
        help_text="ความสัมพันธ์ของผู้ติดต่อกับผู้ป่วย"
    )
    status = models.CharField(
        max_length=30,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING_VERIFICATION,
        db_index=True
    )
    verified_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="วิธีการยืนยันตัวตน เช่น LIFF_HN_OTP, CITIZEN_ID_4DIGIT, STAFF_IN_PERSON"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="เจ้าหน้าที่ผู้ตรวจสอบ/ยืนยันการผูกบัญชี (กรณีเจ้าหน้าที่ทำรายการ)"
    )
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'patients'
        db_table = 'emr_line_patient_bindings'
        unique_together = [('line_user', 'patient')]
        indexes = [
            models.Index(fields=['status', 'line_user']),
            models.Index(fields=['patient', 'status']),
        ]

    def __str__(self):
        return f"{self.line_user.display_name} -> {self.patient.full_name} ({self.get_role_display()}) [{self.status}]"


class CommunicationRecord(models.Model):
    """
    คลังประวัติบทสนทนาแบบแยกขาดจากเวชระเบียน (Unified Communication Log)
    ป้องกันข้อความแชทไหลลง EMR โดยไม่ผ่านการตรวจสอบ
    รองรับ Idempotency ป้องกันข้อความซ้ำจากการ Retry ของ LINE Webhook
    """
    class DirectionChoices(models.TextChoices):
        INCOMING = 'INCOMING', 'ขาเข้า (คนไข้/ผู้ดูแลส่งเข้ามา)'
        OUTGOING = 'OUTGOING', 'ขาออก (คลินิก/บอทตอบกลับ)'

    class MessageTypeChoices(models.TextChoices):
        TEXT = 'text', 'ข้อความ (Text)'
        IMAGE = 'image', 'รูปภาพ/ผลแล็บ (Image)'
        FILE = 'file', 'เอกสาร PDF/ผลตรวจ (File)'
        AUDIO = 'audio', 'เสียง (Audio)'
        LOCATION = 'location', 'ตำแหน่งที่อยู่ (Location)'
        STICKER = 'sticker', 'สติกเกอร์ (Sticker)'

    class RetentionChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'ใช้งานปกติ (Active)'
        ARCHIVED = 'ARCHIVED', 'ย้ายเข้าคลังประวัติระยะยาว (Archived 2Y+)'
        PURGED = 'PURGED', 'ลบตามสิทธิ PDPA (Purged)'

    line_message_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Message ID จาก LINE Messaging API (ป้องกัน Deduplication)"
    )
    line_user = models.ForeignKey(
        LineUser,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="ผู้ติดต่อ LINE"
    )
    patient = models.ForeignKey(
        'patients.Patient',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='communication_logs',
        help_text="ผู้ป่วยเจ้าของบริบทการสนทนา (Set NULL หากลบคนไข้ เพื่อเก็บ Audit)"
    )
    direction = models.CharField(max_length=15, choices=DirectionChoices.choices, default=DirectionChoices.INCOMING)
    message_type = models.CharField(max_length=20, choices=MessageTypeChoices.choices, default=MessageTypeChoices.TEXT)
    content = models.TextField(blank=True, help_text="เนื้อหาข้อความหรือคำอธิบาย")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='line_messages_sent',
        help_text="บุคลากรที่ส่งข้อความขาออกจากหน้า Inbox",
    )
    media_url = models.URLField(max_length=1000, blank=True, help_text="URL ไฟล์ภาพ/เอกสารที่จัดเก็บบน Server")
    raw_payload = models.JSONField(default=dict, blank=True, help_text="Raw JSON Webhook จาก LINE Platform")
    is_clinical_candidate = models.BooleanField(
        default=False,
        db_index=True,
        help_text="ถูกตรวจพบว่าเป็นข้อมูลอาการ/ผลตรวจที่ควรนำเข้าสู่ Clinical Review Queue"
    )
    retention_status = models.CharField(max_length=20, choices=RetentionChoices.choices, default=RetentionChoices.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = 'patients'
        db_table = 'emr_communication_records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['line_user', 'direction', 'created_at']),
            models.Index(fields=['patient', 'created_at']),
            models.Index(fields=['is_clinical_candidate', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.direction}] {self.line_user.display_name}: {self.content[:30]} ({self.created_at:%d/%m %H:%M})"


class ClinicalReviewItem(SoftDeleteModel):
    """
    คิวคัดกรองทางคลินิก (Human-in-the-Loop Clinical Review Queue)
    กลไกความปลอดภัย: ห้ามข้อความแชทกลายเป็นเวชระเบียนทางการจนกว่าจะได้รับการอนุมัติ
    แยกสิทธิ์การอนุมัติ:
    - LEVEL_1_INTAKE: พยาบาล หรือ แพทย์ อนุมัติได้ (บันทึกสัญญาณชีพ อาการทั่วไป คัดกรอง)
    - LEVEL_2_DIAGNOSTIC: แพทย์เท่านั้น (ผลแล็บ วินิจฉัย สั่งยา ปรับแกนชีวภาพ)
    """
    class ReviewTypeChoices(models.TextChoices):
        LEVEL_1_INTAKE = 'LEVEL_1_INTAKE', 'ระดับ 1: บันทึกคัดกรอง/อาการทั่วไป (Nurse/Doctor)'
        LEVEL_2_DIAGNOSTIC = 'LEVEL_2_DIAGNOSTIC', 'ระดับ 2: วินิจฉัย/ผลแล็บ/คำสั่งการรักษา (Doctor Only)'

    class StatusChoices(models.TextChoices):
        PENDING_REVIEW = 'PENDING_REVIEW', 'รอการตรวจสอบ (Pending Review)'
        APPROVED = 'APPROVED', 'อนุมัติลงเวชระเบียนแล้ว (Approved)'
        REJECTED = 'REJECTED', 'ปฏิเสธ/ไม่เกี่ยวข้องกับเวชระเบียน (Rejected)'
        NEEDS_MORE_INFO = 'NEEDS_MORE_INFO', 'ต้องการข้อมูลเพิ่มเติมจากคนไข้ (Needs More Info)'

    review_type = models.CharField(
        max_length=30,
        choices=ReviewTypeChoices.choices,
        default=ReviewTypeChoices.LEVEL_1_INTAKE,
        db_index=True
    )
    source_message = models.ForeignKey(
        CommunicationRecord,
        on_delete=models.PROTECT,
        related_name='review_items',
        help_text="ข้อความต้นทางจาก LINE Unified Inbox"
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='clinical_review_items',
        help_text="ผู้ป่วยเจ้าของประวัติ"
    )
    status = models.CharField(
        max_length=30,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING_REVIEW,
        db_index=True
    )

    # Audit Trail การอนุมัติ (บันทึก ณ เวลาที่ Approve)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='reviewed_clinical_items'
    )
    reviewer_role = models.CharField(
        max_length=30,
        blank=True,
        help_text="บันทึกสิทธิ์ของผู้ตรวจสอบ ณ เวลาที่อนุมัติ (doctor / nurse)"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, help_text="บันทึกหรือความเห็นของผู้ตรวจสอบ")

    # ปลายทางใน EMR: เมื่ออนุมัติแล้วจะสร้าง PatientHistory และชี้มาที่นี่
    committed_history = models.OneToOneField(
        'patients.PatientHistory',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_review_item',
        help_text="บันทึกเวชระเบียนทางการที่ถูกสร้างขึ้นใน EMR หลังการอนุมัติ"
    )
    rejection_reason = models.TextField(blank=True, help_text="เหตุผลในการปฏิเสธคำขอ")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'patients'
        db_table = 'emr_clinical_review_items'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'review_type', 'created_at']),
            models.Index(fields=['patient', 'status']),
        ]

    def __str__(self):
        return f"ReviewItem#{self.pk} [{self.get_review_type_display()}] for {self.patient.full_name} ({self.status})"

    def approve(self, reviewer_user, clinical_summary: str = "", category: str = "soap"):
        """
        อนุมัติรายการและแปลงเป็นเวชระเบียนทางการใน EMR
        บังคับใช้กฎ RBAC:
        - LEVEL_1_INTAKE: Nurse หรือ Doctor อนุมัติได้
        - LEVEL_2_DIAGNOSTIC: Doctor เท่านั้น
        """
        from django.core.exceptions import PermissionDenied
        from patients.models import PatientHistory

        if self.status == self.StatusChoices.APPROVED:
            raise ValueError("Item has already been approved and committed to EMR (Immutable).")

        user_role = getattr(reviewer_user, 'role', '').lower()

        if self.review_type == self.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC:
            if user_role not in ['doctor', 'admin']:
                raise PermissionDenied("Only licensed physicians (Doctor role) can approve Level 2 Diagnostic entries.")
        elif self.review_type == self.ReviewTypeChoices.LEVEL_1_INTAKE:
            if user_role not in ['doctor', 'nurse', 'nursing_assistant', 'admin']:
                raise PermissionDenied("Clinical staff authorization required (Nurse or Doctor role).")

        # บันทึก Audit
        self.reviewer = reviewer_user
        self.reviewer_role = user_role
        self.reviewed_at = timezone.now()
        self.status = self.StatusChoices.APPROVED

        # สร้างประวัติการรักษาทางการใน EMR
        clinical_note = clinical_summary or self.source_message.content
        history = PatientHistory.objects.create(
            patient=self.patient,
            doctor=reviewer_user if user_role == 'doctor' else None,
            subjective=f"ข้อมูลแจ้งผ่าน LINE OA (ผู้ส่ง: {self.source_message.line_user.display_name}): {self.source_message.content}",
            objective=f"ข้อความคัดกรองทางคลินิก: {clinical_note}",
            assessment=f"ผ่านการตรวจทานและรับรองโดย {reviewer_user.get_full_name() or reviewer_user.username} [{user_role.upper()}]",
            plan="ติดตามผลการดูแลทางคลินิกอย่างต่อเนื่อง"
        )

        self.committed_history = history
        self.save()
        return history
