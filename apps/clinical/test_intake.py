"""
LINE / AI Intake แบบเบา: หนึ่งรอบคุย = หนึ่ง Box, AI สรุปเมื่อกดปุ่ม, บุคลากรบันทึกเข้าเวชระเบียน
"""

import base64
import hashlib
import hmac
import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AuditLog, User
from clinical import media_store, services_intake
from clinical.models import Box
from patients.models import Patient, PatientHistory

LINE_SECRET = 'intake-test-line-secret'


def _signed_post(client, events):
    raw = json.dumps({'events': events}).encode('utf-8')
    sig = base64.b64encode(hmac.new(LINE_SECRET.encode(), raw, hashlib.sha256).digest()).decode()
    return client.post('/line/webhook/', data=raw, content_type='application/json', HTTP_X_LINE_SIGNATURE=sig)


def _text_event(user_id, msg_id, text):
    return {'type': 'message', 'replyToken': f'rt-{msg_id}', 'source': {'userId': user_id},
            'message': {'id': msg_id, 'type': 'text', 'text': text}}


class IntakeTestBase(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_dir)
        override = override_settings(PRIVATE_MEDIA_ROOT=self.media_dir, LINE_CHANNEL_SECRET=LINE_SECRET,
                                     LINE_CHANNEL_ACCESS_TOKEN='')
        override.enable()
        self.addCleanup(override.disable)
        self.patient = Patient.objects.create(hn='HN-INT-1', first_name='สมหญิง', last_name='ทดสอบ',
                                              line_user_id='U_INTAKE_1')


class LineSessionTests(IntakeTestBase):
    def test_messages_from_one_conversation_go_into_one_box(self):
        for i, text in enumerate(['ปวดหัวมา 3 วัน', 'กินยาแล้วไม่ดีขึ้น', 'นอนไม่ค่อยหลับ']):
            self.assertEqual(_signed_post(self.client, [_text_event('U_INTAKE_1', f'm{i}', text)]).status_code, 200)

        boxes = Box.objects.filter(patient=self.patient, source=Box.Source.LINE)
        self.assertEqual(boxes.count(), 1)
        box = boxes.get()
        self.assertEqual(box.status, Box.Status.DRAFT)
        self.assertEqual([m['text'] for m in box.contents['messages']],
                         ['ปวดหัวมา 3 วัน', 'กินยาแล้วไม่ดีขึ้น', 'นอนไม่ค่อยหลับ'])
        self.assertTrue(box.verify_integrity())

    def test_line_retry_does_not_duplicate_message(self):
        event = _text_event('U_INTAKE_1', 'dup1', 'ปวดหลัง')
        _signed_post(self.client, [event])
        _signed_post(self.client, [event])
        self.assertEqual(len(Box.objects.get(patient=self.patient).contents['messages']), 1)

    def test_done_closes_session_and_next_message_opens_new_box(self):
        _signed_post(self.client, [_text_event('U_INTAKE_1', 'a1', 'มีผื่นที่แขน')])
        _signed_post(self.client, [_text_event('U_INTAKE_1', 'a2', 'เสร็จแล้ว')])
        first = Box.objects.get(patient=self.patient)
        self.assertEqual(first.status, Box.Status.DONE)

        _signed_post(self.client, [_text_event('U_INTAKE_1', 'a3', 'วันนี้ผื่นลามไปที่ขา')])
        self.assertEqual(Box.objects.filter(patient=self.patient).count(), 2)

    def test_urgent_message_flags_box(self):
        _signed_post(self.client, [_text_event('U_INTAKE_1', 'u1', 'แน่นหน้าอกมาก หายใจไม่ออก')])
        self.assertTrue(Box.objects.get(patient=self.patient).contents.get('red_flag'))

    def test_unbound_user_creates_no_box(self):
        _signed_post(self.client, [_text_event('U_UNKNOWN', 'x1', 'ปวดท้องมาก')])
        self.assertFalse(Box.objects.exists())

    def test_image_is_downloaded_encrypted_and_hash_verified(self):
        png = b'\x89PNG\r\n\x1a\n' + b'fake-image-bytes'
        event = {'type': 'message', 'replyToken': 'rt-img', 'source': {'userId': 'U_INTAKE_1'},
                 'message': {'id': 'img1', 'type': 'image'}}
        with patch('patients.views_line.LineMessagingService.get_message_content', return_value=(png, 'image/png')):
            _signed_post(self.client, [event])

        meta = Box.objects.get(patient=self.patient).contents['messages'][0]['media']
        stored = (media_store._root() / meta['path']).read_bytes()
        self.assertNotIn(b'fake-image-bytes', stored)  # เก็บแบบเข้ารหัส
        self.assertEqual(media_store.read_decrypted(meta), png)


