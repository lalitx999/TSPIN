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
from patients import line_alerts, line_relay
from patients.line_service import make_line_register_token
from patients.models import Patient, PatientHistory
from patients.models_line import ClinicalReviewItem, CommunicationRecord, LineUser

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
        self.line_user = LineUser.objects.create(line_user_id='U_INTAKE_1', display_name='สมหญิง', bot_enabled=True)
        background = patch('patients.line_ai._run_in_background')
        self.ai_background = background.start()
        self.addCleanup(background.stop)


class LineSessionTests(IntakeTestBase):
    def setUp(self):
        super().setUp()
        _signed_post(self.client, [_text_event('U_INTAKE_1', 'start', 'เริ่ม')])

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

        _signed_post(self.client, [_text_event('U_INTAKE_1', 'a3', 'เริ่ม')])
        _signed_post(self.client, [_text_event('U_INTAKE_1', 'a4', 'วันนี้ผื่นลามไปที่ขา')])
        self.assertEqual(Box.objects.filter(patient=self.patient).count(), 2)

    def test_urgent_message_flags_box(self):
        _signed_post(self.client, [_text_event('U_INTAKE_1', 'u1', 'แน่นหน้าอกมาก หายใจไม่ออก')])
        self.assertTrue(Box.objects.get(patient=self.patient).contents.get('red_flag'))

    def test_report_command_replies_when_no_report_yet(self):
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, [_text_event('U_INTAKE_1', 'rep1', 'ดูผลตรวจ')])
        self.assertIn('ยังไม่มีผลตรวจ', json.dumps(reply.call_args.args[1], ensure_ascii=False))

    def test_unbound_user_creates_no_box(self):
        _signed_post(self.client, [_text_event('U_UNKNOWN', 'x1', 'ปวดท้องมาก')])
        self.assertFalse(Box.objects.exclude(patient=self.patient).exists())

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


class LineBotOptInTests(IntakeTestBase):
    """บอทปิดเป็นค่าเริ่มต้น เปิดได้ด้วยการพิมพ์ "เปิดใช้งานบอท" เท่านั้น และทุกคำตอบเป็น Flex ที่มีปุ่มปิดบอท"""

    def setUp(self):
        super().setUp()
        self.line_user.bot_enabled = False
        self.line_user.save()

    def _post(self, *events):
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, list(events))
        return reply

    def _postback(self, user_id, data, event_id='pb1'):
        return {'type': 'postback', 'replyToken': 'r', 'webhookEventId': event_id, 'source': {'userId': user_id},
                'postback': {'data': data}}

    def _close_labels(self, reply):
        card = reply.call_args.args[1][0]
        self.assertEqual(card['type'], 'flex')
        return [b['action']['label'] for b in card['contents'].get('footer', {}).get('contents', [])]

    def test_bot_off_stays_silent_but_message_is_stored(self):
        reply = self._post(_text_event('U_INTAKE_1', 'q1', 'มีครีมขายไหมครับ'))
        reply.assert_not_called()
        self.assertFalse(Box.objects.filter(patient=self.patient).exists())
        self.assertTrue(CommunicationRecord.objects.filter(line_message_id='q1').exists())

    def test_unknown_customer_gets_no_reply_on_follow_or_message(self):
        follow = {'type': 'follow', 'replyToken': 'r', 'source': {'userId': 'U_NEW'}}
        self._post(follow).assert_not_called()
        self._post(_text_event('U_NEW', 'q2', 'สวัสดีครับ')).assert_not_called()

    def test_only_exact_phrase_turns_bot_on(self):
        self._post(_text_event('U_INTAKE_1', 'q3', 'อยากเปิดใช้งานบอทต้องทำไง')).assert_not_called()
        self._post(_text_event('U_INTAKE_1', 'q4', 'เริ่ม')).assert_not_called()
        self.assertFalse(LineUser.objects.get(pk=self.line_user.pk).bot_enabled)

        reply = self._post(_text_event('U_INTAKE_1', 'q5', 'เปิดใช้งานบอท'))
        self.assertTrue(LineUser.objects.get(pk=self.line_user.pk).bot_enabled)
        self.assertIn('ปิดบอท', self._close_labels(reply))
        self.assertTrue(AuditLog.objects.filter(action='LINE_BOT_ENABLED').exists())

    def test_every_bot_reply_is_flex_with_close_button(self):
        self.line_user.bot_enabled = True
        self.line_user.save()
        for i, text in enumerate(['เริ่ม', 'ปวดหลัง', 'แน่นหน้าอกมาก', 'ใบนัด', 'ผลตรวจ', 'ติดต่อ', 'เสร็จแล้ว']):
            reply = self._post(_text_event('U_INTAKE_1', f'all{i}', text))
            if reply.called:
                self.assertIn('ปิดบอท', self._close_labels(reply), text)

    def test_close_button_turns_bot_off_and_sends_open_session_to_staff(self):
        self.line_user.bot_enabled = True
        self.line_user.save()
        self._post(_text_event('U_INTAKE_1', 'c0', 'เริ่ม'))
        self._post(_text_event('U_INTAKE_1', 'c1', 'ปวดหลัง'))
        reply = self._post(self._postback('U_INTAKE_1', 'action=bot_off'))
        self.assertFalse(LineUser.objects.get(pk=self.line_user.pk).bot_enabled)
        self.assertEqual(Box.objects.get(patient=self.patient).status, Box.Status.DONE)
        self.assertEqual(reply.call_args.args[1][0]['type'], 'flex')
        self._post(_text_event('U_INTAKE_1', 'c2', 'ปวดอีกแล้ว')).assert_not_called()

    def test_old_card_buttons_do_not_wake_bot(self):
        self._post(self._postback('U_INTAKE_1', 'action=check_appointment')).assert_not_called()

    def test_line_retry_of_enable_command_replies_once(self):
        event = _text_event('U_INTAKE_1', 'r1', 'เปิดใช้งานบอท')
        self.assertTrue(self._post(event).called)
        self._post(event).assert_not_called()


