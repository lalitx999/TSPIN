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
        self.assertEqual(self.client.get(reverse('portal_patient:assistant')).status_code, 200)

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

    def test_daily_limit(self):
        from portal_patient import views_assistant
        tid = self._post('assistant_new_thread_api').json()['thread']['id']
        with patch.object(views_assistant, 'DAILY_MESSAGE_LIMIT', 2):
            self._send(tid, 'ถาม 1')
            self._send(tid, 'ถาม 2')
            self.assertEqual(self._send(tid, 'ถาม 3').status_code, 429)
