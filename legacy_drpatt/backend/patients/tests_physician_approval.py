from copy import deepcopy
from datetime import datetime, timezone
from unittest import TestCase

from .physician_approval import inspect_physician_approval


class PhysicianApprovalContractTests(TestCase):
    def setUp(self):
        self.context = dict(actor_id='doctor-test', patient_id='patient-test',
                            artifact_id='artifact-test', artifact_hash='a' * 64,
                            manifest_hash='b' * 64)
        self.credential = dict(id='credential-test', actor_id='doctor-test', status='VERIFIED',
            authority='synthetic-authority', verification_reference='synthetic-reference',
            licence_number='synthetic-licence', valid_from='2026-01-01T00:00:00Z',
            valid_until='2027-01-01T00:00:00Z', verified_at='2026-01-02T00:00:00Z',
            revoked_at=None)
        self.approval = dict(self.context, id='approval-test', decision='APPROVE',
            credential_id='credential-test', signed_at='2026-10-18T00:00:00Z')
        self.now = datetime(2026, 10, 19, tzinfo=timezone.utc)

    def inspect(self, **overrides):
        return inspect_physician_approval(**dict(self.context, credential=self.credential,
            approval=self.approval, as_of=self.now, **overrides))

    def test_valid_preflight_never_authorizes_delivery(self):
        result = self.inspect()
        self.assertEqual(result['state'], 'APPROVAL_PREFLIGHT_PASSED')
        self.assertFalse(result['send_allowed'])
        self.assertFalse(result['clinical_use_authorized'])
        self.assertEqual(len(result['review_context_hash']), 64)
        self.assertNotIn('licence_number', result)

    def test_each_binding_change_blocks_approval(self):
        for key in self.context:
            with self.subTest(key=key):
                approval = deepcopy(self.approval)
                approval[key] = 'different'
                result = inspect_physician_approval(**self.context, credential=self.credential,
                    approval=approval, as_of=self.now)
                self.assertIn('APPROVAL_CONTEXT_MISMATCH', result['issues'])

    def test_missing_trusted_source_cannot_be_replaced_by_group_or_checkbox(self):
        self.credential = None
        self.approval = {'is_physician_signoff': True, 'group': 'doctor', 'is_superuser': True}
        self.assertEqual(self.inspect()['state'], 'BLOCKED')

    def test_revoked_expired_wrong_actor_and_missing_provenance_block(self):
        for change in ({'revoked_at': '2026-10-19T00:00:00Z'}, {'status': 'PENDING'},
                       {'valid_until': '2026-10-19T00:00:00Z'}, {'actor_id': 'other'},
                       {'verification_reference': ''}, {'verified_at': '2026-10-19T00:00:00Z'},
                       {'valid_from': '2026-12-01T00:00:00Z'}, {'valid_until': 'invalid'}):
            with self.subTest(change=change):
                original = self.credential
                self.credential = dict(original, **change)
                self.assertEqual(self.inspect()['state'], 'BLOCKED')
                self.credential = original

    def test_invalid_decision_signing_time_and_credential_binding(self):
        for change in ({'decision': 'REJECT'}, {'signed_at': '2026-10-20T00:00:00Z'},
                       {'signed_at': '2026-10-18'}, {'credential_id': 'other'}, {'id': ''}):
            original = self.approval
            self.approval = dict(original, **change)
            self.assertEqual(self.inspect()['state'], 'BLOCKED')
            self.approval = original

    def test_explicit_clock_and_well_formed_context_required(self):
        self.now = datetime(2026, 10, 19)
        with self.assertRaises(ValueError):
            self.inspect()
        self.now = datetime(2026, 10, 19, tzinfo=timezone.utc)
        self.context['artifact_hash'] = True
        self.assertIn('INVALID_REVIEW_CONTEXT', self.inspect()['issues'])

    def test_does_not_mutate_snapshots(self):
        before = deepcopy((self.credential, self.approval))
        self.inspect()
        self.assertEqual(before, (self.credential, self.approval))
