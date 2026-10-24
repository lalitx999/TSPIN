import base64
import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from .models import Patient, LineChat


class LineIdentitySecurityTests(TestCase):
    def setUp(self):
        self.first = Patient.objects.create(legacy_id='SYNTHETIC-FIRST', hn='TEST-FIRST',
            first_name='PrivateFirst', last_name='Only', id_card='0000000000001', line_user_id='U_TEST')
        self.second = Patient.objects.create(legacy_id='SYNTHETIC-SECOND', hn='TEST-SECOND',
            first_name='PrivateSecond', last_name='Only', id_card='0000000000002')

    def send(self, text):
        body = json.dumps({'events': [{'type': 'message', 'replyToken': 'test-token',
            'source': {'userId': 'U_TEST'}, 'message': {'type': 'text', 'text': text}}]}).encode()
        signature = base64.b64encode(hmac.new(b'test-secret', body, hashlib.sha256).digest()).decode()
        with patch.dict('os.environ', {'LINE_DOCTORPATT_CHANNEL_SECRET': 'test-secret',
                                      'LINE_DOCTORPATT_CHANNEL_ACCESS_TOKEN': 'test-token'}), \
             patch('patients.views_line.reply_line_message') as reply, \
             patch('urllib.request.urlopen', side_effect=AssertionError('Network forbidden')):
            response = APIClient().post('/api/line/webhook/', body, content_type='application/json',
                                        HTTP_X_LINE_SIGNATURE=signature)
            self.assertEqual(response.status_code, 200)
            reply.assert_called_once()
            return reply.call_args.args[1]

    def test_signed_citizen_id_cannot_transfer_binding(self):
        messages = self.send(self.second.id_card)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual(self.first.line_user_id, 'U_TEST')
        self.assertFalse(self.second.line_user_id)
        self.assertNotIn(self.second.first_name, json.dumps(messages))
        self.assertFalse(LineChat.objects.exists())

    def test_unknown_id_does_not_reveal_registration_status(self):
        self.assertEqual(self.send(self.second.id_card), self.send('0000000000009'))

    def test_unlinked_user_cannot_claim_patient_by_id(self):
        self.first.line_user_id = None
        self.first.save()
        self.send(self.second.id_card)
        self.second.refresh_from_db()
        self.assertFalse(self.second.line_user_id)

    def test_duplicate_binding_never_selects_latest_patient(self):
        self.second.line_user_id = 'U_TEST'
        self.second.save()
        messages = self.send('เริ่มซักประวัติสุขภาพ')
        self.assertNotIn(self.first.first_name, json.dumps(messages))
        self.assertNotIn(self.second.first_name, json.dumps(messages))
        self.assertFalse(LineChat.objects.exists())
        self.assertEqual(Patient.objects.filter(line_user_id='U_TEST').count(), 2)

    def test_legacy_link_endpoints_cannot_lookup_or_change_bindings(self):
        for path in ('/api/line/link/', '/api/liff/identity/'):
            with self.subTest(path=path), \
                 patch('patients.views_line.Patient.objects.filter') as lookup, \
                 patch('patients.views_line.LineLinkingToken.objects.filter') as token_lookup, \
                 patch('patients.views_line.push_line_message') as push:
                response = APIClient().post(path, {'phone': 'synthetic-phone', 'token': 'synthetic-token',
                    'lineUserId': 'U_TEST', 'displayName': 'Untrusted'}, format='json')
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.data['code'], 'VERIFIED_ACCOUNT_LINK_REQUIRED')
                lookup.assert_not_called()
                token_lookup.assert_not_called()
                push.assert_not_called()
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual(self.first.line_user_id, 'U_TEST')
        self.assertFalse(self.second.line_user_id)
