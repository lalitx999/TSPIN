"""
ฟอร์มบันทึกการตรวจในหน้าแฟ้มคนไข้: สัญญาณชีพบังคับ, ร่างต่อผู้ใช้, รูปเข้ารหัส,
Gemini สรุป SOAP (ข้อมูลระบุตัวตนไม่หลุด), ต้องยืนยันการตรวจทานก่อนบันทึกเข้าเวชระเบียน
"""

import io
import json
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import AuditLog, User
from clinical import media_store, services_visit
from clinical.models import Box
from intelligence.models import AIUsageLog
from patients.forms import VisitVitalsForm
from patients.models import Patient, PatientHistory

VITALS = {'bp_systolic': '128', 'bp_diastolic': '82', 'pulse': '76', 'temperature': '36.8',
          'weight_kg': '64', 'height_cm': '160', 'spo2': '97'}
SOAP = {'subjective': 'ปวดท้องขวาล่าง 2 วัน', 'objective': 'BP 128/82', 'assessment': 'ควรตรวจเพิ่ม', 'plan': 'ตรวจเลือด'}


def _png(color=(200, 80, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (40, 30), color).save(buf, format='PNG')
    return buf.getvalue()


def _gemini_ok(soap=None):
    fake = MagicMock(status_code=200)
    fake.json.return_value = {'success': True, 'soap': soap or SOAP, 'gateway': 'gemini:gemini-2.5-flash',
                              'provider': 'gemini', 'model': 'gemini-2.5-flash', 'images_sent': 1,
                              'usage': {'prompt_tokens': 900, 'completion_tokens': 200}}
    return fake


class VisitVitalsFormTests(TestCase):
    def test_all_vitals_required(self):
        form = VisitVitalsForm({**VITALS, 'spo2': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('กรุณากรอกออกซิเจนปลายนิ้ว (SpO2)', form.error_list())

    def test_out_of_range_and_inverted_pressure_rejected(self):
        self.assertFalse(VisitVitalsForm({**VITALS, 'temperature': '65'}).is_valid())
        form = VisitVitalsForm({**VITALS, 'bp_diastolic': '130'})
        self.assertFalse(form.is_valid())
        self.assertIn('bp_diastolic', form.errors)

    def test_bmi_is_calculated(self):
        form = VisitVitalsForm(VITALS)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.vitals()['bmi'], 25.0)


class VisitFlowTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_dir)
        override = override_settings(PRIVATE_MEDIA_ROOT=self.media_dir)
        override.enable()
        self.addCleanup(override.disable)
        self.patient = Patient.objects.create(hn='HN-VIS-1', first_name='มานี', last_name='ใจดี', phone='0811111111')
        self.nurse = User.objects.create_user(username='nurse_visit', password='NursePass2026!x', role=User.Role.NURSE)
        self.client.force_login(self.nurse)

    def url(self, name):
        return reverse(f'patients:{name}', args=[self.patient.pk])

    def save(self, **extra):
        resp = self.client.post(self.url('visit_save'), {'history_text': 'ปวดเข่าซ้ายมาก โทร 0812345678', **VITALS, **extra})
        self.assertEqual(resp.status_code, 200)
        return resp.json()['box_id']

    def test_autosave_creates_one_draft_per_user_and_page_restores_it(self):
        box_id = self.save()
        self.assertEqual(self.save(box_id=box_id), box_id)
        box = Box.objects.get(pk=box_id)
        self.assertEqual(box.contents['origin'], 'visit')
        self.assertEqual(box.opened_by, self.nurse)
        page = self.client.get(reverse('patients:patient_detail', args=[self.patient.pk]))
        self.assertContains(page, box_id)
        self.assertContains(page, 'visitForm(')

    def test_other_staff_cannot_touch_someone_elses_draft(self):
        box_id = self.save()
        other = User.objects.create_user(username='doc_visit', password='DocPass2026!x', role=User.Role.DOCTOR)
        self.client.force_login(other)
        resp = self.client.post(self.url('visit_summarize'), {'box_id': box_id, **VITALS})
        self.assertEqual(resp.status_code, 404)
        page = self.client.get(reverse('patients:patient_detail', args=[self.patient.pk]))
        self.assertContains(page, 'มีร่างของ')
        self.assertNotContains(page, 'ปวดเข่าซ้ายมาก')

    def test_images_are_encrypted_validated_and_capped(self):
        resp = self.client.post(self.url('visit_image_add'), {'image': _upload(_png())})
        self.assertTrue(resp.json()['ok'])
        box = Box.objects.get(pk=resp.json()['box_id'])
        meta = services_visit.images(box)[0]['media']
        self.assertEqual(media_store.read_decrypted(meta), _png())
        self.assertNotIn(b'IHDR', open(f"{self.media_dir}/{meta['path']}", 'rb').read())

        bad = self.client.post(self.url('visit_image_add'), {'box_id': str(box.id), 'image': _upload(b'%PDF', 'a.pdf', 'application/pdf')})
        self.assertFalse(bad.json()['ok'])
        for _ in range(5):
            self.client.post(self.url('visit_image_add'), {'box_id': str(box.id), 'image': _upload(_png())})
        over = self.client.post(self.url('visit_image_add'), {'box_id': str(box.id), 'image': _upload(_png())})
        self.assertIn('สูงสุด 6 รูป', over.json()['error'])

        remove = self.client.post(self.url('visit_image_remove'), {'box_id': str(box.id), 'media_id': meta['media_id']})
        self.assertTrue(remove.json()['ok'])
        box.refresh_from_db()
        self.assertEqual(len(services_visit.images(box)), 5)
        self.assertIsNotNone(media_store.read_decrypted(meta))  # ไม่ลบไฟล์จริง

    def test_summarize_requires_complete_vitals(self):
        box_id = self.save()
        resp = self.client.post(self.url('visit_summarize'), {'box_id': box_id, 'history_text': 'ปวดหัว', **VITALS, 'pulse': ''})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('pulse', resp.json()['fields'])

    def test_summarize_sends_deidentified_text_vitals_and_images_to_gemini(self):
        box_id = self.client.post(self.url('visit_image_add'), {'image': _upload(_png())}).json()['box_id']
        with patch('clinical.services_visit.httpx.post', return_value=_gemini_ok()) as post:
            resp = self.client.post(self.url('visit_summarize'),
                                    {'box_id': box_id, 'history_text': 'ปวดท้อง โทร 0812345678', **VITALS})
        self.assertTrue(resp.json()['ok'])
        self.assertEqual(resp.json()['soap']['subjective'], SOAP['subjective'])
        call = post.call_args
        self.assertTrue(call.args[0].endswith('/api/ai/visit/soap'))
        self.assertNotIn('0812345678', call.kwargs['data']['history'])
        self.assertEqual(json.loads(call.kwargs['data']['vitals'])['bmi'], 25.0)
        self.assertEqual(len(call.kwargs['files']), 1)
        box = Box.objects.get(pk=box_id)
        self.assertEqual(box.contents['soap_source'], 'ai')
        self.assertTrue(AIUsageLog.objects.filter(provider='gemini', purpose='visit_soap').exists())

    def test_ai_failure_offers_manual_soap(self):
        box_id = self.save()
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'success': False, 'error': 'GEMINI_API_KEY_MISSING'}
        with patch('clinical.services_visit.httpx.post', return_value=fake):
            resp = self.client.post(self.url('visit_summarize'), {'box_id': box_id, 'history_text': 'ปวดหัว', **VITALS})
        self.assertEqual(resp.status_code, 502)
        self.assertTrue(resp.json()['can_manual'])
        self.assertTrue(self.client.post(self.url('visit_manual'), {'box_id': box_id}).json()['ok'])
        self.assertEqual(Box.objects.get(pk=box_id).contents['soap_source'], 'manual')

    def test_commit_needs_summary_and_review_then_saves_vitals_once(self):
        box_id = self.save()
        early = self.client.post(self.url('visit_commit'), {'box_id': box_id, 'reviewed': '1', **VITALS, **SOAP})
        self.assertIn('ก่อนบันทึก', early.json()['error'])

        with patch('clinical.services_visit.httpx.post', return_value=_gemini_ok()):
            self.client.post(self.url('visit_summarize'), {'box_id': box_id, 'history_text': 'ปวดท้อง', **VITALS})
        unreviewed = self.client.post(self.url('visit_commit'), {'box_id': box_id, 'reviewed': '0', **VITALS, **SOAP})
        self.assertIn('ติ๊กยืนยัน', unreviewed.json()['error'])
        self.assertFalse(PatientHistory.objects.exists())

        edited = {**SOAP, 'plan': 'ตรวจ CBC และนัดติดตาม'}
        resp = self.client.post(self.url('visit_commit'), {'box_id': box_id, 'reviewed': '1', **VITALS, **edited})
        self.assertTrue(resp.json()['ok'])
        self.assertIn('BP: 128/82', resp.json()['html'])
        history = PatientHistory.objects.get()
        self.assertEqual(history.doctor, self.nurse)
        self.assertEqual(history.plan, 'ตรวจ CBC และนัดติดตาม')
        self.assertEqual(history.vitals['spo2'], 97)
        self.assertEqual(history.vitals['bmi'], 25.0)
        box = Box.objects.get(pk=box_id)
        self.assertEqual(box.status, Box.Status.REVIEWED)
        self.assertEqual(box.decision, Box.Decision.MODIFY)  # แก้จากร่าง AI
        again = self.client.post(self.url('visit_commit'), {'box_id': box_id, 'reviewed': '1', **VITALS, **edited})
        self.assertFalse(again.json()['ok'])
        self.assertEqual(PatientHistory.objects.count(), 1)

    def test_discard_soft_deletes_draft(self):
        box_id = self.save()
        self.assertTrue(self.client.post(self.url('visit_discard'), {'box_id': box_id}).json()['ok'])
        self.assertFalse(Box.objects.filter(pk=box_id).exists())
        self.assertTrue(Box.objects.all_with_deleted().filter(pk=box_id).exists())
        self.assertTrue(AuditLog.objects.filter(action='VISIT_DRAFT_DISCARDED').exists())


