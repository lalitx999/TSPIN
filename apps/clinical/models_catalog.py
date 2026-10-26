"""
Clinical Product Catalog & 39 Axes Harmonization Models (Phase 4).
Represents the 42 Product Categories, Botanical Modules, and 39 Axes Cross-Mapping.
"""

from django.db import models
from core.models import SoftDeleteModel


class ProductCategory(SoftDeleteModel):
    """
    42 หมวดผลิตภัณฑ์สารอาหารและไฟโตเคมีคอลมาตรฐาน TSPI
    นำเข้าจากเอกสารแพทย์และตาราง Excel 'หมวดผลิตภัณฑ์ต้นฉบับ'
    """
    category_number = models.PositiveIntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True, help_text="ชื่อหมวดผลิตภัณฑ์ (เช่น 1. Inflammation Balance)")
    description = models.TextField(blank=True, help_text="คำอธิบายและขอบเขตทางคลินิกของหมวด")
    items_raw = models.TextField(blank=True, help_text="รายชื่อผลิตภัณฑ์ทั้งหมดในหมวดนี้")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clinical'
        db_table = 'clinical_product_categories'
        ordering = ['category_number']

    def __str__(self):
        return f"[{self.category_number}] {self.name}"

    @property
    def product_list(self):
        """แยกรายชื่อผลิตภัณฑ์ออกมาเป็น List สะอาด"""
        if not self.items_raw:
            return []
        lines = [line.strip() for line in self.items_raw.replace('\r', '').split('\n') if line.strip()]
        return lines


class AxisProductMapping(SoftDeleteModel):
    """
    ตารางจับคู่ 39 แกนชีวภาพ × 42 หมวดผลิตภัณฑ์ (57 แถวจับคู่)
    เป็นแหล่งความจริงในการแนะนำตำรับสารอาหารและผลิตภัณฑ์ตามคะแนนความผิดปกติของแกน
    """
    axis_id = models.PositiveIntegerField(db_index=True, help_text="หมายเลขแกนชีววิทยา (1-39)")
    axis_name = models.CharField(max_length=255, db_index=True, help_text="ชื่อแกนชีวภาพมาตรฐาน")
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='axis_mappings',
        help_text="หมวดผลิตภัณฑ์ที่แมปตรงกับแกนนี้"
    )
    category_name = models.CharField(max_length=255, blank=True, help_text="ชื่อหมวดที่ปรากฏในตาราง Excel")
    scope_status = models.CharField(max_length=100, default="ตรงขอบเขต", help_text="สถานะความตรงขอบเขต (เช่น ตรงขอบเขต / ขยายขอบเขต)")
    recommended_products = models.TextField(blank=True, help_text="รายการผลิตภัณฑ์ที่แนะนำสำหรับแกนนี้")
    source_notes = models.TextField(blank=True, help_text="หมายเหตุและแหล่งข้อมูลอ้างอิง")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clinical'
        db_table = 'clinical_axis_product_mappings'
        ordering = ['axis_id', 'id']
        indexes = [
            models.Index(fields=['axis_id', 'is_deleted'], name='idx_ax_map_ax_act'),
        ]

    def __str__(self):
        return f"Axis {self.axis_id} -> {self.category_name}"


class CatalogImportLog(models.Model):
    """
    บันทึกประวัติการนำเข้าตาราง Excel ผลิตภัณฑ์ (Gotcha 5: Auditable Import Log)
    """
    file_name = models.CharField(max_length=255)
    imported_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_dry_run = models.BooleanField(default=False)
    categories_count = models.PositiveIntegerField(default=0)
    mappings_count = models.PositiveIntegerField(default=0)
    summary = models.TextField(blank=True)

    class Meta:
        app_label = 'clinical'
        db_table = 'clinical_catalog_import_logs'
        ordering = ['-imported_at']

    def __str__(self):
        status_str = "DRY-RUN" if self.is_dry_run else "LIVE"
        return f"[{status_str}] {self.file_name} ({self.imported_at:%Y-%m-%d %H:%M}) - Cats: {self.categories_count}, Maps: {self.mappings_count}"
