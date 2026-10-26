"""
Accounts Models for Dr. Patt Clinical EMR.
Enforces Custom User with RBAC, 2FA readiness, and Full AuditLog (Pillars 1, 2, 8).
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password

class User(AbstractUser):
    """
    Custom User Model สำหรับระบบการแพทย์ TSPI
    รองรับ Role-Based Access Control (RBAC) 5 ระดับ
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', 'ผู้ดูแลระบบ (Admin)'
        DOCTOR = 'doctor', 'แพทย์ผู้รักษา (Doctor)'
        NURSE = 'nurse', 'พยาบาล (Nurse)'
        STAFF = 'staff', 'เจ้าหน้าที่คลินิก (Staff)'
        PATIENT = 'patient', 'คนไข้ (Patient)'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
        db_index=True,
        help_text="สิทธิ์การเข้าถึงระบบ"
    )
    
    phone = models.CharField(
        max_length=30,
        blank=True,
        help_text="เบอร์โทรศัพท์สำหรับติดต่อและแจ้งเตือน"
    )
    
    id_card_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 Hash ของเลขบัตรประชาชน (ป้องกันการเก็บ Plaintext ใน Auth Model)"
    )
    
    email_verified = models.BooleanField(
        default=False,
        help_text="ยืนยันอีเมลแล้วหรือไม่ (บังคับตาม Pillar 1)"
    )
    
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text="เปิดใช้งาน 2FA TOTP หรือไม่ (บังคับสำหรับ Admin/Doctor)"
    )
    
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP Address ล่าสุดที่ทำการล็อกอิน"
    )

    box_password_hash = models.CharField(
        max_length=128,
        blank=True,
        help_text="Cryptographic Hash (bcrypt/argon2) สำหรับปลดล็อกกล่องประวัติคนไข้ส่วนตัว"
    )

    must_change_password = models.BooleanField(
        default=True,
        help_text="บังคับเปลี่ยนรหัสผ่านในการเข้าใช้งานครั้งแรก"
    )

    class Meta:
        app_label = 'accounts'
        db_table = 'auth_users'
        verbose_name = 'ผู้ใช้งานระบบ'
        verbose_name_plural = 'ผู้ใช้งานระบบทั้งหมด'

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name or self.username} ({self.get_role_display()})"

    @property
    def is_clinical_staff(self):
        """ตรวจสอบว่าเป็นบุคลากรทางการแพทย์ (หมอ/พยาบาล/แอดมิน) หรือไม่"""
        return self.role in [self.Role.ADMIN, self.Role.DOCTOR, self.Role.NURSE]

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def has_box_password(self) -> bool:
        """ตรวจสอบว่าแพทย์/เจ้าหน้าที่ได้ตั้งรหัสผ่านสำหรับเปิดกล่องแล้วหรือไม่"""
        return bool(self.box_password_hash)

    def set_box_password(self, raw_box_password: str, save: bool = True):
        """ตั้งค่ารหัสผ่านเปิดกล่องส่วนตัว (เข้ารหัส bcrypt/argon2 ตาม Django Hashers)"""
        if not raw_box_password or len(raw_box_password.strip()) < 6:
            raise ValueError("รหัสผ่านเปิดกล่องต้องมีความยาวอย่างน้อย 6 ตัวอักษร")
        self.box_password_hash = make_password(raw_box_password.strip())
        if save:
            self.save(update_fields=['box_password_hash'])

    def check_box_password(self, raw_box_password: str) -> bool:
        """ตรวจสอบรหัสผ่านเปิดกล่องส่วนตัว"""
        if not self.box_password_hash or not raw_box_password:
            return False
        return check_password(raw_box_password.strip(), self.box_password_hash)


class AuditLog(models.Model):
    """
    บันทึก Audit Trail ของระบบตามมาตรฐาน PDPA & HIPAA (Pillar 8)
    ห้ามบันทึก Password, Token หรือข้อมูลบัตรเครดิตเด็ดขาด
    """
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="ผู้กระทำการ (Actor)"
    )
    action = models.CharField(
        max_length=100,
        db_index=True,
        help_text="การกระทำ เช่น USER_LOGIN, EMR_VIEW, REPORT_APPROVE"
    )
    model = models.CharField(
        max_length=100,
        blank=True,
        help_text="ชื่อโมเดลเป้าหมาย เช่น Patient, AnalysisRecord"
    )
    object_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID ของข้อมูลที่ถูกกระทำ"
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="รายละเอียดการเปลี่ยนแปลงข้อมูล (Diff)"
    )
    client_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP Address ของผู้เรียกใช้งาน"
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        help_text="เบราว์เซอร์หรืออุปกรณ์ของผู้เรียกใช้งาน"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="วันเวลาที่เกิดเหตุการณ์"
    )

    class Meta:
        app_label = 'accounts'
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        actor = self.user.username if self.user else "ANONYMOUS"
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {actor} -> {self.action} on {self.model}:{self.object_id}"
