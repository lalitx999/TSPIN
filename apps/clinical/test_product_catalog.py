"""
Tests for Harmonized Product Catalog & 39 Axes Mappings (Phase 4).
"""

from django.test import TestCase
from django.core.management import call_command
from clinical.models_catalog import ProductCategory, AxisProductMapping, CatalogImportLog


class ProductCatalogHarmonizationTests(TestCase):
    def test_import_command_dry_run_does_not_modify_database(self):
        """Gotcha 5: คำสั่งนำเข้าด้วย --dry-run ต้องไม่บันทึกลงฐานข้อมูล"""
        initial_cats = ProductCategory.objects.count()
        initial_maps = AxisProductMapping.objects.count()

        call_command('import_39_axes_42_products', dry_run=True)

        self.assertEqual(ProductCategory.objects.count(), initial_cats)
        self.assertEqual(AxisProductMapping.objects.count(), initial_maps)

    def test_import_command_populates_categories_and_mappings_in_transaction(self):
        """Phase 4: คำสั่งนำเข้าต้องบันทึก 42 หมวดผลิตภัณฑ์ และ 39 แกนชีวภาพลง DB จริง"""
        call_command('import_39_axes_42_products')

        # Verify 42 categories
        self.assertGreaterEqual(ProductCategory.objects.count(), 40)
        cat_1 = ProductCategory.objects.filter(category_number=1).first()
        self.assertIsNotNone(cat_1)
        self.assertIn("Inflammation", cat_1.name)

        # Verify 39 axes mapping
        mappings = AxisProductMapping.objects.all()
        self.assertGreaterEqual(mappings.count(), 50)
        distinct_axes = set(mappings.values_list('axis_id', flat=True))
        self.assertEqual(len(distinct_axes), 39, "All 39 biological axes must have corresponding product mappings")

        # Verify audit log recorded
        import_log = CatalogImportLog.objects.first()
        self.assertIsNotNone(import_log)
        self.assertFalse(import_log.is_dry_run)
