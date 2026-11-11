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


class AIUsageLog(models.Model):
    """
    บันทึกการใช้ LLM ทุกครั้ง (token และค่าใช้จ่ายโดยประมาณ) ใช้คุมงบรายเดือนต่อผู้ให้บริการ
    ไม่เก็บเนื้อหาคำถาม/คำตอบ
    """
    provider = models.CharField(max_length=30, db_index=True)
    model_name = models.CharField(max_length=100, blank=True)
    purpose = models.CharField(max_length=50, help_text="เช่น intake_soap")
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_thb = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = 'intelligence'
        db_table = 'ai_usage_logs'
        ordering = ['-created_at']


class AssistantThread(models.Model):
    """ห้องแชทผู้ช่วย AI ของผู้ป่วย (หน้าเว็บแบบ ChatGPT) หนึ่งห้องต่อหนึ่งเรื่องที่คุย"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assistant_threads')
    title = models.CharField(max_length=120, default='แชทใหม่')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    # ส่งให้คลินิกแล้ว = เป็นส่วนหนึ่งของเวชระเบียน ลบจริงไม่ได้ ผู้ใช้ทำได้แค่ซ่อน
    submitted_box = models.OneToOneField('clinical.Box', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='assistant_thread')
    hidden_by_user = models.BooleanField(default=False)

    class Meta:
        app_label = 'intelligence'
        db_table = 'ai_assistant_threads'
        ordering = ['-updated_at']


class AssistantMessage(models.Model):
    ROLE_CHOICES = [('user', 'ผู้ใช้'), ('assistant', 'ผู้ช่วย AI')]
    thread = models.ForeignKey(AssistantThread, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    kind = models.CharField(max_length=20, blank=True, help_text="answer / out_of_scope / emergency / unavailable")
    sources = models.JSONField(default=list, blank=True)
    # ไฟล์แนบ (รูป/เสียง) ที่เข้ารหัสไว้ใน PRIVATE_MEDIA_ROOT ผ่าน media_store
    attachments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'intelligence'
        db_table = 'ai_assistant_messages'
        ordering = ['created_at']


class KnowledgeDocument(models.Model):
    """
    คลังองค์ความรู้และงานวิจัยภายนอกที่คลินิกนำเข้าเพิ่มเติม (External / Clinic Knowledge RAG)
    """
    CATEGORY_CHOICES = [
        ('research', 'งานวิจัย / บทความวิชาการ (Research Paper)'),
        ('protocol', 'โปรโตคอลการรักษาคลินิก (Clinical Protocol)'),
        ('herb_note', 'ข้อมูลสารสกัด / สมุนไพรใหม่ (Botanical & Drug Note)'),
        ('guideline', 'แนวทางเวชปฏิบัติ (Medical Guideline)'),
    ]

    title = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='research', db_index=True)
    source_name = models.CharField(max_length=200, blank=True, help_text="แหล่งที่มา เช่น PubMed, DOI, ชื่อวารสาร, ชื่อไฟล์")
    source_url = models.URLField(max_length=500, blank=True, help_text="ลิงก์อ้างอิงภายนอก (ถ้ามี)")
    content = models.TextField(help_text="เนื้อหาหลัก บทคัดย่อ หรือกลไกชีวเคมี")
    tags = models.CharField(max_length=300, blank=True, help_text="แท็กคั่นด้วยจุลภาค เช่น Axis 1, NF-kB, Curcumin")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='knowledge_documents',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'intelligence'
        db_table = 'ai_knowledge_documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

    def tag_list(self):
        return [t.strip() for t in (self.tags or '').split(',') if t.strip()]
