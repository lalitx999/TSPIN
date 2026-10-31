"""
Unit Tests for Public Core Pages & Base Layout Rendering (Pillars 2, 4, 15).
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class CorePagesLayoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(
            username='doctor_test',
            email='doc@tspi.test',
            password='ComplexDocPassword2026!',
            role=User.Role.DOCTOR
        )
        self.patient = User.objects.create_user(
            username='1100400123456',
            email='patient@tspi.test',
            password='ComplexPatientPassword2026!',
            role=User.Role.PATIENT
        )

    def test_home_page_renders_200(self):
        """หน้าหลัก Landing Page ต้องแสดงผลได้ปกติ (HTTP 200)"""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')
        self.assertTemplateUsed(response, 'layouts/public_base.html')
        self.assertContains(response, "TSPI CLINIC")

    def test_about_page_renders_200(self):
        """หน้าเกี่ยวกับคลินิก ต้องแสดงผลได้ปกติ (HTTP 200)"""
        response = self.client.get(reverse('core:about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/about.html')

    def test_privacy_page_renders_200(self):
        """หน้านโยบาย PDPA ต้องแสดงผลได้ปกติ (HTTP 200)"""
        response = self.client.get(reverse('core:privacy'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/privacy.html')

    def test_terms_page_renders_200(self):
        """หน้าข้อตกลงการใช้งาน ต้องแสดงผลได้ปกติ (HTTP 200)"""
        response = self.client.get(reverse('core:terms'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/terms.html')

    def test_doctor_dashboard_uses_adminlte_layout_for_doctor(self):
        """แพทย์ล็อกอินแล้วเปิดหน้า Dashboard ต้องเรนเดอร์โครงสร้าง AdminLTE doctor_base.html"""
        self.client.force_login(self.doctor)
        response = self.client.get(reverse('patients:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/dashboard.html')
        self.assertTemplateUsed(response, 'layouts/doctor_base.html')
        self.assertContains(response, "DR. PATT EMR")
        self.assertContains(response, "Clinical Overview Dashboard")

    def test_patient_dashboard_uses_patient_layout_for_patient(self):
        """คนไข้ล็อกอินแล้วเปิดหน้า Dashboard ต้องเรนเดอร์โครงสร้าง patient_base.html"""
        self.client.force_login(self.patient)
        response = self.client.get(reverse('portal_patient:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal_patient/dashboard.html')
        self.assertTemplateUsed(response, 'layouts/patient_base.html')
        self.assertContains(response, "TSPI Health")

    def test_health_check_endpoint_returns_healthy(self):
        """Pillar 6: ตรวจสอบสถานะความพร้อมระบบผ่าน /health/ ต้องคืนค่า 200 และสถานะ healthy"""
        response = self.client.get(reverse('core:health'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertEqual(data.get('database'), 'connected')
        self.assertEqual(data.get('service'), 'tspi-clinical-emr')

    def test_production_hardening_rules(self):
        """Pillar 6: ตรวจสอบการตั้งค่าความปลอดภัยระดับ Production"""
        import os
        from unittest.mock import patch

        # ตรวจสอบว่าถ้า SECRET_KEY ว่างหรือสั้นเกินไป ต้องเกิด ValueError
        with patch.dict(os.environ, {'DJANGO_SECRET_KEY': 'short', 'ALLOWED_HOSTS': 'example.com'}, clear=True):
            with self.assertRaises(ValueError):
                import importlib
                from config.settings import prod
                importlib.reload(prod)

    def test_medical_article_list_and_detail_views(self):
        """Phase 1: ตรวจสอบหน้ารวมบทความและหน้ารายละเอียดบทความทางการแพทย์"""
        from core.models import MedicalArticle

        article = MedicalArticle.objects.create(
            title="ทดสอบบทความ 39 แกนชีววิทยา",
            slug="test-39-axes-article",
            category="systems_biology",
            author_name="นพ. ทดสอบ",
            author_title="ผู้เชี่ยวชาญ",
            excerpt="บทคัดย่อทดสอบ",
            content="### หัวข้อบทความ\nข้อความเนื้อหา <script>alert('xss')</script>",
            meta_title="SEO Title Test",
            meta_description="SEO Description Test",
            is_published=True
        )

        # 1. หน้ารวมบทความ
        resp_list = self.client.get(reverse('core:article_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, "ทดสอบบทความ 39 แกนชีววิทยา")

        # 2. หน้ารายละเอียดบทความ
        resp_detail = self.client.get(reverse('core:article_detail', kwargs={'slug': article.slug}))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, "ทดสอบบทความ 39 แกนชีววิทยา")
        self.assertContains(resp_detail, "SEO Title Test")
        # Gotcha 1 Verification: nh3 must sanitize script tags
        self.assertNotContains(resp_detail, "<script>alert('xss')</script>")

        # View count should increment
        article.refresh_from_db()
        self.assertEqual(article.view_count, 1)




class EncryptionKeyRotationTests(TestCase):
    """ย้ายข้อมูลขึ้น VPS: ข้อมูลที่เข้ารหัสด้วยคีย์เดิมต้องอ่านได้ และหมุนไปคีย์ใหม่ได้"""

    def tearDown(self):
        from core.models import ClinicalEncryption
        ClinicalEncryption._fernet = None

    def test_old_data_readable_then_rotated_to_new_key(self):
        import os
        import tempfile
        from cryptography.fernet import Fernet
        from django.core.management import call_command
        from django.test import override_settings
        from core.models import ClinicalEncryption
        from patients.models import Patient

        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        with override_settings(FERNET_KEY=old_key, FERNET_OLD_KEYS=()):
            ClinicalEncryption._fernet = None
            p = Patient(hn='HN-ROT-1', first_name='a', last_name='b')
            p.set_id_card('1100400123450')
            p.save()
        old_token = Patient.objects.get(pk=p.pk).id_card_encrypted

        with override_settings(FERNET_KEY=new_key, FERNET_OLD_KEYS=(old_key,), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp()):
            ClinicalEncryption._fernet = None
            self.assertEqual(ClinicalEncryption.decrypt(old_token), '1100400123450')
            call_command('rotate_encryption_key', apply=True, stdout=open(os.devnull, 'w'))

        with override_settings(FERNET_KEY=new_key, FERNET_OLD_KEYS=()):
            ClinicalEncryption._fernet = None
            rotated = Patient.objects.get(pk=p.pk).id_card_encrypted
            self.assertNotEqual(rotated, old_token)
            self.assertEqual(ClinicalEncryption.decrypt(rotated), '1100400123450')
