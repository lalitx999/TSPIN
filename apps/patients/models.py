"""
Patient EMR & Clinical Records Models for TSPI Clinic (Pillars 2, 5, 8).
Enforces Relational Integrity, Thai ID Protection, and Complete Audit Trail.
"""

from datetime import date
from django.db import models
from django.conf import settings

class Patient(models.Model):
    """
    เวชระเบียนผู้ป่วย (Patient Master Record)
    รองรับการระบุตัวตนด้วย HN และเข้ารหัสความปลอดภัยตามมาตรฐาน PDPA
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
        help_text="SHA-256 Hash ของเลขบัตรประชาชน 13 หลัก"
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
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['status', '-created_at']),
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


class PatientHistory(models.Model):
    """
    บันทึกการตรวจรักษาและการติดตามผลของแพทย์ (SOAP Clinical Notes)
    """
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

    def __str__(self):
        doc_name = self.doctor.get_full_name() if self.doctor else "Unknown Doctor"
        return f"SOAP Note: {self.patient.hn} on {self.visit_date:%d/%m/%Y} by {doc_name}"


class Appointment(models.Model):
    """
    ตารางนัดหมายแพทย์
    """
    STATUS_CHOICES = [
        ('scheduled', 'นัดหมายล่วงหน้า (Scheduled)'),
        ('confirmed', 'ยืนยันการนัดแล้ว (Confirmed)'),
        ('completed', 'เข้าพบแพทย์แล้ว (Completed)'),
        ('cancelled', 'ยกเลิกนัด (Cancelled)'),
    ]

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

    def __str__(self):
        return f"Appt: {self.patient.full_name} on {self.appointment_date} at {self.appointment_time}"

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

