"""
Automated Unit Tests for Option A: FastAPI <-> Django Internal LINE Webhook Ingestion.
Verifies:
1. Internal Token Security (constant-time token rejection / acceptance)
2. Strict Idempotency / Deduplication (message_id, webhookEventId)
3. Non-clinical message passing without noise
4. Clinical symptom detection (Level 1 Intake)
5. Urgent symptom detection (Level 2 Diagnostic)
6. Thai Negation awareness (prevents false positives)
7. Unbound user handling (binding_required flag)
8. Rapid message time-window grouping (< 5 mins)
"""

import json
from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from patients.models import (
    Patient,
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
)
from accounts.models import User


TEST_INTERNAL_TOKEN = 'test-internal-token-for-unit-tests-only-0123456789'


@override_settings(INTERNAL_API_TOKEN=TEST_INTERNAL_TOKEN)
class LineInternalWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.internal_token = TEST_INTERNAL_TOKEN

        # ข้อมูลผู้ป่วยและบัญชี LINE สำหรับทดสอบ
        self.patient = Patient.objects.create(
            hn='HN-TEST-INT01',
            first_name='สมศักดิ์',
            last_name='ภักดีวงษ์',
            phone='0891234567'
        )

        self.line_user = LineUser.objects.create(
            line_user_id='U_INTERNAL_TEST_USER_999',
            display_name='สมศักดิ์ LINE',
            active_patient=self.patient
        )

        self.binding = LinePatientBinding.objects.create(
            line_user=self.line_user,
            patient=self.patient,
            role=LinePatientBinding.RoleChoices.SELF,
            status=LinePatientBinding.StatusChoices.ACTIVE,
            verified_method='LIFF_2STEP_OTP'
        )

    def test_internal_token_auth_rejected_when_invalid(self):
        """1. ตรวจสอบการปฏิเสธคำขอหากไม่มีหรือ Token ไม่ถูกต้อง (401 Unauthorized)"""
        url = reverse('root_internal_line_webhook')

        # ไม่มี Header Token
        resp1 = self.client.post(
            url,
            data=json.dumps({"type": "message"}),
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 401)

        # Header Token ผิด
        resp2 = self.client.post(
            url,
            data=json.dumps({"type": "message"}),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN='WRONG_TOKEN_VALUE'
        )
        self.assertEqual(resp2.status_code, 401)

    def test_internal_token_auth_accepted_when_valid(self):
        """2. ตรวจสอบการยอมรับคำขอเมื่อ Token ถูกต้อง (200 OK)"""
        url = reverse('root_internal_line_webhook')
        payload = {
            "type": "message",
            "source": {"userId": self.line_user.line_user_id},
            "message": {
                "id": "msg_valid_token_001",
                "type": "text",
                "text": "สวัสดีครับคุณหมอ"
            }
        }
        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['action'], 'processed')

    def test_deduplication_with_message_id(self):
        """3. Deduplication: ส่งข้อความซ้ำด้วย message.id เดียวกัน ต้องตอบ 200 Deduplicated และไม่สร้างเรคคอร์ดเบิ้ล"""
        url = reverse('root_internal_line_webhook')
        payload = {
            "type": "message",
            "source": {"userId": self.line_user.line_user_id},
            "message": {
                "id": "msg_dedupe_unique_777",
                "type": "text",
                "text": "สอบถามตารางนัดครับ"
            }
        }

        # ส่งครั้งที่ 1 -> บันทึกสำเร็จ
        resp1 = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()['action'], 'processed')
        self.assertEqual(CommunicationRecord.objects.filter(line_message_id="msg_dedupe_unique_777").count(), 1)

        # ส่งครั้งที่ 2 (LINE Retry) -> ต้อง Deduplicate ไม่สร้างซ้ำ
        resp2 = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()['action'], 'deduplicated')
        self.assertEqual(CommunicationRecord.objects.filter(line_message_id="msg_dedupe_unique_777").count(), 1)

    def test_deduplication_with_webhook_event_id(self):
        """4. Deduplication: Event ที่ไม่ใช่ message เช่น follow/postback ใช้ webhookEventId"""
        url = reverse('root_internal_line_webhook')
        payload = {
            "type": "follow",
            "webhookEventId": "webhook_evt_follow_abc_123",
            "source": {"userId": self.line_user.line_user_id}
        }

        resp1 = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()['action'], 'processed')

        # Retry ส่งซ้ำ
        resp2 = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()['action'], 'deduplicated')

    def test_general_message_no_clinical_flag(self):
        """5. ข้อความทั่วไป: ไม่ติด Flag คลินิก และไม่สร้าง ClinicalReviewItem"""
        url = reverse('root_internal_line_webhook')
        payload = {
            "type": "message",
            "source": {"userId": self.line_user.line_user_id},
            "message": {
                "id": "msg_general_001",
                "type": "text",
                "text": "คลินิกเปิดทำการวันเสาร์กี่โมงครับ พอดีจะแวะไปรับเอกสาร"
            }
        }

        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['is_clinical_candidate'])
        self.assertIsNone(data['review_item_id'])
        self.assertEqual(ClinicalReviewItem.objects.filter(source_message__line_message_id="msg_general_001").count(), 0)

    def test_clinical_message_creates_level1_review_item(self):
        """6. ข้อความอาการทั่วไป: is_clinical_candidate=True -> สร้าง ClinicalReviewItem Level 1 Intake (พยาบาล/แพทย์)"""
        url = reverse('root_internal_line_webhook')
        payload = {
            "type": "message",
            "source": {"userId": self.line_user.line_user_id},
            "message": {
                "id": "msg_clinical_001",
                "type": "text",
                "text": "คุณหมอครับ วันนี้มีอาการไข้ต่ำๆ และไอแห้งมา 3 วันแล้ว"
            }
        }

        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['is_clinical_candidate'])
        self.assertFalse(data['is_urgent'])
        self.assertIn('ไข้', data['matched_keywords'])
        self.assertIsNotNone(data['review_item_id'])

        # ตรวจสอบว่าใน Database เป็น LEVEL_1_INTAKE
        review_item = ClinicalReviewItem.objects.get(pk=data['review_item_id'])
        self.assertEqual(review_item.review_type, ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE)
        self.assertEqual(review_item.status, ClinicalReviewItem.StatusChoices.PENDING_REVIEW)
        self.assertEqual(review_item.patient, self.patient)

    def test_urgent_message_creates_level2_review_item(self):
        """7. ข้อความอาการด่วนวิกฤต: URGENT KEYWORDS -> สร้าง ClinicalReviewItem Level 2 Diagnostic (แพทย์เท่านั้น)"""
        url = reverse('root_internal_line_webhook')
        payload = {
            "type": "message",
            "source": {"userId": self.line_user.line_user_id},
            "message": {
                "id": "msg_urgent_001",
                "type": "text",
                "text": "ตอนนี้มีอาการ แน่นหน้าอก หายใจไม่ออก รบกวนหมอช่วยดูหน่อยครับ"
            }
        }

        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['is_clinical_candidate'])
        self.assertTrue(data['is_urgent'])
        self.assertIn('แน่นหน้าอก', data['matched_keywords'])

        # ตรวจสอบว่าใน Database เป็น LEVEL_2_DIAGNOSTIC
        review_item = ClinicalReviewItem.objects.get(pk=data['review_item_id'])
        self.assertEqual(review_item.review_type, ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC)
        self.assertEqual(review_item.status, ClinicalReviewItem.StatusChoices.PENDING_REVIEW)

    def test_negation_awareness_prevents_false_positive(self):
        """8. Negation Awareness: ตรวจจับคำปฏิเสธ 'ไม่ปวด' / 'ไม่มีไข้' ไม่ส่ง Alert ปลอม"""
        url = reverse('root_internal_line_webhook')
        payload = {
            "type": "message",
            "source": {"userId": self.line_user.line_user_id},
            "message": {
                "id": "msg_negation_001",
                "type": "text",
                "text": "วันนี้สบายดีมากครับ หายปวดแล้ว และไม่มีไข้แล้วครับ ขอบคุณครับ"
            }
        }

        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # ควรไม่ติด Flag คลินิก เพราะถูก negate ด้วย 'หายปวด' และ 'ไม่มีไข้'
        self.assertFalse(data['is_clinical_candidate'])
        self.assertIsNone(data['review_item_id'])

    def test_unbound_user_message_sets_binding_required(self):
        """9. ผู้ใช้ยังไม่ได้ Bind คนไข้: บันทึก CommunicationRecord และแจ้งเตือน binding_required=True"""
        unbound_user_id = 'U_UNBOUND_NEW_USER_888'
        url = reverse('root_internal_line_webhook')
        payload = {
            "type": "message",
            "source": {"userId": unbound_user_id},
            "message": {
                "id": "msg_unbound_001",
                "type": "text",
                "text": "มีไข้สูง หนาวสั่น"
            }
        }

        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['is_clinical_candidate'])
        self.assertTrue(data['binding_required'])
        self.assertIsNone(data['review_item_id'])  # ยังไม่สร้าง Review Item จนกว่าจะระบุตัวตนคนไข้ได้

        record = CommunicationRecord.objects.get(line_message_id="msg_unbound_001")
        self.assertIsNone(record.patient)
        self.assertEqual(record.line_user.line_user_id, unbound_user_id)

    def test_time_window_grouping_merges_rapid_messages(self):
        """10. Message Grouping: คนไข้พิมพ์ข้อความต่อเนื่องใน 5 นาที รวมเข้าเป็น 1 Review Item ไม่สร้างขยะในคิว"""
        url = reverse('root_internal_line_webhook')

        # ข้อความที่ 1 (ปวดท้อง -> Level 1)
        resp1 = self.client.post(
            url,
            data=json.dumps({
                "type": "message",
                "source": {"userId": self.line_user.line_user_id},
                "message": {"id": "msg_group_01", "type": "text", "text": "มีอาการปวดท้องด้านขวา"}
            }),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        item1_id = resp1.json()['review_item_id']

        # ข้อความที่ 2 ใน 1 นาทีถัดมา (แน่นหน้าอก -> URGENT -> Level 2)
        resp2 = self.client.post(
            url,
            data=json.dumps({
                "type": "message",
                "source": {"userId": self.line_user.line_user_id},
                "message": {"id": "msg_group_02", "type": "text", "text": "และตอนนี้เริ่มมีอาการ แน่นหน้าอก ด้วยครับ"}
            }),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN=self.internal_token
        )
        item2_id = resp2.json()['review_item_id']

        # ต้องเป็น Review Item เดียวกัน
        self.assertEqual(item1_id, item2_id)

        # ตรวจสอบว่าได้รับการยกระดับเป็น LEVEL_2_DIAGNOSTIC จากข้อความที่ 2
        item = ClinicalReviewItem.objects.get(pk=item1_id)
        self.assertEqual(item.review_type, ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC)
        self.assertIn("แน่นหน้าอก", item.review_notes)
        self.assertIn("ข้อความต่อเนื่อง", item.review_notes)


TEST_LINE_SECRET = 'test-line-channel-secret'


@override_settings(LINE_CHANNEL_SECRET=TEST_LINE_SECRET, LINE_CHANNEL_ACCESS_TOKEN='')
class DjangoLineWebhookIngestionTests(TestCase):
    """LINE OA ส่ง webhook ตรงเข้า Django (เส้นทางเดียว) แล้วต้องเข้า Unified Inbox"""

    def setUp(self):
        self.client = Client()
        self.patient = Patient.objects.create(hn='HN-TEST-DJ01', first_name='ทดสอบ', last_name='เว็บฮุก', phone='0890000001')
        self.line_user = LineUser.objects.create(line_user_id='U_DJANGO_DIRECT_001', display_name='Direct')
        LinePatientBinding.objects.create(
            line_user=self.line_user, patient=self.patient,
            role=LinePatientBinding.RoleChoices.SELF, status=LinePatientBinding.StatusChoices.ACTIVE,
            verified_method='LIFF_2STEP_OTP',
        )
        self.line_user.active_patient = self.patient
        self.line_user.save()

    def _post_signed(self, body: dict, signature=None):
        import base64, hashlib, hmac
        raw = json.dumps(body).encode('utf-8')
        if signature is None:
            signature = base64.b64encode(hmac.new(TEST_LINE_SECRET.encode(), raw, hashlib.sha256).digest()).decode()
        return self.client.post('/line/webhook/', data=raw, content_type='application/json', HTTP_X_LINE_SIGNATURE=signature)

    def test_signed_message_is_ingested_into_inbox_and_review_queue(self):
        resp = self._post_signed({'events': [{
            'type': 'message',
            'source': {'userId': self.line_user.line_user_id},
            'message': {'id': 'dj_direct_msg_1', 'type': 'text', 'text': 'มีไข้สูงตั้งแต่เมื่อวาน'},
        }]})
        self.assertEqual(resp.status_code, 200)
        record = CommunicationRecord.objects.get(line_message_id='dj_direct_msg_1')
        self.assertEqual(record.patient, self.patient)
        self.assertTrue(record.is_clinical_candidate)
        self.assertTrue(ClinicalReviewItem.objects.filter(patient=self.patient).exists())

    def test_bad_signature_is_rejected_and_nothing_stored(self):
        resp = self._post_signed({'events': [{
            'type': 'message',
            'source': {'userId': self.line_user.line_user_id},
            'message': {'id': 'dj_forged_1', 'type': 'text', 'text': 'แน่นหน้าอก'},
        }]}, signature='Zm9yZ2Vk')
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(CommunicationRecord.objects.filter(line_message_id='dj_forged_1').exists())


@override_settings(INTERNAL_API_TOKEN='')
class InternalEndpointFailsClosedTests(TestCase):
    def test_unset_token_rejects_even_empty_header(self):
        resp = Client().post(
            reverse('root_internal_line_webhook'),
            data=json.dumps({'type': 'message', 'source': {'userId': 'U1'}, 'message': {'id': 'x', 'type': 'text', 'text': 'hi'}}),
            content_type='application/json',
            HTTP_X_INTERNAL_TOKEN='',
        )
        self.assertEqual(resp.status_code, 401)
