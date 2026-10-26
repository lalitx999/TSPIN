"""
Patient EMR & Clinical Records Models for TSPI Clinic (Pillars 2, 5, 8).
Enforces Relational Integrity, Thai ID Protection, and Complete Audit Trail.
"""

from datetime import date
import uuid
import hashlib
from typing import Optional
from django.db import models
from django.conf import settings
from core.models import SoftDeleteModel, ClinicalEncryption

class Patient(SoftDeleteModel):
    """
    เวชระเบียนผู้ป่วย (Patient Master Record)
    รองรับการระบุตัวตนด้วย HN และเข้ารหัสความปลอดภัยตามมาตรฐาน PDPA (Two-Tier ID Protection)
    """
    GENDER_CHOICES = [
        ('M', 'ชาย (Male)'),
        ('F', 'หญิง (Female)'),
        ('O', 'อื่นๆ (Other)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'รอดำเนินการ (Pending)'),
        ('urgent', 'เคสด่วนเฝ้าระวัง (Urgent)'),
        ('medicine', 'รับการบำบัด/ยา (Active Therapy)'),
        ('completed', 'เสร็จสิ้นการรักษา (Completed)'),
    ]

    BLOOD_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('UNKNOWN', 'ไม่ระบุ'),
    ]

    # Public Non-Predictable Identifier (Anti-IDOR)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)

    # Primary Medical Identifiers
    hn = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Hospital Number (หมายเลขประจำตัวผู้ป่วย)"
    )
    id_card_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 Hash ของเลขบัตรประชาชน 13 หลัก สำหรับค้นหาแบบ Exact Match"
    )
    id_card_encrypted = models.TextField(
        blank=True,
        null=True,
        help_text="AES-256 Fernet Encrypted ID Card สำหรับถอดรหัสมาแสดงผลเฉพาะผู้มีสิทธิ์"
    )

    # Personal Information
    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=5, choices=GENDER_CHOICES, default='O')
    birth_date = models.DateField(null=True, blank=True)
    blood_type = models.CharField(max_length=10, choices=BLOOD_CHOICES, default='UNKNOWN')

    # User Account Linking (Pillar 2)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_record',
        help_text="บัญชีผู้ใช้เข้าสู่ระบบ Patient Portal"
    )

    # Contact Details
    phone = models.CharField(max_length=30, db_index=True)
    email = models.EmailField(blank=True, null=True)
    line_user_id = models.CharField(max_length=150, blank=True, null=True, db_index=True)

    # Clinical Status & Notes
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', db_index=True)
    allergies = models.TextField(blank=True, help_text="ประวัติการแพ้ยา สารอาหาร และข้อห้ามทางการแพทย์")
    chief_complaint = models.TextField(blank=True, help_text="อาการสำคัญหรือสาเหตุที่มารับการรักษา")
    medical_history = models.TextField(blank=True, help_text="โรคประจำตัวและประวัติการผ่าตัด")

    # Metadata & Extensibility
    extra_data = models.JSONField(default=dict, blank=True, help_text="ข้อมูลผลแล็บดิบและพารามิเตอร์เสริม")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'patients'
        db_table = 'emr_patients'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['first_name', 'last_name'], condition=models.Q(is_deleted=False), name='idx_pt_name_act'),
            models.Index(fields=['status', '-created_at'], condition=models.Q(is_deleted=False), name='idx_pt_stat_dt_act'),
            models.Index(fields=['hn'], condition=models.Q(is_deleted=False), name='idx_pt_hn_act'),
            models.Index(fields=['phone'], condition=models.Q(is_deleted=False), name='idx_pt_phone_act'),
        ]

    def __str__(self):
        return f"[{self.hn}] {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        """คำนวณอายุอัตโนมัติจากวันเดือนปีเกิด"""
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    def set_id_card(self, raw_id: str):
        """ตั้งค่าเลขบัตร ปชช. ทั้งแบบ Hash สำหรับค้นหา และ AES Encrypted สำหรับแสดงผล"""
        if not raw_id:
            self.id_card_hash = ""
            self.id_card_encrypted = None
            return
        cleaned = raw_id.strip().replace('-', '').replace(' ', '')
        self.id_card_hash = hashlib.sha256(cleaned.encode('utf-8')).hexdigest()
        self.id_card_encrypted = ClinicalEncryption.encrypt(cleaned)

    def get_id_card(self) -> Optional[str]:
        """ถอดรหัสเลขบัตรประชาชน 13 หลักกลับมา"""
        return ClinicalEncryption.decrypt(self.id_card_encrypted)

    @property
    def masked_id_card(self) -> str:
        """เลขบัตรประชาชนแบบปิดบังเพื่อความปลอดภัยตาม PDPA เช่น 1-xxxx-xxxxx-04-6"""
        raw = self.get_id_card()
        if not raw or len(raw) != 13:
            return "x-xxxx-xxxxx-xx-x"
        return f"{raw[0]}-xxxx-xxxxx-{raw[10:12]}-{raw[12]}"

    @property
    def status_badge_class(self) -> str:
        """CSS Badge Class สำหรับสถานะคนไข้ ไม่ต้องเขียน if ซ้อนใน HTML"""
        mapping = {
            'urgent': 'badge bg-danger-subtle text-danger border border-danger',
            'medicine': 'badge bg-primary-subtle text-primary border border-primary',
            'completed': 'badge bg-success-subtle text-success border border-success',
            'pending': 'badge bg-warning-subtle text-warning-emphasis border border-warning',
        }
        return mapping.get(self.status, 'badge bg-light text-dark border')

    @property
    def status_label(self) -> str:
        """ป้ายชื่อสถานะภาษาไทย"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class PatientHistory(SoftDeleteModel):
    """
    บันทึกการตรวจรักษาและการติดตามผลของแพทย์ (SOAP Clinical Notes)
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='histories',
        help_text="ผู้ป่วยเจ้าของประวัติ"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_histories',
        help_text="แพทย์ผู้บันทึกการรักษา"
    )
    visit_date = models.DateTimeField(auto_now_add=True, db_index=True)

    # SOAP Framework
    subjective = models.TextField(blank=True, help_text="S: ข้อมูลอาการที่คนไข้บอกเล่า ความรู้สึก ความเจ็บปวด")
    objective = models.TextField(blank=True, help_text="O: ข้อมูลที่ตรวจพบ ผลแล็บ การตรวจร่างกาย สัญญาณชีพ")
    assessment = models.TextField(blank=True, help_text="A: การประเมินของแพทย์ สมมติฐานโรค แกนชีวภาพที่มีปัญหา")
    plan = models.TextField(blank=True, help_text="P: แผนการรักษา การสั่งจ่ายสารอาหารบำบัด ยา นัดติดตามผล")

    # Vitals Summary (ความดัน ชีพจร อุณหภูมิ นน. สส.)
    vitals = models.JSONField(default=dict, blank=True, help_text="BP, Pulse, Temp, Weight, Height, BMI, SpO2")

    class Meta:
        app_label = 'patients'
        db_table = 'emr_patient_histories'
        ordering = ['-visit_date']
        indexes = [
            models.Index(fields=['patient', '-visit_date'], condition=models.Q(is_deleted=False), name='idx_hist_pt_dt_act'),
        ]

    def __str__(self):
        doc_name = self.doctor.get_full_name() if self.doctor else "Unknown Doctor"
        return f"SOAP Note: {self.patient.hn} on {self.visit_date:%d/%m/%Y} by {doc_name}"


class Appointment(SoftDeleteModel):
    """
    ตารางนัดหมายแพทย์
    """
    STATUS_CHOICES = [
        ('scheduled', 'นัดหมายล่วงหน้า (Scheduled)'),
        ('confirmed', 'ยืนยันการนัดแล้ว (Confirmed)'),
        ('completed', 'เข้าพบแพทย์แล้ว (Completed)'),
        ('cancelled', 'ยกเลิกนัด (Cancelled)'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctor_appointments'
    )
    appointment_date = models.DateField(db_index=True)
    appointment_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, help_text="บันทึกจุดประสงค์การนัดหมาย")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'patients'
        db_table = 'emr_appointments'
        ordering = ['appointment_date', 'appointment_time']
        indexes = [
            models.Index(fields=['appointment_date', 'status'], condition=models.Q(is_deleted=False), name='idx_appt_dt_stat_act'),
            models.Index(fields=['patient', 'appointment_date'], condition=models.Q(is_deleted=False), name='idx_appt_pt_dt_act'),
        ]

    def __str__(self):
        return f"Appt: {self.patient.full_name} on {self.appointment_date} at {self.appointment_time}"

    @property
    def status_badge_class(self) -> str:
        """CSS Badge Class สำหรับสถานะนัดหมาย"""
        mapping = {
            'scheduled': 'badge bg-primary-subtle text-primary border border-primary',
            'confirmed': 'badge bg-success-subtle text-success border border-success',
            'completed': 'badge bg-secondary-subtle text-secondary border',
            'cancelled': 'badge bg-danger-subtle text-danger border border-danger',
        }
        return mapping.get(self.status, 'badge bg-light text-dark border')

    @property
    def status_label(self) -> str:
        """ป้ายชื่อสถานะนัดหมายภาษาไทย"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

