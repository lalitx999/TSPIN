"""
Core Base Models and Security Utilities for TSPI Clinic.
Provides Soft Delete, QuerySet Filtering, and Fernet AES-256 Encryption.
"""

import base64
import hashlib
from typing import Optional
from django.db import models
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet


class ClinicalEncryption:
    """
    ระบบเข้ารหัสข้อมูลทางการแพทย์สองทาง (Two-Way AES-256 Fernet Encryption)
    ใช้สำหรับข้อมูลอ่อนไหวระดับบุคคล เช่น เลขบัตรประชาชนตัวจริง (PDPA Protection)
    """
    _fernet = None

    @classmethod
    def get_cipher(cls) -> Fernet:
        if cls._fernet is None:
            # Derive deterministic 32-byte key from Django SECRET_KEY
            secret = getattr(settings, 'FERNET_KEY', None)
            if not secret:
                secret_raw = settings.SECRET_KEY.encode('utf-8')
                derived_key = hashlib.sha256(secret_raw).digest()
                secret = base64.urlsafe_b64encode(derived_key)
            cls._fernet = Fernet(secret)
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """เข้ารหัสข้อความเป็น Ciphertext ปลอดภัย"""
        if not plaintext:
            return ""
        cipher = cls.get_cipher()
        return cipher.encrypt(plaintext.strip().encode('utf-8')).decode('utf-8')

    @classmethod
    def decrypt(cls, ciphertext: str) -> Optional[str]:
        """ถอดรหัส Ciphertext กลับมาเป็น Plaintext"""
        if not ciphertext:
            return None
        try:
            cipher = cls.get_cipher()
            return cipher.decrypt(ciphertext.strip().encode('utf-8')).decode('utf-8')
        except Exception:
            return None


class SoftDeleteQuerySet(models.QuerySet):
    """
    QuerySet ที่รองรับ Soft Delete เป็นค่าเริ่มต้น
    """
    def delete(self):
        """Soft delete ทั้ง QuerySet"""
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        """ลบข้อมูลออกจากฐานข้อมูลจริงอย่างถาวร (สำหรับสิทธิ์ Right to Erasure ของ PDPA)"""
        return super().delete()

    def restore(self):
        """กู้คืนข้อมูลที่ถูก Soft Delete กลับมา"""
        return self.update(is_deleted=False, deleted_at=None)

    def alive(self):
        """กรองเฉพาะข้อมูลที่ยังไม่ถูกลบ"""
        return self.filter(is_deleted=False)

    def dead(self):
        """กรองเฉพาะข้อมูลที่ถูก Soft Delete ไปแล้ว"""
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """
    Manager เริ่มต้นที่จะกรองเฉพาะข้อมูลที่ยังไม่ถูก Soft Delete เสมอ
    """
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def alive(self):
        return self.get_queryset()

    def deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=True)

    def all_with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)



class SoftDeleteModel(models.Model):
    """
    Abstract Model สำหรับเวชระเบียนทางการแพทย์ทั้งหมด
    ห้ามลบข้อมูลทิ้งเด็ดขาด (Compliance with Medical Council & PDPA regulations)
    """
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="ระบุว่ารายการนี้ถูกลบแบบซอฟต์ดีลีทหรือไม่"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="วันและเวลาที่ทำรายการลบ"
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete รายการนี้"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """ลบจริงทางกายภาพออกจากตาราง (Physical Delete)"""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """กู้คืนข้อมูลกลับสู่สถานะปกติ"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class MedicalArticle(SoftDeleteModel):
    """
    บทความ สาระสุขภาพ และข่าวสารทางการแพทย์ (Clinical Insights & News)
    เผยแพร่โดยแพทย์หรือแอดมิน เพื่อให้ความรู้ประชาชนบนหน้า Landing Page
    """
    CATEGORY_CHOICES = [
        ('systems_biology', '39 แกนชีววิทยา & เวชศาสตร์แม่นยำ'),
        ('immune_recovery', 'ภูมิคุ้มกันบำบัด & การอักเสบระดับเซลล์'),
        ('metabolic_longevity', 'เมตาบอลิซึม & ชะลอวัยระดับเซลล์'),
        ('gut_microbiome', 'ระบบทางเดินอาหาร & ไมโครไบโอม'),
        ('clinical_news', 'ข่าวสารคลินิก & นวัตกรรมการแพทย์'),
    ]

    title = models.CharField(max_length=255, help_text="หัวข้อบทความ")
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, help_text="URL Slug")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_articles',
        help_text="ผู้เขียนบทความ (แพทย์หรือแอดมิน)"
    )
    author_name = models.CharField(
        max_length=150,
        default="นพ. ผู้เชี่ยวชาญ คณะแพทย์ TSPI Clinic",
        help_text="ชื่อแพทย์หรือผู้เขียนบทความสำหรับแสดงผล"
    )
    author_title = models.CharField(
        max_length=150,
        default="แพทย์ผู้เชี่ยวชาญด้านเวชศาสตร์แม่นยำและชีววิทยาระบบ",
        blank=True
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='systems_biology',
        db_index=True
    )
    excerpt = models.TextField(help_text="บทคัดย่อสั้น (สำหรับแสดงบนการ์ดหน้าแรก)")
    content = models.TextField(help_text="เนื้อหาบทความฉบับเต็ม")
    cover_image_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL ภาพหน้าปกบทความ"
    )
    read_time_minutes = models.PositiveIntegerField(
        default=4,
        help_text="ระยะเวลาอ่านโดยประมาณ (นาที)"
    )
    is_published = models.BooleanField(default=True, db_index=True)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    view_count = models.PositiveIntegerField(default=0)

    # SEO & Social Share (Gotcha 1)
    meta_title = models.CharField(max_length=255, blank=True, help_text="SEO Meta Title")
    meta_description = models.TextField(blank=True, help_text="SEO Meta Description สำหรับ OpenGraph / Search")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        db_table = 'core_medical_articles'
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['is_published', '-published_at'], name='idx_article_pub_dt'),
            models.Index(fields=['category', 'is_published'], name='idx_article_cat_pub'),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

    def increment_view_count(self):
        MedicalArticle.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)