def _upload(data, name='photo.png', content_type='image/png'):
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, data, content_type=content_type)


class VisitSoapEndpointTests(TestCase):
    """ai_service: ลบข้อมูลระบุตัวตนซ้ำ, เบลอ/ลบ EXIF ในรูปก่อนส่ง Gemini, ใช้ guardrail กับ assessment"""

    def setUp(self):
        from starlette.testclient import TestClient
        from ai_service.config import config as ai_config
        from ai_service.main import app as fastapi_app
        self.api = TestClient(fastapi_app, headers={'X-Internal-Token': ai_config.INTERNAL_API_TOKEN})

    def test_images_are_sanitized_and_text_deidentified_before_gemini(self):
        reply = {'success': True, 'content': json.dumps(SOAP, ensure_ascii=False), 'provider': 'gemini',
                 'model': 'gemini-2.5-flash', 'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
        with patch('ai_service.main.gateway.call_gemini_json', new=AsyncMock(return_value=reply)) as gem, \
             patch('ai_service.main.MediaSanitizer.blur_faces', side_effect=lambda b, safety_margin: (b, 0)) as blur:
            resp = self.api.post('/api/ai/visit/soap', data={'history': 'ปวดหัว โทร 0899999999', 'vitals': json.dumps({'pulse': 80})},
                                 files=[('images', ('a.png', _png(), 'image/png'))])
        body = resp.json()
        self.assertTrue(body['success'])
        self.assertEqual(body['images_sent'], 1)
        blur.assert_called_once()
        sent_text = gem.call_args.args[1]
        self.assertNotIn('0899999999', sent_text)
        self.assertIn('ชีพจร: 80', sent_text)
        self.assertEqual(gem.call_args.kwargs['images'][0]['mime_type'], 'image/jpeg')

    def test_no_gemini_key_reports_failure_not_fake_soap(self):
        with patch('ai_service.gateway.config.is_gemini_available', return_value=False):
            resp = self.api.post('/api/ai/visit/soap', data={'history': 'ปวดหัว', 'vitals': '{}'})
        self.assertFalse(resp.json()['success'])
        self.assertNotIn('soap', resp.json())

    def test_empty_input_rejected(self):
        self.assertEqual(self.api.post('/api/ai/visit/soap', data={'history': '', 'vitals': '{}'}).status_code, 400)