from datetime import date, timedelta
from django.utils import timezone
import secrets

class PatientLinkingToken(models.Model):
    """
    โทเค็นสำหรับเชื่อมโยงบัญชี LINE OA หรือลงทะเบียน Patient Portal แบบปลอดภัย (Pillars 1, 14)
    ป้องกันการสวมรอยบัญชีด้วย One-time Nonce และระบบหมดอายุตามเวลาที่กำหนด
    """
    ACTION_CHOICES = [
        ('line_binding', 'เชื่อมต่อบัญชี LINE OA'),
        ('portal_access', 'ยืนยันตัวตนเข้าใช้งาน Patient Portal'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='linking_tokens',
        help_text="ผู้ป่วยเจ้าของคำขอเชื่อมโยงบัญชี"
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="โทเค็นสุ่มความปลอดภัยสูง"
    )
    nonce = models.CharField(
        max_length=32,
        db_index=True,
        help_text="One-time Nonce สำหรับป้องกัน Replay Attack"
    )
    action_type = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        default='line_binding'
    )
    is_used = models.BooleanField(
        default=False,
        help_text="ถูกใช้งานแล้วหรือไม่ (ใช้ได้ครั้งเดียวเท่านั้น)"
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="เวลาหมดอายุของโทเค็น"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'patients'
        db_table = 'emr_patient_linking_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Token({self.action_type}) for {self.patient.hn} - Used: {self.is_used}"

    @property
    def is_valid(self) -> bool:
        """ตรวจสอบความถูกต้อง: ยังไม่ถูกใช้และยังไม่หมดอายุ"""
        return not self.is_used and timezone.now() < self.expires_at

    @classmethod
    def create_token(cls, patient: Patient, action_type: str = 'line_binding', expires_in_minutes: int = 15) -> 'PatientLinkingToken':
        """สร้างโทเค็นใหม่ที่ปลอดภัยสูงและมีอายุการใช้งานจำกัด"""
        return cls.objects.create(
            patient=patient,
            token=secrets.token_urlsafe(32),
            nonce=secrets.token_hex(16),
            action_type=action_type,
            expires_at=timezone.now() + timedelta(minutes=expires_in_minutes)
        )

    @classmethod
    def create_otp_token(cls, patient: Patient, expires_in_minutes: int = 15) -> tuple['PatientLinkingToken', str]:
        """
        สร้างคำขอ 2-Step OTP Verification สำหรับ LIFF Binding
        สุ่ม OTP 6 หลัก และสร้าง Token UUID
        """
        otp = f"{secrets.randbelow(900000) + 100000}"
        token_str = secrets.token_urlsafe(32)
        obj = cls.objects.create(
            patient=patient,
            token=token_str,
            nonce=otp,
            action_type='line_binding',
            expires_at=timezone.now() + timedelta(minutes=expires_in_minutes)
        )
        return obj, otp

    def verify_otp(self, input_otp: str) -> bool:
        """ตรวจสอบความถูกต้องของ OTP ด้วย constant-time comparison ป้องกัน Timing Attacks"""
        if not self.is_valid:
            return False
        return secrets.compare_digest(str(self.nonce).strip(), str(input_otp).strip())


# Re-export Level 2 LINE OA & Caregiver Models
from .models_line import (
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
)

