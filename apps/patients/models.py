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
