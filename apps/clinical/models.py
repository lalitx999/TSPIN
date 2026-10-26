"""
Clinical Models for TSPI 39 Biological Axes Framework & Analysis Records (EP 4).
Enforces Mechanistic Ontologies, Immutable Audit Snapshots, and Strict Doctor Approval Gates.
"""

import uuid
import hmac
import hashlib
import json
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import SoftDeleteModel

class BiologicalRecord(SoftDeleteModel):
    """
    บันทึกการประเมินคะแนน 39 แกนชีววิทยา (Mechanistic Biological Axes Record)
    ระดับคะแนน 0 - 100:
      - 0 - 39: สภาวะสมบูรณ์สูงสุด (Optimal / Balanced Homeostasis)
      - 40 - 69: ภาวะเครียดระดับเบาถึงปานกลาง (Mild to Moderate Stress)
      - 70 - 100: ความผิดปกติรุนแรง / เสื่อมสภาพ (Severe Dysfunction / Clinical Priority)
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='biological_records',
        help_text="ผู้ป่วยเจ้าของประวัติ"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluated_biological_records',
        help_text="แพทย์ผู้ประเมินและบันทึกคะแนน"
    )
    record_date = models.DateTimeField(auto_now_add=True, db_index=True)
    is_baseline = models.BooleanField(
        default=False,
        help_text="เป็นค่าพื้นฐานแรกรับ (Baseline) เพื่อใช้เปรียบเทียบความก้าวหน้า"
    )
    notes = models.TextField(blank=True, help_text="บันทึกความเห็นทางคลินิกและสมมติฐานแพทย์")

    # 39 Biological Axes (Indexed for fast aggregation & timeline)
    axis_1 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_2 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_3 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_4 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_5 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_6 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_7 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_8 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_9 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_10 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_11 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_12 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_13 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_14 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_15 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_16 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_17 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_18 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_19 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_20 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_21 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_22 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_23 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_24 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_25 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_26 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_27 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_28 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_29 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_30 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_31 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_32 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_33 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_34 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_35 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_36 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_37 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_38 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    axis_39 = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])

    # Raw Sub-axes or Omics Metadata
    sub_axes_json = models.JSONField(default=dict, blank=True, help_text="คะแนนระดับ Sub-axes A, B, C (ถ้ามี)")

    class Meta:
        app_label = 'clinical'
        db_table = 'clinical_biological_records'
        ordering = ['-record_date']
        indexes = [
            models.Index(fields=['patient', '-record_date'], condition=models.Q(is_deleted=False), name='idx_bio_pt_dt_act'),
        ]

    def __str__(self):
        return f"39-Axes Record: {self.patient.hn} on {self.record_date:%d/%m/%Y}"

    def to_scores_dict(self):
        """แปลงคะแนน 39 แกนเป็น Dictionary {1: 50, 2: 75, ...}"""
        return {i: getattr(self, f"axis_{i}") for i in range(1, 40)}

    def to_radar_list(self):
        """ส่งออกคะแนน 39 ค่าตามลำดับ เพื่อป้อนเข้า Chart.js Radar"""
        return [getattr(self, f"axis_{i}") for i in range(1, 40)]

    def get_dysfunctional_axes(self, threshold=60):
        """ดึงรายการแกนที่มีคะแนนความผิดปกติสูงกว่าเกณฑ์วิกฤต"""
        high_axes = []
        for i in range(1, 40):
            score = getattr(self, f"axis_{i}")
            if score >= threshold:
                high_axes.append({'axis_id': i, 'score': score})
        return sorted(high_axes, key=lambda x: x['score'], reverse=True)


class AnalysisRecord(SoftDeleteModel):
    """
    เอกสารวิเคราะห์และรายงานทางคลินิกแบบไม่สามารถแก้ไขย้อนหลังได้ (Immutable Clinical Snapshot)
    คุ้มครองความปลอดภัยตาม Pillar 8 & 15 เพื่อใช้ในการออกรายงาน Precision Medicine
    """
    STATUS_CHOICES = [
        ('draft', 'ฉบับร่าง (Draft Analysis)'),
        ('reviewed', 'แพทย์ตรวจสอบแล้ว (Physician Reviewed)'),
        ('approved', 'อนุมัติผลทางการแพทย์ (Clinically Approved)'),
        ('released', 'ส่งมอบรายงานให้คนไข้ (Released to Patient)'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='analysis_records',
        help_text="ผู้ป่วยเจ้าของผลการวิเคราะห์"
    )
    biological_record = models.ForeignKey(
        BiologicalRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='associated_analyses'
    )
    physician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='authorized_analyses',
        help_text="แพทย์ผู้ตรวจทานและลงนามกำกับ"
    )
    analysis_date = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True)

    # Immutable Snapshot Data
    snapshot_scores = models.JSONField(help_text="สำเนาคะแนน 39 แกนแบบแช่แข็ง ณ เวลาที่วิเคราะห์")
    key_findings = models.JSONField(default=list, blank=True, help_text="สรุปพยาธิสภาพและกลไกหลักที่พบ")
    therapeutic_plan = models.JSONField(default=list, blank=True, help_text="แผนการบำบัดด้วยสารอาหารและสารพฤกษเคมี 200 โมดูล")
    doctor_summary = models.TextField(blank=True, help_text="บทสรุปทางการแพทย์ฉบับเต็มโดยแพทย์")

    approved_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'clinical'
        db_table = 'clinical_analysis_records'
        ordering = ['-analysis_date']
        indexes = [
            models.Index(fields=['patient', 'status'], condition=models.Q(is_deleted=False), name='idx_ana_pt_stat_act'),
            models.Index(fields=['status', '-analysis_date'], condition=models.Q(is_deleted=False), name='idx_ana_stat_dt_act'),
        ]

    def __str__(self):
        return f"Analysis Snapshot: {self.patient.hn} [{self.get_status_display()}] ({self.analysis_date:%d/%m/%Y})"

    @property
    def status_badge_class(self):
        mapping = {
            'draft': 'bg-secondary-subtle text-secondary border border-secondary-subtle',
            'reviewed': 'bg-info-subtle text-info border border-info-subtle',
            'approved': 'bg-success-subtle text-success border border-success-subtle',
            'released': 'bg-primary-subtle text-primary border border-primary-subtle',
        }
        return mapping.get(self.status, 'bg-light text-dark')

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class Box(SoftDeleteModel):
    """
    Multimodal Medical Intake Box (Pillars 1, 2, 4, 8).
    Encloses multimodal raw evidence + AI synthesized SOAP and 39 axes scores
    with cryptographic HMAC-SHA256 signature sealing.
    Unlocked only by a Doctor with their Personal Box Password.
    """
    class Source(models.TextChoices):
        LINE = 'LINE', 'LINE Official Account'
        WEB = 'WEB', 'Patient Web Portal'
        CLINIC = 'CLINIC', 'Clinic Intake Terminal'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'ฉบับร่าง (Draft)'
        PROCESSING = 'processing', 'กำลังประมวลผล (Processing)'
        DONE = 'done', 'พร้อมให้แพทย์ตรวจ (Done)'
        REVIEWED = 'reviewed', 'แพทย์ตรวจแล้ว (Reviewed)'

    class Decision(models.TextChoices):
        APPROVE = 'APPROVE', 'อนุมัติตามที่เสนอ (Approve)'
        MODIFY = 'MODIFY', 'แก้ไขปรับปรุง (Modify)'
        REJECT = 'REJECT', 'ปฏิเสธ (Reject)'
        REFER = 'REFER', 'ส่งต่อแพทย์เฉพาะทาง (Refer)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.CharField(max_length=64, blank=True, help_text="HMAC-SHA256 Cryptographic Payload Signature")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WEB, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intake_boxes',
        help_text="คนไข้เจ้าของกล่องข้อมูล"
    )

    # Local Encrypted Asset references
    voice_file_path = models.CharField(max_length=500, blank=True)
    video_file_path = models.CharField(max_length=500, blank=True)
    lab_image_paths = models.JSONField(default=list, blank=True)

    # AI Synthesized Payload (SOAP + 39 Axes + Citations + Lab Markers)
    contents = models.JSONField(default=dict, help_text="SOAP + 39 Axes Scores + Citations + Lab Markers")

    # Audit & Lifecycle Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opened_boxes',
        help_text="แพทย์/บุคลากรที่เปิดกล่อง"
    )
    opened_at = models.DateTimeField(null=True, blank=True)

    # Doctor Verdict
    decision = models.CharField(max_length=20, choices=Decision.choices, blank=True)
    doctor_notes = models.TextField(blank=True)

    # Emergency Break-Glass Flag
    is_break_glass = models.BooleanField(default=False)
    break_glass_reason = models.TextField(blank=True)

    class Meta:
        app_label = 'clinical'
        db_table = 'clinical_boxes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='idx_box_status_created'),
            models.Index(fields=['patient', '-created_at'], name='idx_box_pt_created'),
        ]

    def __str__(self):
        pt_label = self.patient.hn if self.patient else "ANONYMOUS"
        return f"Box [{self.id.hex[:8]}] - {pt_label} ({self.get_status_display()})"

    def compute_hmac_signature(self, secret_key: str = None) -> str:
        """Computes HMAC-SHA256 signature over sorted canonical contents JSON."""
        key = (secret_key or getattr(settings, 'SECRET_KEY', 'tspi-box-fallback-secret')).encode('utf-8')
        canonical_payload = json.dumps(self.contents, sort_keys=True, ensure_ascii=False).encode('utf-8')
        return hmac.new(key, canonical_payload, hashlib.sha256).hexdigest()

    def verify_integrity(self, secret_key: str = None) -> bool:
        """Verifies that the Box contents have not been tampered with."""
        if not self.signature:
            return False
        expected_sig = self.compute_hmac_signature(secret_key)
        return hmac.compare_digest(self.signature, expected_sig)

    def save(self, *args, **kwargs):
        """Seals the box with cryptographic signature on save."""
        self.signature = self.compute_hmac_signature()
        super().save(*args, **kwargs)


# Harmonized Product Catalog & 39 Axes Mappings (Phase 4)
from clinical.models_catalog import ProductCategory, AxisProductMapping, CatalogImportLog

