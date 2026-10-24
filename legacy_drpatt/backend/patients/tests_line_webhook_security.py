"""Authenticate webhook bytes before any clinical side effects. No network calls."""
import base64
import hashlib
import hmac
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class LineWebhookSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.environment = patch.dict('os.environ', {
            'LINE_DOCTORPATT_CHANNEL_SECRET': 'synthetic-secret', 'LINE_CHANNEL_SECRET': '',
            'LINE_DOCTORPATT_CHANNEL_ACCESS_TOKEN': 'synthetic-token'})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def signature(self, body):
        return base64.b64encode(hmac.new(b'synthetic-secret', body, hashlib.sha256).digest()).decode()

    def post(self, body, signature=''):
        return self.client.post('/api/line/webhook/', body, content_type='application/json',
                                HTTP_X_LINE_SIGNATURE=signature)

    def test_missing_invalid_or_unicode_signature_has_no_side_effects(self):
        body = b'{"events":[{"type":"postback","source":{"userId":"synthetic"}}]}'
        for debug in (True, False):
            for signature in ('', 'invalid', 'ลายเซ็น', self.signature(body + b' ')):
                with self.subTest(debug=debug, signature=signature), override_settings(DEBUG=debug), \
                     patch('patients.views_line.Patient.objects.filter') as lookup, \
                     patch('patients.views_line.reply_line_message') as reply, \
                     patch('urllib.request.urlopen', side_effect=AssertionError('Network forbidden')):
                    self.assertEqual(self.post(body, signature).status_code, 401)
                    lookup.assert_not_called()
                    reply.assert_not_called()

    def test_missing_server_secret_fails_closed(self):
        with patch.dict('os.environ', {'LINE_DOCTORPATT_CHANNEL_SECRET': '', 'LINE_CHANNEL_SECRET': ''}):
            self.assertEqual(self.post(b'{"events":[]}').status_code, 503)

    def test_valid_signed_empty_probe_is_accepted(self):
        body = b'{ "events": [] }'
        self.assertEqual(self.post(body, self.signature(body)).status_code, 200)

    def test_signed_invalid_encoding_json_and_events_are_bad_requests(self):
        for body in (b'\xff', b'{', b'[]', b'{}', b'{"events":{}}',
                     b'{"events":[null]}', b'{"events":[{"source":null}]}'):
            with self.subTest(body=body):
                self.assertEqual(self.post(body, self.signature(body)).status_code, 400)

    def test_unsigned_malformed_bytes_are_rejected_before_parsing(self):
        self.assertEqual(self.post(b'\xff').status_code, 401)
