import base64
import hashlib
import hmac
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Patient, PatientBiologicalRecord, AnalysisRecord


class AnalysisDeliveryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='synthetic-analysis-owner')
        self.staff = User.objects.create_user(username='synthetic-reviewer', is_staff=True)
        self.patient = Patient.objects.create(legacy_id='TEST-DELIVERY', hn='TEST-DELIVERY',
            first_name='Synthetic', last_name='Only', id_card=self.owner.username, line_user_id='U_SYNTHETIC')
        source = PatientBiologicalRecord.objects.create(patient=self.patient, axis_1=72)
        AnalysisRecord.objects.create(patient=self.patient, source_record=source, inputs_hash='test-delivery',
                                      ledger={'analysis_state': 'ANALYSIS_READY', 'private_draft': 'test-only'})
        self.client = APIClient()

    def test_owner_cannot_read_raw_analysis_ledger(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(f'/api/patients/{self.patient.pk}/tspi-analysis/')
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('test-only', response.content.decode())

    def test_staff_can_review_analysis(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(f'/api/patients/{self.patient.pk}/tspi-analysis/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['private_draft'], 'test-only')

    def test_line_dashboard_paths_never_calculate_or_send_scores(self):
        variants = [{'type': 'postback', 'postback': {'data': 'action=view_dashboard'}},
                    {'type': 'message', 'message': {'type': 'text', 'text': '39 แกน', 'id': 'synthetic'}}]
        for variant in variants:
            with self.subTest(variant=variant):
                event = {**variant, 'replyToken': 'synthetic-reply', 'source': {'userId': 'U_SYNTHETIC'}}
                body = json.dumps({'events': [event]}).encode()
                signature = base64.b64encode(hmac.new(b'synthetic-secret', body, hashlib.sha256).digest()).decode()
                with patch.dict('os.environ', {'LINE_DOCTORPATT_CHANNEL_SECRET': 'synthetic-secret',
                        'LINE_DOCTORPATT_CHANNEL_ACCESS_TOKEN': 'synthetic-token'}), \
                     patch('patients.views_line.reply_line_message') as reply, \
                     patch('patients.tspi_engine.calculate_tspi_analysis') as calculate, \
                     patch('urllib.request.urlopen', side_effect=AssertionError('Network forbidden')):
                    response = self.client.post('/api/line/webhook/', body, content_type='application/json',
                                                HTTP_X_LINE_SIGNATURE=signature)
                    self.assertEqual(response.status_code, 200)
                    calculate.assert_not_called()
                    reply.assert_called_once()
                    message = reply.call_args.args[1][0]
                    self.assertEqual(message['type'], 'text')
                    self.assertIn('ยังไม่พร้อมเผยแพร่', message['text'])
                    self.assertNotIn(self.patient.hn, message['text'])
