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