class LineRegisterFormTests(IntakeTestBase):
    """เชื่อมบัญชีด้วยชื่อ เบอร์ ยินยอม: ระบุตัว LINE จากลิงก์ลงนาม และเบอร์ซ้ำต้องผ่านเจ้าหน้าที่"""
    USER_ID = 'Uabc123'

    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()
        self.line_new = LineUser.objects.create(line_user_id=self.USER_ID, display_name='ใหม่', bot_enabled=True)
        self.url = f"{reverse('root_line_register')}?t={make_line_register_token(self.USER_ID)}"

    def _submit(self, **overrides):
        data = {'full_name': 'สมชาย ใจดี', 'phone': '081-234-5678', 'consent': 'on', **overrides}
        with patch('patients.views_line_register.LineMessagingService.push_message', return_value=True) as push:
            return self.client.post(self.url, {k: v for k, v in data.items() if v is not None}), push

    def test_form_only_asks_name_phone_consent(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['form'].fields), ['full_name', 'phone', 'consent'])
        self.assertNotContains(response, 'liff')

    def test_bot_binding_button_opens_signed_form(self):
        self.line_new.bot_enabled = False
        self.line_new.save()
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, [_text_event(self.USER_ID, 'r1', 'เปิดใช้งานบอท')])
        card = reply.call_args.args[1][0]
        uri = card['contents']['footer']['contents'][0]['action']['uri']
        self.assertIn(reverse('root_line_register'), uri)
        self.assertEqual(self.client.get(uri).status_code, 200)

    def test_new_person_can_use_bot_right_away_and_is_greeted_by_name(self):
        self.line_new.bot_enabled = False
        self.line_new.save()
        response, push = self._submit()
        self.assertEqual(response.status_code, 302)
        patient = Patient.objects.get(line_user_id=self.USER_ID)
        self.assertEqual((patient.first_name, patient.last_name, patient.phone), ('สมชาย', 'ใจดี', '0812345678'))
        self.assertTrue(patient.extra_data['needs_staff_verification'])
        self.assertIn('pdpa_consent_at', patient.extra_data)
        self.line_new.refresh_from_db()
        self.assertEqual(self.line_new.active_patient, patient)
        self.assertTrue(self.line_new.bot_enabled)
        self.assertEqual(push.call_args.args[0], self.USER_ID)
        card = push.call_args.args[1][0]
        self.assertEqual(card['type'], 'flex')
        self.assertIn('สวัสดีครับคุณสมชาย', json.dumps(card, ensure_ascii=False))
        self.assertContains(self.client.get(self.url), 'ลงทะเบียนเรียบร้อย')

    def test_consent_and_valid_phone_are_required(self):
        response, _ = self._submit(consent=None)
        self.assertContains(response, 'กรุณากดยอมรับ')
        response, _ = self._submit(phone='12345')
        self.assertContains(response, 'เบอร์โทรศัพท์ไม่ถูกต้อง')
        self.assertFalse(Patient.objects.filter(line_user_id=self.USER_ID).exists())

    def test_existing_phone_gets_bot_now_but_never_the_old_record(self):
        existing = Patient.objects.create(hn='HN-INT-2', first_name='เดิม', last_name='คนไข้', phone='081-234-5678')
        _, push = self._submit()
        self.assertIn('สวัสดีครับคุณสมชาย', json.dumps(push.call_args.args[1], ensure_ascii=False))
        self.line_new.refresh_from_db()
        self.assertNotEqual(self.line_new.active_patient, existing)
        self.assertEqual(self.line_new.active_patient.extra_data['possible_duplicate_of_hn'], existing.hn)
        existing.refresh_from_db()
        self.assertIsNone(existing.line_user_id)
        item = ClinicalReviewItem.objects.get(patient=existing)
        self.assertIn(f'({self.USER_ID})', item.review_notes)  # รูปแบบที่ปุ่มอนุมัติใน Admin อ่านได้
        self.assertNotContains(self.client.get(self.url), existing.first_name)
        self._submit()
        self.assertEqual(ClinicalReviewItem.objects.filter(patient=existing).count(), 1)

    def test_forged_or_expired_link_is_rejected(self):
        self.assertEqual(self.client.get(reverse('root_line_register') + '?t=forged').status_code, 400)
        response = self.client.post(reverse('root_line_register') + '?t=forged',
                                    {'full_name': 'ก ข', 'phone': '0812345678', 'consent': 'on'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Patient.objects.filter(phone='0812345678').exists())
        with patch('patients.line_service.LINE_REGISTER_MAX_AGE_SECONDS', -1):
            self.assertEqual(self.client.get(self.url).status_code, 400)


class LineAiChatTests(IntakeTestBase):
    """ผู้ใช้ที่เปิดบอทแล้ว พิมพ์คำถามทั่วไป AI ตอบเป็น Flex ระหว่างเล่าอาการยังเข้ากล่องเหมือนเดิม"""

    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()
        self.ai_background.side_effect = lambda func, *args: func(*args)

    def _ask(self, text, event_id='ai1', status_code=200, data=None):
        fake = MagicMock(status_code=status_code)
        fake.json.return_value = data if data is not None else {
            'answer': 'ตอบจากเอกสาร [1]', 'kind': 'answer', 'sources': ['แกนที่ 16'], 'provider': 'groq', 'model': 'm',
            'usage': {'prompt_tokens': 5, 'completion_tokens': 3}}
        with patch('patients.line_ai.httpx.post', return_value=fake) as post, \
                patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, [_text_event('U_INTAKE_1', event_id, text)])
        return post, reply

    def test_question_answered_with_flex_sources_and_saved_for_staff(self):
        post, reply = self._ask('เบาหวานกินอะไรได้บ้าง')
        self.assertEqual(post.call_args.kwargs['json']['messages'][-1],
                         {'role': 'user', 'content': 'เบาหวานกินอะไรได้บ้าง'})
        card = reply.call_args.args[1][0]
        self.assertEqual(card['type'], 'flex')
        text = json.dumps(card, ensure_ascii=False)
        self.assertIn('ตอบจากเอกสาร [1]', text)
        self.assertIn('[1] แกนที่ 16', text)
        self.assertIn('ปิดบอท', text)
        self.assertFalse(Box.objects.filter(patient=self.patient).exists())
        self.assertTrue(CommunicationRecord.objects.filter(
            line_user=self.line_user, direction='OUTGOING', content='ตอบจากเอกสาร [1]').exists())

    def _tap_send_to_doctor(self, message_id, user_id='U_INTAKE_1', event_id='tap1'):
        event = {'type': 'postback', 'replyToken': 'r', 'webhookEventId': event_id, 'source': {'userId': user_id},
                 'postback': {'data': f'action=send_to_doctor&msg={message_id}'}}
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, [event])
        return json.dumps(reply.call_args.args[1], ensure_ascii=False)

    def test_symptom_answer_offers_send_to_doctor_and_general_question_does_not(self):
        _, reply = self._ask('ปวดหัวมา 3 วัน', event_id='sym1')
        text = json.dumps(reply.call_args.args[1], ensure_ascii=False)
        self.assertIn('ส่งอาการนี้ให้หมอ', text)
        self.assertIn('action=send_to_doctor&msg=sym1', text)
        _, reply = self._ask('คลินิกเปิดกี่โมง', event_id='gen1')
        text = json.dumps(reply.call_args.args[1], ensure_ascii=False)
        self.assertNotIn('ส่งอาการนี้ให้หมอ', text)
        self.assertIn('เล่าอาการให้คลินิก', text)

    def test_send_to_doctor_submits_message_once_with_next_steps(self):
        self._ask('ปวดหัวมา 3 วัน', event_id='sym2')
        text = self._tap_send_to_doctor('sym2')
        box = Box.objects.get(patient=self.patient)
        self.assertEqual(box.status, Box.Status.DONE)
        self.assertEqual(box.contents['messages'][0]['text'], 'ปวดหัวมา 3 วัน')
        self.assertIn('พิมพ์ถาม AI ได้เลย', text)
        self.assertIn('ส่งให้ทีมแพทย์แล้ว', self._tap_send_to_doctor('sym2', event_id='tap2'))
        self.assertEqual(Box.objects.filter(patient=self.patient).count(), 1)

    def test_send_to_doctor_cannot_take_another_users_message(self):
        self._ask('ปวดหัวมา 3 วัน', event_id='sym3')
        other = Patient.objects.create(hn='HN-INT-3', first_name='คนอื่น', last_name='ทดสอบ', phone='0899999999',
                                       line_user_id='U_OTHER')
        LineUser.objects.create(line_user_id='U_OTHER', display_name='อื่น', bot_enabled=True, active_patient=other)
        self.assertIn('ไม่พบข้อความนี้', self._tap_send_to_doctor('sym3', user_id='U_OTHER'))
        self.assertFalse(Box.objects.filter(patient=other).exists())

    def test_send_to_doctor_joins_open_session(self):
        self._ask('ปวดหัวมา 3 วัน', event_id='sym4')
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True):
            _signed_post(self.client, [_text_event('U_INTAKE_1', 's2', 'เริ่ม'), _text_event('U_INTAKE_1', 's3', 'เวียนหัวด้วย')])
        self.assertIn('เสร็จแล้ว', self._tap_send_to_doctor('sym4'))
        box = Box.objects.get(patient=self.patient)
        self.assertEqual(box.status, Box.Status.DRAFT)
        self.assertEqual(len([m for m in box.contents['messages'] if m['sender'] == 'patient']), 2)

    def test_done_card_tells_patient_what_to_do_next(self):
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, [_text_event('U_INTAKE_1', 'd1', 'เริ่ม'), _text_event('U_INTAKE_1', 'd2', 'ปวดหลัง'),
                                       _text_event('U_INTAKE_1', 'd3', 'เสร็จแล้ว')])
        text = json.dumps(reply.call_args.args[1], ensure_ascii=False)
        self.assertIn('พิมพ์ถาม AI ได้เลย', text)
        self.assertIn('ดูใบนัด', text)

    def test_next_question_sends_earlier_answer_as_context(self):
        self._ask('เบาหวานคืออะไร')
        post, _ = self._ask('กินข้าวได้ไหม', event_id='ai2')
        roles = [m['role'] for m in post.call_args.kwargs['json']['messages']]
        self.assertEqual(roles, ['user', 'assistant', 'user'])

    def test_during_intake_text_goes_to_box_not_ai(self):
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True):
            _signed_post(self.client, [_text_event('U_INTAKE_1', 's1', 'เริ่ม')])
        post, _ = self._ask('ปวดหลังมา 3 วัน')
        post.assert_not_called()
        self.assertEqual(Box.objects.get(patient=self.patient).contents['messages'][0]['text'], 'ปวดหลังมา 3 วัน')

    def test_emergency_skips_ai_and_reaches_doctors(self):
        post, reply = self._ask('แน่นหน้าอกมาก หายใจไม่ออก')
        post.assert_not_called()
        self.assertIn('1669', json.dumps(reply.call_args.args[1], ensure_ascii=False))
        self.assertTrue(Box.objects.get(patient=self.patient).contents.get('red_flag'))

    def test_service_down_replies_politely(self):
        _, reply = self._ask('เบาหวานคืออะไร', status_code=500)
        self.assertIn('ไม่พร้อมใช้งาน', json.dumps(reply.call_args.args[1], ensure_ascii=False))
        self.assertFalse(CommunicationRecord.objects.filter(line_user=self.line_user, direction='OUTGOING').exists())

    def test_daily_limit_stops_ai_calls(self):
        with patch('patients.line_ai.DAILY_LIMIT_PER_USER', 1):
            self._ask('ข้อแรก')
            post, reply = self._ask('ข้อสอง', event_id='ai2')
        post.assert_not_called()
        self.assertIn('ถามครบจำนวน', json.dumps(reply.call_args.args[1], ensure_ascii=False))

    def test_reply_failure_falls_back_to_push(self):
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'answer': 'ตอบ', 'kind': 'general', 'sources': []}
        with patch('patients.line_ai.httpx.post', return_value=fake), \
                patch('patients.views_line.LineMessagingService.reply_message', return_value=False), \
                patch('patients.views_line.LineMessagingService.push_message', return_value=True) as push:
            _signed_post(self.client, [_text_event('U_INTAKE_1', 'ai3', 'เบาหวานคืออะไร')])
        self.assertEqual(push.call_args.args[0], 'U_INTAKE_1')

    def test_bot_off_never_calls_ai(self):
        self.line_user.bot_enabled = False
        self.line_user.save()
        post, reply = self._ask('เบาหวานคืออะไร')
        post.assert_not_called()
        reply.assert_not_called()


