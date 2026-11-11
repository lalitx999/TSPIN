"""
ผู้ช่วย AI แบบแชทสำหรับผู้ป่วย: ตอบจากความรู้ของ TSPI เท่านั้น, จัดการห้องแชท, ส่งให้คลินิก
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from clinical.models import Box
from intelligence.models import AssistantThread
from patients.models import Patient


class AssistantServiceTests(TestCase):
    """AI service endpoint: ฉุกเฉินไม่เรียก LLM, เอกสาร TSPI เป็นหลัก + ความรู้ทั่วไปแยกหัวข้อ, นอกเรื่องปฏิเสธ"""

    def setUp(self):
        from starlette.testclient import TestClient
        from ai_service.config import config as ai_config
        from ai_service.main import app
        self.client_ai = TestClient(app)
        self.client_ai.__enter__()  # รัน startup เพื่อโหลดฐานความรู้
        self.addCleanup(self.client_ai.__exit__, None, None, None)
        self.headers = {'X-Internal-Token': ai_config.INTERNAL_API_TOKEN}

    def _ask(self, text):
        return self.client_ai.post('/api/ai/assistant/chat', headers=self.headers,
                                   json={'messages': [{'role': 'user', 'content': text}]}).json()

    def _llm(self, content):
        return AsyncMock(return_value={'success': True, 'content': content, 'provider': 'groq', 'model': 'm',
                                       'usage': {'prompt_tokens': 100, 'completion_tokens': 20}})

    def test_off_topic_refused(self):
        with patch('ai_service.main.gateway.call_chat', new=self._llm('OUT_OF_SCOPE')):
            data = self._ask('ช่วยเขียนโค้ด python ให้หน่อย')
        self.assertEqual(data['kind'], 'out_of_scope')
        self.assertNotIn('OUT_OF_SCOPE', data['answer'])

    def test_health_question_without_clinic_docs_gets_general_answer(self):
        fake = self._llm('ข้อมูลทั่วไปเพิ่มเติม (จาก AI ไม่ใช่เอกสารของคลินิก):\nไข้หวัดมักหายเองใน 7 วัน')
        with patch('ai_service.main.gateway.call_chat', new=fake), \
                patch('ai_service.main.retrieve_tspi_knowledge', return_value=[]):
            data = self._ask('ไข้หวัดหายเองได้ไหม')
        self.assertEqual(data['kind'], 'general')
        self.assertEqual(data['sources'], [])
        self.assertIn('ไม่พบเอกสารของคลินิก', fake.call_args.kwargs['messages'][-1]['content'])

    def test_emergency_answered_without_llm(self):
        with patch('ai_service.main.gateway.call_chat', new=AsyncMock()) as llm:
            data = self._ask('แน่นหน้าอกมาก หายใจไม่ออก')
        self.assertEqual(data['kind'], 'emergency')
        self.assertIn('1669', data['answer'])
        llm.assert_not_called()

    def test_in_scope_question_grounded_in_tspi_knowledge(self):
        fake = self._llm('ลำไส้รั่วคือภาวะที่เยื่อบุลำไส้ซึมผ่านง่าย [1]')
        with patch('ai_service.main.gateway.call_chat', new=fake):
            data = self._ask('ลำไส้รั่วคืออะไร 0812345678')
        self.assertEqual(data['kind'], 'answer')
        self.assertTrue(data['sources'])
        prompt = fake.call_args.kwargs['messages'][-1]['content']
        self.assertIn('<ความรู้>', prompt)
        self.assertNotIn('0812345678', prompt)  # ลบข้อมูลระบุตัวตนก่อนส่ง LLM
        self.assertIn('ห้ามอ้างว่าเป็นข้อมูลของคลินิก', fake.call_args.kwargs['messages'][0]['content'])

    def test_image_chat_uses_gemini_vision_with_face_blur(self):
        import base64
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (40, 40), color=(200, 120, 120)).save(buf, format='JPEG')
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        fake = self._llm('สังเกตเห็นรอยแดงเบื้องต้น กรุณาเล่าอาการคันร่วมด้วยค่ะ')
        with patch('ai_service.main.gateway.call_gemini_chat', new=fake) as vis:
            resp = self.client_ai.post('/api/ai/assistant/chat', headers=self.headers, json={
                'messages': [{'role': 'user', 'content': 'ช่วยดูผื่นนี้หน่อย'}],
                'images_base64': [{'data': b64, 'mime_type': 'image/jpeg'}],
            })
        data = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertIn('รอยแดง', data['answer'])
        self.assertTrue(vis.call_args.kwargs['images'])
        self.assertIn('ห้ามวินิจฉัยโรคจากภาพ', vis.call_args.args[0])

    def test_voice_endpoint_marks_simulated_when_gateway_fails(self):
        fake_fail = AsyncMock(return_value={'success': False, 'error': 'GEMINI_API_KEY_MISSING', 'content': 'simulated'})
        with patch('ai_service.main.gateway.call_gemini_audio', new=fake_fail):
            resp = self.client_ai.post('/api/intake/voice', headers=self.headers,
                                       data={'consent_granted': 'true'},
                                       files={'file': ('v.webm', b'1234', 'audio/webm')})
        data = resp.json()
        self.assertTrue(data['simulated'])

    def test_voice_endpoint_strips_verbose_headers_on_real_transcript(self):
        verbose = 'ถอดความเสียงพูดภาษาไทยของคนไข้: "สวัสดีครับ เจ็บคอ"\n\nคำศัพท์อาการที่ครบถ้วน:\n1. เจ็บคอ'
        fake_ok = AsyncMock(return_value={'success': True, 'content': verbose})
        with patch('ai_service.main.gateway.call_gemini_audio', new=fake_ok):
            resp = self.client_ai.post('/api/intake/voice', headers=self.headers,
                                       data={'consent_granted': 'true'},
                                       files={'file': ('v.webm', b'1234', 'audio/webm')})
        data = resp.json()
        self.assertFalse(data['simulated'])
        self.assertEqual(data['sanitized_transcript'], 'สวัสดีครับ เจ็บคอ')


class AssistantThreadApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pt_asst', password='PatientPass2026!x', role=User.Role.PATIENT)
        self.patient = Patient.objects.create(hn='HN-ASST-1', first_name='ผู้ป่วย', last_name='ทดสอบ', user=self.user)
        self.client.force_login(self.user)

    def _post(self, name, thread_id=None, body=None):
        args = [thread_id] if thread_id else []
        return self.client.post(reverse(f'portal_patient:{name}', args=args), data=json.dumps(body or {}),
                                content_type='application/json')

    def _send(self, thread_id, text, answer='คำตอบจากความรู้คลินิก'):
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'answer': answer, 'kind': 'answer', 'sources': ['แกนที่ 16'],
                                  'provider': 'groq', 'model': 'm', 'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
        with patch('portal_patient.views_assistant.httpx.post', return_value=fake):
            return self._post('assistant_send_api', thread_id, {'text': text})

    def test_page_renders(self):
        resp = self.client.get(reverse('portal_patient:assistant'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'fa-edit')
        self.assertNotContains(resp, 'fa-pen-to-square')

    def test_patient_assistant_sends_anonymous_patient_context_without_pii(self):
        self.patient.allergies = 'แพ้กุ้ง'
        self.patient.save(update_fields=['allergies'])
        tid = self._post('assistant_new_thread_api').json()['thread']['id']
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'answer': 'รับทราบค่ะ', 'kind': 'answer', 'sources': [],
                                  'provider': 'groq', 'model': 'm', 'usage': {}}
        with patch('portal_patient.views_assistant.httpx.post', return_value=fake) as post:
            self._post('assistant_send_api', tid, {'text': 'ขอบคุณสำหรับข้อมูล'})
        sent = post.call_args.kwargs['json']
        self.assertEqual(sent['patient_context']['allergies'], 'แพ้กุ้ง')
        self.assertNotIn('ผู้ป่วย', json.dumps(sent['patient_context'], ensure_ascii=False))
        self.assertNotIn('HN-ASST-1', json.dumps(sent['patient_context'], ensure_ascii=False))

    def test_chat_flow_saves_history_and_titles_thread(self):
        tid = self._post('assistant_new_thread_api').json()['thread']['id']
        resp = self._send(tid, 'ลำไส้รั่วคืออะไร')
        self.assertEqual(resp.status_code, 200)
        thread = AssistantThread.objects.get(pk=tid)
        self.assertEqual(thread.title, 'ลำไส้รั่วคืออะไร')
        self.assertEqual([m.role for m in thread.messages.all()], ['user', 'assistant'])

    def test_cannot_read_another_users_thread(self):
        other = User.objects.create_user(username='pt_other', password='PatientPass2026!x', role=User.Role.PATIENT)
        foreign = AssistantThread.objects.create(user=other)
        self.assertEqual(self.client.get(reverse('portal_patient:assistant_thread_api', args=[foreign.pk])).status_code, 404)
        self.assertEqual(self._send(foreign.pk, 'x').status_code, 404)

    def test_delete_unsubmitted_removes_thread(self):
        tid = self._post('assistant_new_thread_api').json()['thread']['id']
        self.assertTrue(self._post('assistant_delete_api', tid).json()['deleted'])
        self.assertFalse(AssistantThread.objects.filter(pk=tid).exists())

    def test_submit_creates_intake_box_and_delete_only_hides(self):
        tid = self._post('assistant_new_thread_api').json()['thread']['id']
        self._send(tid, 'ปวดท้องมาสามวัน')
        self.assertEqual(self._post('assistant_submit_api', tid).status_code, 200)
        box = Box.objects.get(patient=self.patient, source=Box.Source.WEB)
        self.assertEqual(box.status, Box.Status.DONE)
        self.assertEqual(box.contents['messages'][0]['text'], 'ปวดท้องมาสามวัน')

        result = self._post('assistant_delete_api', tid).json()
        self.assertFalse(result['deleted'])
        self.assertTrue(AssistantThread.objects.get(pk=tid).hidden_by_user)
        self.assertTrue(Box.objects.filter(pk=box.pk).exists())  # เวชระเบียนยังอยู่

    def test_burst_limit_and_continuous_chat(self):
        from portal_patient import views_assistant
        tid = self._post('assistant_new_thread_api').json()['thread']['id']
        with patch.object(views_assistant, 'BURST_LIMIT_PER_MINUTE', 2):
            self._send(tid, 'ถาม 1')
            self._send(tid, 'ถาม 2')
            self.assertEqual(self._send(tid, 'ถาม 3').status_code, 429)

    def test_patient_can_upload_image_and_audio_but_not_video_and_idor_blocked(self):
        import io
        import tempfile
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings

        img_buf = io.BytesIO()
        Image.new('RGB', (32, 32), color=(180, 90, 90)).save(img_buf, format='JPEG')
        img_file = SimpleUploadedFile('rash.jpg', img_buf.getvalue(), content_type='image/jpeg')
        aud_file = SimpleUploadedFile('voice.webm', b'RIFF0000WEBP', content_type='audio/webm;codecs=opus')
        vid_file = SimpleUploadedFile('clip.mp4', b'0000', content_type='video/mp4')

        with tempfile.TemporaryDirectory() as tmpdir, override_settings(PRIVATE_MEDIA_ROOT=tmpdir):
            tid = self._post('assistant_new_thread_api').json()['thread']['id']

            # วิดีโอต้องถูกปฏิเสธ
            r_vid = self.client.post(reverse('portal_patient:assistant_send_api', args=[tid]),
                                     {'text': 'ส่งวิดีโอ', 'audio': vid_file})
            self.assertEqual(r_vid.status_code, 400)

            # รูป + เสียง ทำงานสำเร็จ เข้ารหัสเก็บ และเปิดดูได้เฉพาะเจ้าของ
            fake_voice = MagicMock(status_code=200)
            fake_voice.json.return_value = {'success': True, 'sanitized_transcript': 'มีผื่นคันที่แขนมาสามวัน'}
            fake_chat = MagicMock(status_code=200)
            fake_chat.json.return_value = {'answer': 'รับทราบค่ะ ควรให้แพทย์ตรวจเพิ่มเติม', 'kind': 'general',
                                           'sources': [], 'provider': 'gemini', 'model': 'm', 'usage': {}}

            def _mock_post(url, **kwargs):
                return fake_voice if '/api/intake/voice' in url else fake_chat

            with patch('portal_patient.views_assistant.httpx.post', side_effect=_mock_post):
                r_ok = self.client.post(reverse('portal_patient:assistant_send_api', args=[tid]),
                                        {'text': 'ช่วยดูหน่อย', 'images': [img_file], 'audio': aud_file})
            self.assertEqual(r_ok.status_code, 200)
            user_msg = r_ok.json()['messages'][0]
            self.assertEqual(len(user_msg['attachments']), 2)
            self.assertIn('มีผื่นคันที่แขนมาสามวัน', user_msg['content'])

            # เจ้าของเปิดดูไฟล์แนบได้
            att_url = user_msg['attachments'][0]['url']
            self.assertEqual(self.client.get(att_url).status_code, 200)

            # ผู้ป่วยคนอื่นเปิดดูไม่ได้ (IDOR)
            other = User.objects.create_user(username='pt_other2', password='PatientPass2026!x', role=User.Role.PATIENT)
            self.client.force_login(other)
            self.assertEqual(self.client.get(att_url).status_code, 404)

            # กลับมาเป็นเจ้าของแล้วส่งเข้าคลินิก -> Box มีทั้งข้อความและไฟล์แนบ
            self.client.force_login(self.user)
            self.assertEqual(self._post('assistant_submit_api', tid).status_code, 200)
            box = Box.objects.get(patient=self.patient, source=Box.Source.WEB)
            kinds = [m['kind'] for m in box.contents['messages']]
            self.assertIn('image', kinds)
            self.assertIn('audio', kinds)