class IntakeStaffFlowTests(IntakeTestBase):
    def setUp(self):
        super().setUp()
        self.nurse = User.objects.create_user(username='nurse_int', password='NursePass2026!x', role=User.Role.NURSE)
        self.nurse.set_box_password('BoxPass2026')
        self.box = services_intake.open_session(self.patient, Box.Source.LINE)
        services_intake.append_message(self.box, 'text', text='ปวดเข่าเวลาเดินขึ้นบันได คุณสมหญิง 0812345678')
        services_intake.close_session(self.box)
        self.client.force_login(self.nurse)

    def _unlock(self):
        self.client.post(reverse('clinical:box_unlock', args=[self.box.id]), {'box_password': 'BoxPass2026'})

    def test_locked_box_hides_conversation_and_blocks_actions(self):
        resp = self.client.get(reverse('clinical:intake_detail', args=[self.box.id]))
        self.assertNotContains(resp, 'ปวดเข่า')
        self.client.post(reverse('clinical:intake_commit', args=[self.box.id]), {'subjective': 'x'})
        self.assertFalse(PatientHistory.objects.exists())

    def test_ai_summary_is_sanitized_and_stored(self):
        self._unlock()
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'success': True, 'is_fallback': False, 'gateway': 'groq-test',
                                  'soap': {'subjective': 'ปวดเข่า', 'objective': '', 'assessment': 'ข้อเข่า', 'plan': 'ตรวจเพิ่ม'}}
        with patch('clinical.services_intake.httpx.post', return_value=fake) as post:
            self.client.post(reverse('clinical:intake_summarize', args=[self.box.id]))
        sent = post.call_args.kwargs['json']['complaint']
        self.assertNotIn('0812345678', sent)
        self.assertEqual(post.call_args.kwargs['headers']['X-Internal-Token'], self.settings_token())
        self.box.refresh_from_db()
        self.assertEqual(self.box.contents['soap_source'], 'ai')
        self.assertEqual(self.box.contents['soap']['plan'], 'ตรวจเพิ่ม')

    def settings_token(self):
        from django.conf import settings
        return settings.INTERNAL_API_TOKEN

    def test_ai_fallback_is_not_saved_as_ai_draft(self):
        self._unlock()
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'success': True, 'is_fallback': True, 'gateway': 'groq-fallback',
                                  'soap': {'subjective': 'แม่แบบ', 'objective': '', 'assessment': '', 'plan': ''}}
        with patch('clinical.services_intake.httpx.post', return_value=fake):
            self.client.post(reverse('clinical:intake_summarize', args=[self.box.id]))
        self.box.refresh_from_db()
        self.assertEqual(self.box.contents.get('soap'), {})
        self.assertTrue(AuditLog.objects.filter(action='INTAKE_AI_SUMMARY_FAILED').exists())

    def test_nurse_commits_to_emr_once(self):
        self._unlock()
        soap = {'subjective': 'ปวดเข่าขวา 2 สัปดาห์', 'objective': '', 'assessment': 'สงสัยข้อเข่าเสื่อม', 'plan': 'นัดตรวจ'}
        resp = self.client.post(reverse('clinical:intake_commit', args=[self.box.id]), soap)
        self.assertRedirects(resp, reverse('patients:patient_detail', args=[self.patient.id]), fetch_redirect_response=False)

        history = PatientHistory.objects.get(patient=self.patient)
        self.assertEqual(history.doctor, self.nurse)
        self.assertEqual(history.assessment, 'สงสัยข้อเข่าเสื่อม')
        self.box.refresh_from_db()
        self.assertEqual(self.box.status, Box.Status.REVIEWED)
        self.assertEqual(self.box.emr_history, history)

        self.client.post(reverse('clinical:intake_commit', args=[self.box.id]), soap)
        self.assertEqual(PatientHistory.objects.filter(patient=self.patient).count(), 1)

    def test_media_requires_unlock(self):
        meta = media_store.save_encrypted(b'audio-bytes', 'audio/m4a', kind='line/audio')
        services_intake.append_message(self.box, 'audio', media=meta)
        url = reverse('clinical:intake_media', args=[self.box.id, meta['media_id']])
        self.assertEqual(self.client.get(url).status_code, 404)
        self._unlock()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'audio-bytes')
        self.assertTrue(AuditLog.objects.filter(action='INTAKE_MEDIA_VIEWED').exists())