class LinePhase2Tests(IntakeTestBase):
    """Dashboard หมอ แจ้งเตือนฉุกเฉิน แจ้งคนไข้เมื่อตรวจแล้ว และหน้าตรวจเบอร์ซ้ำ"""

    def setUp(self):
        super().setUp()
        self.ai_background.side_effect = lambda func, *args: func(*args)
        self.doctor = User.objects.create_user(username='doc_p2', password='x-Strong-pass-1', role=User.Role.DOCTOR,
                                               email='doc@tspi.test')
        self.client.force_login(self.doctor)

    def _message(self, event_id, text):
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True):
            _signed_post(self.client, [_text_event('U_INTAKE_1', event_id, text)])

    def _duplicate_request(self):
        """เบอร์ซ้ำจากฟอร์มจริง: ได้เวชระเบียนใหม่และคำขอย้าย LINE"""
        existing = Patient.objects.create(hn='HN-INT-9', first_name='เดิม', last_name='คนไข้', phone='081-234-5678')
        LineUser.objects.create(line_user_id='Uabc999', display_name='ใหม่', bot_enabled=True)
        url = f"{reverse('root_line_register')}?t={make_line_register_token('Uabc999')}"
        with patch('patients.views_line_register.LineMessagingService.push_message', return_value=True):
            self.client.post(url, {'full_name': 'สมชาย ใจดี', 'phone': '0812345678', 'consent': 'on'})
        return existing, ClinicalReviewItem.objects.get(patient=existing)

    def test_dashboard_shows_emergency_before_patient_finishes(self):
        self._message('e1', 'แน่นหน้าอกมาก หายใจไม่ออก')
        self.assertEqual(Box.objects.get(patient=self.patient).status, Box.Status.DRAFT)
        response = self.client.get(reverse('patients:dashboard'))
        self.assertContains(response, 'มีเคสฉุกเฉินจาก LINE 1 เคส')
        self.assertContains(response, reverse('clinical:intake_detail', kwargs={'box_id': Box.objects.get().id}))

    def test_dashboard_lists_finished_case_but_not_open_ordinary_session(self):
        self._message('n1', 'เริ่ม')
        self._message('n2', 'ปวดหลังนิดหน่อย')
        self.assertNotContains(self.client.get(reverse('patients:doctor_line_cases')), self.patient.hn)
        self._message('n3', 'เสร็จแล้ว')
        response = self.client.get(reverse('patients:doctor_line_cases'))
        self.assertContains(response, self.patient.hn)
        self.assertNotContains(response, 'ปวดหลัง')  # เนื้อหายังต้องปลดล็อกกล่องก่อน

    def test_line_cases_requires_clinical_staff(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('patients:doctor_line_cases')).status_code, 302)

    def test_emergency_email_once_without_patient_details(self):
        from django.core import mail
        self._message('e2', 'แน่นหน้าอกมาก')
        self._message('e3', 'หายใจไม่ออก แน่นหน้าอก')
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['doc@tspi.test'])
        self.assertNotIn(self.patient.first_name, sent.subject + sent.body)
        self.assertNotIn('แน่นหน้าอก', sent.subject + sent.body)

    def test_patient_told_when_case_saved_only_if_bot_on(self):
        box = Box.objects.create(patient=self.patient, source=Box.Source.LINE, status=Box.Status.DONE,
                                 contents={'messages': []})
        with patch('patients.line_alerts.LineMessagingService.push_message', return_value=True) as push:
            line_alerts.notify_patient_reviewed(box)
        self.assertEqual(push.call_args.args[0], 'U_INTAKE_1')
        self.assertIn('ทีมแพทย์ตรวจข้อมูลแล้ว', json.dumps(push.call_args.args[1], ensure_ascii=False))
        self.line_user.bot_enabled = False
        self.line_user.save()
        with patch('patients.line_alerts.LineMessagingService.push_message', return_value=True) as push:
            line_alerts.notify_patient_reviewed(box)
        push.assert_not_called()

    def test_link_request_only_on_its_own_page_and_queue_cannot_approve_it(self):
        existing, item = self._duplicate_request()
        self.assertNotContains(self.client.get(reverse('patients:staff_review_queue')), existing.hn)
        page = self.client.get(reverse('patients:staff_line_links'))
        self.assertContains(page, 'สมชาย ใจดี')
        self.assertContains(page, existing.hn)
        response = self.client.post(f'/staff/api/review-item/{item.pk}/approve/', {'clinical_summary': 'x'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PatientHistory.objects.filter(patient=existing).exists())

    def test_approving_moves_line_to_old_record_and_tells_patient(self):
        existing, item = self._duplicate_request()
        line_user = LineUser.objects.get(line_user_id='Uabc999')
        temporary = line_user.active_patient
        with patch('patients.line_links.LineMessagingService.push_message', return_value=True) as push:
            self.client.post(reverse('patients:staff_line_link_decide', args=[item.pk]), {'decision': 'approve'})
        line_user.refresh_from_db()
        temporary.refresh_from_db()
        existing.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(line_user.active_patient, existing)
        self.assertEqual(existing.line_user_id, 'Uabc999')
        self.assertIsNone(temporary.line_user_id)
        self.assertEqual(item.status, ClinicalReviewItem.StatusChoices.APPROVED)
        self.assertEqual(item.reviewer, self.doctor)
        self.assertFalse(PatientHistory.objects.filter(patient=existing).exists())
        self.assertEqual(push.call_args.args[0], 'Uabc999')
        self.assertTrue(AuditLog.objects.filter(action='LINE_BINDING_SUCCESS', user=self.doctor).exists())

    def test_rejecting_keeps_new_record(self):
        existing, item = self._duplicate_request()
        line_user = LineUser.objects.get(line_user_id='Uabc999')
        temporary = line_user.active_patient
        self.client.post(reverse('patients:staff_line_link_decide', args=[item.pk]), {'decision': 'reject'})
        line_user.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(line_user.active_patient, temporary)
        self.assertEqual(item.status, ClinicalReviewItem.StatusChoices.REJECTED)
        existing.refresh_from_db()
        self.assertIsNone(existing.line_user_id)


class LineEmergencyWhileBotOffTests(IntakeTestBase):
    """บอทปิดยังเงียบทุกอย่าง ยกเว้นเคสฉุกเฉินที่ต้องเตือน 1669 และแจ้งทีมแพทย์"""
    TEXT = 'แน่นหน้าอกมาก หายใจไม่ออก'

    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()
        self.ai_background.side_effect = lambda func, *args: func(*args)
        self.line_user.bot_enabled = False
        self.line_user.save()
        self.doctor = User.objects.create_user(username='doc_off', password='x-Strong-pass-1', role=User.Role.DOCTOR,
                                               email='doc@tspi.test')

    def _send(self, user_id, event_id, text):
        with patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, [_text_event(user_id, event_id, text)])
        return reply

    def test_registered_patient_warned_and_case_reaches_doctors_but_bot_stays_off(self):
        from django.core import mail
        reply = self._send('U_INTAKE_1', 'e1', self.TEXT)
        text = json.dumps(reply.call_args.args[1], ensure_ascii=False)
        self.assertIn('tel:1669', text)
        self.assertNotIn('ปิดบอท', text)
        self.assertTrue(Box.objects.get(patient=self.patient).contents['red_flag'])
        self.assertEqual(len(mail.outbox), 1)
        self.line_user.refresh_from_db()
        self.assertFalse(self.line_user.bot_enabled)
        self._send('U_INTAKE_1', 'e2', self.TEXT)
        self.assertEqual(len(mail.outbox), 1)

    def test_unregistered_customer_warned_and_shown_on_dashboard_with_one_email(self):
        from django.core import mail
        reply = self._send('U_SALES', 'u1', self.TEXT)
        self.assertIn('tel:1669', json.dumps(reply.call_args.args[1], ensure_ascii=False))
        self._send('U_SALES', 'u2', self.TEXT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn('แน่นหน้าอก', mail.outbox[0].body)
        self.assertFalse(Box.objects.exists())
        self.client.force_login(self.doctor)
        response = self.client.get(reverse('patients:doctor_line_cases'))
        self.assertContains(response, 'ลูกค้า LINE ที่ยังไม่ลงทะเบียน')
        self.assertContains(response, 'มีเคสฉุกเฉินจาก LINE 2 เคส')
        self.assertContains(response, 'user_id=U_SALES')

    def test_ordinary_message_still_silent(self):
        from django.core import mail
        self._send('U_INTAKE_1', 'n1', 'ปวดหลังนิดหน่อย มีครีมไหม').assert_not_called()
        self.assertFalse(Box.objects.exists())
        self.assertEqual(mail.outbox, [])

    @override_settings(LINE_RELAY_URL='https://old.example/webhook/')
    def test_emergency_not_forwarded_to_old_system(self):
        with patch('patients.line_relay._deliver_in_background') as deliver:
            self._send('U_SALES', 'r1', self.TEXT)
        deliver.assert_not_called()


class LineInboxMediaTests(IntakeTestBase):
    """บอทปิด: ไฟล์ถูกเก็บแบบเข้ารหัสให้เจ้าหน้าที่ดู โดยบอทยังเงียบและไม่เปิดกล่อง"""

    PNG = b'\x89PNG\r\n\x1a\n' + b'inbox-image-bytes'

    def setUp(self):
        super().setUp()
        self.line_user.bot_enabled = False
        self.line_user.save()
        self.doctor = User.objects.create_user(username='doc_media', password='x-Strong-pass-1', role=User.Role.DOCTOR)

    def _send(self, content=None, msg_type='image', msg_id='im1'):
        event = {'type': 'message', 'replyToken': 'r', 'source': {'userId': 'U_INTAKE_1'},
                 'message': {'id': msg_id, 'type': msg_type}}
        with patch('patients.views_line.LineMessagingService.get_message_content',
                   return_value=content if content is not None else (self.PNG, 'image/png')) as download, \
                patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, [event])
        return download, reply

    def test_stored_encrypted_silently_without_box(self):
        _, reply = self._send()
        reply.assert_not_called()
        self.assertFalse(Box.objects.filter(patient=self.patient).exists())
        meta = CommunicationRecord.objects.get(line_message_id='im1').raw_payload['stored_media']
        self.assertNotIn(b'inbox-image-bytes', (media_store._root() / meta['path']).read_bytes())
        self.assertEqual(media_store.read_decrypted(meta), self.PNG)

    def test_retry_does_not_download_twice(self):
        self._send()
        download, _ = self._send()
        download.assert_not_called()

    def test_download_failure_keeps_message(self):
        with patch('patients.views_line.LineMessagingService.get_message_content', return_value=None):
            _signed_post(self.client, [{'type': 'message', 'replyToken': 'r', 'source': {'userId': 'U_INTAKE_1'},
                                        'message': {'id': 'im2', 'type': 'image'}}])
        record = CommunicationRecord.objects.get(line_message_id='im2')
        self.assertNotIn('stored_media', record.raw_payload)

    def test_staff_can_view_with_audit_and_others_cannot(self):
        self._send()
        record = CommunicationRecord.objects.get(line_message_id='im1')
        url = reverse('patients:staff_inbox_media', args=[record.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        patient_user = User.objects.create_user(username='pat_media', password='x-Strong-pass-1', role=User.Role.PATIENT)
        self.client.force_login(patient_user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.doctor)
        response = self.client.get(url)
        self.assertEqual(response.content, self.PNG)
        self.assertEqual(response['Content-Disposition'], 'inline')
        self.assertTrue(AuditLog.objects.filter(action='INBOX_MEDIA_VIEWED', user=self.doctor).exists())
        page = self.client.get(reverse('patients:staff_inbox'), {'user_id': self.line_user.line_user_id})
        self.assertContains(page, url)

    def test_risky_file_type_is_downloaded_not_rendered(self):
        self._send(content=(b'<script>alert(1)</script>', 'text/html'), msg_type='file', msg_id='im3')
        record = CommunicationRecord.objects.get(line_message_id='im3')
        self.client.force_login(self.doctor)
        response = self.client.get(reverse('patients:staff_inbox_media', args=[record.pk]))
        self.assertEqual(response['Content-Disposition'], 'attachment')
        self.assertEqual(response['Content-Type'], 'application/octet-stream')


class LineQrPosterTests(TestCase):
    @override_settings(LINE_BOT_LINK_ENABLED=False, LINE_OA_ID='@testoa')
    def test_staff_get_printable_qr_of_the_opt_in_link(self):
        url = reverse('patients:staff_line_qr')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(User.objects.create_user(username='doc_qr', password='x-Strong-pass-1', role=User.Role.DOCTOR))
        response = self.client.get(url)
        self.assertContains(response, '<svg')
        self.assertContains(response, 'เปิดใช้งานบอท')
        self.assertIn('https://line.me/R/oaMessage/@testoa/?', response.context['link'])


class LineDispatchTests(TestCase):
    def test_same_user_stays_in_order_and_error_does_not_stop_queue(self):
        import threading
        from patients import line_dispatch
        seen = []
        done = threading.Event()

        def fail():
            raise RuntimeError('boom')

        with override_settings(LINE_DISPATCH_INLINE=False), patch('patients.line_dispatch.connections'):
            line_dispatch.submit('U1', seen.append, 1)
            line_dispatch.submit('U1', fail)
            line_dispatch.submit('U1', seen.append, 2)
            line_dispatch.submit('U1', done.set)
            self.assertTrue(done.wait(5))
        self.assertEqual(seen, [1, 2])

    @override_settings(LINE_CHANNEL_SECRET=LINE_SECRET, LINE_CHANNEL_ACCESS_TOKEN='', LINE_DISPATCH_INLINE=False)
    def test_webhook_saves_message_before_slow_work_runs(self):
        with patch('patients.views_line.line_dispatch.submit') as submit:
            response = _signed_post(self.client, [_text_event('U_QUEUE', 'q1', 'สวัสดี')])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CommunicationRecord.objects.filter(line_message_id='q1').exists())
        submit.assert_called_once()


@override_settings(LINE_RELAY_URL='https://old.example/webhook/')
class LineRelayTests(IntakeTestBase):
    """ระบบเก่าได้ข้อความของคนที่ไม่ได้เปิดบอทเท่านั้น สองบอทต้องไม่ตอบซ้อนกัน"""

    def setUp(self):
        super().setUp()
        self.line_user.bot_enabled = False
        self.line_user.save()

    def _post(self, *events):
        with patch('patients.line_relay._deliver_in_background') as deliver, \
                patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            response = _signed_post(self.client, list(events))
        self.assertEqual(response.status_code, 200)
        return deliver, reply

    def _forwarded_ids(self, deliver):
        _, body, signature = deliver.call_args.args
        expected = base64.b64encode(hmac.new(LINE_SECRET.encode(), body, hashlib.sha256).digest()).decode()
        self.assertEqual(signature, expected)  # ระบบเก่าใช้ secret เดียวกัน ต้องตรวจผ่าน
        return [e['message']['id'] for e in json.loads(body)['events']]

    def test_nothing_forwarded_when_url_not_set(self):
        with override_settings(LINE_RELAY_URL=''):
            deliver, _ = self._post(_text_event('U_INTAKE_1', 'n1', 'มีครีมขายไหม'))
        deliver.assert_not_called()

    def test_bot_off_message_goes_to_old_system_only(self):
        deliver, reply = self._post(_text_event('U_INTAKE_1', 'o1', 'มีครีมขายไหม'))
        self.assertEqual(self._forwarded_ids(deliver), ['o1'])
        reply.assert_not_called()

    def test_turn_on_word_and_later_messages_stay_with_our_bot(self):
        deliver, reply = self._post(_text_event('U_INTAKE_1', 'o2', 'เปิดใช้งานบอท'),
                                    _text_event('U_INTAKE_1', 'o3', 'ปวดหัว'))
        deliver.assert_not_called()
        self.assertTrue(reply.called)

    def test_mixed_batch_forwards_only_other_customer(self):
        self.line_user.bot_enabled = True
        self.line_user.save()
        deliver, _ = self._post(_text_event('U_INTAKE_1', 'o4', 'ปวดหัว'),
                                _text_event('U_SALES', 'o5', 'สั่งของครับ'))
        self.assertEqual(self._forwarded_ids(deliver), ['o5'])

    def test_after_turning_off_next_message_goes_to_old_system(self):
        self.line_user.bot_enabled = True
        self.line_user.save()
        off = {'type': 'postback', 'replyToken': 'r', 'webhookEventId': 'p1', 'source': {'userId': 'U_INTAKE_1'},
               'postback': {'data': 'action=bot_off'}}
        deliver, _ = self._post(off, _text_event('U_INTAKE_1', 'o6', 'สั่งของครับ'))
        self.assertEqual(self._forwarded_ids(deliver), ['o6'])

    def test_follow_event_is_forwarded_even_when_bot_is_on(self):
        self.line_user.bot_enabled = True
        self.line_user.save()
        deliver, _ = self._post({'type': 'follow', 'replyToken': 'r', 'source': {'userId': 'U_INTAKE_1'}})
        self.assertEqual(json.loads(deliver.call_args.args[1])['events'][0]['type'], 'follow')

    def test_relay_error_does_not_stop_our_bot(self):
        with patch('patients.line_relay._deliver_in_background', side_effect=RuntimeError('boom')), \
                patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            self.assertEqual(_signed_post(self.client, [_text_event('U_INTAKE_1', 'o7', 'เปิดใช้งานบอท'),
                                                        _text_event('U_SALES', 'o8', 'สั่งของ')]).status_code, 200)
        self.assertTrue(reply.called)

    def test_delivery_retries_server_errors_but_not_rejections(self):
        with patch('patients.line_relay.httpx.post', side_effect=[MagicMock(status_code=502), MagicMock(status_code=200)]) as post:
            self.assertTrue(line_relay._deliver('https://old.example/', b'{}', 'sig'))
        self.assertEqual(post.call_count, 2)
        with patch('patients.line_relay.httpx.post', return_value=MagicMock(status_code=401)) as post:
            self.assertFalse(line_relay._deliver('https://old.example/', b'{}', 'sig'))
        self.assertEqual(post.call_count, 1)


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


class Phase3ChatAndVoiceTests(IntakeTestBase):
    def setUp(self):
        super().setUp()
        self.line_user.active_patient = self.patient
        self.line_user.save()
        self.nurse = User.objects.create_user(username='nurse_p3', password='NursePass2026!x', role=User.Role.NURSE)
        self.doctor = User.objects.create_user(username='dr_p3', password='DoctorPass2026!x', role=User.Role.DOCTOR)

    def _reply(self, user, text='นัดตรวจพรุ่งนี้ 10 โมงนะคะ'):
        self.client.force_login(user)
        with patch('patients.line_service.LineMessagingService.push_message', return_value=True) as push:
            resp = self.client.post(reverse('root_staff_inbox_reply'), {'line_user_id': 'U_INTAKE_1', 'text': text})
        return resp, push

    def test_nurse_without_permission_cannot_reply(self):
        from patients.models import CommunicationRecord
        resp, push = self._reply(self.nurse)
        self.assertEqual(resp.status_code, 403)
        push.assert_not_called()
        self.assertFalse(CommunicationRecord.objects.filter(direction='OUTGOING').exists())

    def test_doctor_reply_is_pushed_and_recorded(self):
        from patients.models import CommunicationRecord
        resp, push = self._reply(self.doctor)
        self.assertEqual(resp.status_code, 302)
        push.assert_called_once()
        rec = CommunicationRecord.objects.get(direction='OUTGOING')
        self.assertEqual(rec.sent_by, self.doctor)
        self.assertEqual(rec.patient, self.patient)

    def test_owner_grants_chat_permission_to_nurse(self):
        owner = User.objects.create_superuser(username='owner_p3', password='OwnerPass2026!x', email='o@x.test')
        self.client.force_login(owner)
        self.client.post(reverse('patients:doctor_settings'), {'action': 'set_chat_permissions', 'can_reply': [str(self.nurse.pk)]})
        self.nurse.refresh_from_db()
        self.assertTrue(self.nurse.may_reply_line_chat)
        _, push = self._reply(self.nurse)
        push.assert_called_once()

    def test_non_owner_cannot_change_chat_permissions(self):
        self.client.force_login(self.doctor)
        resp = self.client.post(reverse('patients:doctor_settings'), {'action': 'set_chat_permissions', 'can_reply': [str(self.nurse.pk)]})
        self.assertEqual(resp.status_code, 403)
        self.nurse.refresh_from_db()
        self.assertFalse(self.nurse.can_reply_line_chat)

    def test_voice_dictation_creates_unlocked_box_with_ai_draft(self):
        self.client.force_login(self.doctor)
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'success': True, 'is_fallback': False, 'gateway': 'groq:test',
                                  'soap': {'subjective': 'ปวดหลัง', 'objective': '', 'assessment': '', 'plan': 'ติดตาม'}}
        with patch('clinical.services_intake.httpx.post', return_value=fake):
            resp = self.client.post(reverse('clinical:voice_soap'), {'patient_id': self.patient.pk, 'transcript': 'คนไข้ปวดหลังสามวัน'})
        box = Box.objects.get(source=Box.Source.CLINIC)
        self.assertRedirects(resp, reverse('clinical:intake_detail', args=[box.id]), fetch_redirect_response=False)
        self.assertEqual(box.contents['soap']['plan'], 'ติดตาม')
        detail = self.client.get(reverse('clinical:intake_detail', args=[box.id]))
        self.assertContains(detail, 'คนไข้ปวดหลังสามวัน')  # ผู้บันทึกเปิดได้ทันที

    @override_settings(AI_INTAKE_BOT_ENABLED=True)
    def test_ai_followup_question_replied_and_capped(self):
        fake = MagicMock(status_code=200)
        fake.json.return_value = {'success': True, 'question': 'ปวดมานานเท่าไหร่แล้วคะ', 'provider': 'groq',
                                  'model': 'm', 'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
        with patch('clinical.services_intake.httpx.post', return_value=fake) as post, \
             patch('patients.views_line.LineMessagingService.reply_message', return_value=True) as reply:
            _signed_post(self.client, [_text_event('U_INTAKE_1', 'fstart', 'เริ่ม')])
            for i in range(7):
                _signed_post(self.client, [_text_event('U_INTAKE_1', f'f{i}', f'ปวดหัวมาก ครั้งที่ {i}')])
        self.assertEqual(post.call_count, services_intake.MAX_AI_FOLLOWUPS_PER_SESSION)
        sent = post.call_args.kwargs['json']['transcript']
        self.assertIn('ผู้ป่วย:', sent)
        box = Box.objects.get(patient=self.patient, source=Box.Source.LINE)
        self.assertEqual(sum(1 for m in box.contents['messages'] if m['sender'] == 'bot'), 5)
        self.assertIn('ปวดมานานเท่าไหร่แล้วคะ', json.dumps(reply.call_args_list[1].args[1][0], ensure_ascii=False))

    def test_ai_followup_off_by_default(self):
        with patch('clinical.services_intake.httpx.post') as post:
            _signed_post(self.client, [_text_event('U_INTAKE_1', 'off1', 'ปวดท้อง')])
        post.assert_not_called()
