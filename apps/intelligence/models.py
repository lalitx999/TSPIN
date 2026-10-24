"""
Models for AI Physician Assistant, Clinical Copilot, and Artifact Review Gates (EP 5).
Enforces Anti-Hallucination Grounding, Immutable Artifact Reviews, and Pillar 15 Safety Gates.
"""

from django.db import models
from django.conf import settings

class AIConsultationSession(models.Model):
    """
    เซสชันการปรึกษาเคสผู้ป่วยร่วมกับ AI Physician Assistant
    """
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='ai_consultations',
        null=True,
        blank=True,
        help_text="ผู้ป่วยที่เป็นหัวข้อการปรึกษา (ถ้ามี)"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_sessions',
        help_text="แพทย์ผู้ใช้งาน"
    )
    title = models.CharField(max_length=200, default="การปรึกษาเคสเวชศาสตร์แม่นยำ")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'intelligence'
        db_table = 'ai_consultation_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        hn = self.patient.hn if self.patient else "General"
        return f"AI Session [{hn}]: {self.title} by Dr. {self.doctor.username}"


class AIConsultationMessage(models.Model):
    """
    ข้อความการสนทนาในแต่ละเซสชัน (Prompt & Streaming Responses)
    """
    ROLE_CHOICES = [
        ('user', 'แพทย์ผู้ซักถาม (Doctor)'),
        ('assistant', 'ผู้ช่วย AI Physician'),
        ('system', 'บริบทระบบและข้อมูล EMR'),
    ]

    session = models.ForeignKey(
        AIConsultationSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    content = models.TextField(help_text="เนื้อหาข้อความ")
    grounded_axes = models.JSONField(
        default=list, 
        blank=True, 
        help_text="แกนชีวภาพ 39 แกนที่ถูกอ้างอิงในคำตอบเพื่อป้องกัน Hallucination"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = 'intelligence'
        db_table = 'ai_consultation_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:40]}..."


class AgenticArtifact(models.Model):
    """
    ชิ้นงานและผลการวิเคราะห์ของ AI ก่อนนำเข้าสู่เวชระเบียนจริง (Pillar 15: Safety Gate)
    ต้องผ่านการตรวจสอบและอนุมัติจากแพทย์ (Artifact Review) เสมอ
    """
    TYPE_CHOICES = [
        ('lab_extraction', 'ผลสแกนและสกัดค่าแล็บ (Lab OCR & Biomarkers)'),
        ('axis_recommendation', 'ข้อเสนอแนะคะแนน 39 แกนชีววิทยา (Suggested Axes)'),
        ('therapeutic_plan', 'แผนสารพฤกษเคมีและสารอาหารบำบัด (Therapeutic Plan)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'รอแพทย์ตรวจทาน (Pending Review)'),
        ('approved', 'อนุมัติเข้าแฟ้ม EMR (Approved & Applied)'),
        ('rejected', 'ปฏิเสธ (Rejected)'),
    ]

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='agentic_artifacts',
        help_text="ผู้ป่วยเจ้าของข้อมูล"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_artifacts',
        help_text="แพทย์ผู้ตรวจทาน"
    )
    artifact_type = models.CharField(max_length=50, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=250)
    proposed_data = models.JSONField(help_text="ข้อมูลที่ AI เสนอ เช่น คะแนน 39 แกน หรือค่าแล็บที่อ่านได้")
    safety_checks = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="ผลการตรวจความปลอดภัยและข้อห้ามทางการแพทย์ (Contraindications)"
    )
    doctor_notes = models.TextField(blank=True, help_text="บันทึกความเห็นหรือเหตุผลที่แพทย์ปรับปรุงแก้ไข")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'intelligence'
        db_table = 'ai_agentic_artifacts'
        ordering = ['-created_at']

    def __str__(self):
        return f"Artifact [{self.get_artifact_type_display()}]: {self.patient.hn} ({self.get_status_display()})"