class BoxDecisionAndPasswordTests(IntakeTestBase):
    def setUp(self):
        super().setUp()
        self.doctor = User.objects.create_user(username='dr_int', password='DoctorPass2026!x', role=User.Role.DOCTOR)
        self.client.force_login(self.doctor)

    def test_box_decision_requires_unlock(self):
        box = services_intake.open_session(self.patient, Box.Source.LINE)
        self.client.post(reverse('clinical:box_decision', args=[box.id]), {'decision': 'APPROVE'})
        box.refresh_from_db()
        self.assertEqual(box.decision, '')
        self.assertTrue(AuditLog.objects.filter(action='BOX_DECISION_DENIED_LOCKED').exists())

    def test_set_box_password_from_settings(self):
        url = reverse('patients:doctor_settings')
        self.client.post(url, {'action': 'set_box_password', 'current_password': 'wrong',
                               'box_password': 'NewBoxPass1', 'box_password_confirm': 'NewBoxPass1'})
        self.doctor.refresh_from_db()
        self.assertFalse(self.doctor.has_box_password)

        self.client.post(url, {'action': 'set_box_password', 'current_password': 'DoctorPass2026!x',
                               'box_password': 'NewBoxPass1', 'box_password_confirm': 'NewBoxPass1'})
        self.doctor.refresh_from_db()
        self.assertTrue(self.doctor.check_box_password('NewBoxPass1'))


class AIBudgetTests(IntakeTestBase):
    PRICES = {
        'AI_PRICE_THB_PER_1M_INPUT_GROQ': '20',
        'AI_PRICE_THB_PER_1M_OUTPUT_GROQ': '30',
        'AI_BUDGET_THB_GROQ': '1',
    }

    def setUp(self):
        super().setUp()
        self.nurse = User.objects.create_user(username='nurse_budget', password='NursePass2026!x', role=User.Role.NURSE)
        self.box = services_intake.open_session(self.patient, Box.Source.LINE)
        services_intake.append_message(self.box, 'text', text='ไอเรื้อรัง')

    def test_usage_is_priced_and_recorded(self):
        from intelligence.ai_budget import record_usage
        with patch.dict('os.environ', self.PRICES):
            log = record_usage('groq', 'm', {'prompt_tokens': 1_000_000, 'completion_tokens': 0}, 'intake_soap', self.nurse)
        self.assertEqual(float(log.estimated_cost_thb), 20.0)

    def test_summary_blocked_when_monthly_budget_used_up(self):
        from intelligence.ai_budget import record_usage
        with patch.dict('os.environ', self.PRICES), override_settings(AI_SOAP_PROVIDER='groq'):
            record_usage('groq', 'm', {'prompt_tokens': 100_000, 'completion_tokens': 0}, 'intake_soap')  # 2 บาท > งบ 1 บาท
            with patch('clinical.services_intake.httpx.post') as post:
                ok, msg = services_intake.summarize_with_ai(self.box, self.nurse)
        self.assertFalse(ok)
        self.assertIn('งบ AI', msg)
        post.assert_not_called()

    def test_tokens_logged_even_when_ai_output_unusable(self):
        from intelligence.models import AIUsageLog
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'success': True, 'is_fallback': True, 'provider': 'groq', 'model': 'x',
                                  'usage': {'prompt_tokens': 50, 'completion_tokens': 10}, 'soap': {}}
        with patch('clinical.services_intake.httpx.post', return_value=fake):
            services_intake.summarize_with_ai(self.box, self.nurse)
        self.assertEqual(AIUsageLog.objects.get().prompt_tokens, 50)
