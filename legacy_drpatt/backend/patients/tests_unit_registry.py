"""Synthetic unit-registry governance and evidence integration tests."""
from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from .evidence_service import append_evidence, read_evidence_state
from .models import Patient, ClinicalEvidenceRevision
from .unit_registry import create_unit_registry, transition_unit_registry, approved_registry


class UnitRegistryTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='registry-author')
        self.reviewer = User.objects.create_user(username='registry-reviewer')
        self.author.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='patients', codename__in=[
                'add_canonicalunitregistry', 'approve_unitregistry', 'add_clinicalevidencerevision']))
        self.reviewer.user_permissions.add(Permission.objects.get(
            content_type__app_label='patients', codename='approve_unitregistry'))
        self.registry = create_unit_registry(actor=self.author, version='test-v1', units={'synthetic': 'unit'})
        self.patient = Patient.objects.create(hn='SYNTHETIC-REGISTRY', first_name='Synthetic', last_name='Only')
        self.source = {'patient_id': str(self.patient.pk), 'hn': self.patient.hn,
            'concept_id': 'synthetic', 'source_id': 'source-1', 'source_type': 'LAB_MEASURED',
            'source_timestamp': '2026-10-01T00:00:00Z', 'consent_scope': 'CARE', 'value': 1, 'unit': 'unit'}

    def transition(self, state):
        return transition_unit_registry(registry_id=self.registry.pk, actor=self.reviewer,
                                        state=state, reason='Synthetic test only')

    def append(self, registry=None):
        return append_evidence(patient_id=self.patient.pk, actor=self.author, source=self.source,
                               registry_id=(registry or self.registry).pk)

    def test_draft_cannot_be_used_for_evidence(self):
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_NOT_APPROVED'):
            self.append()
        self.assertFalse(ClinicalEvidenceRevision.objects.exists())

    def test_provisional_cannot_be_used(self):
        self.transition('PROVISIONAL')
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_NOT_APPROVED'):
            self.append()

    def test_author_cannot_self_approve(self):
        with self.assertRaises(PermissionDenied):
            transition_unit_registry(registry_id=self.registry.pk, actor=self.author,
                                     state='APPROVED', reason='Self approval')

    def test_approved_version_hash_is_stored_with_evidence(self):
        self.transition('APPROVED')
        row, state = self.append()
        self.assertEqual(row.unit_registry_id, self.registry.pk)
        self.assertEqual(row.payload['unit_registry']['content_hash'], self.registry.content_hash)
        self.assertEqual(state['unit_registry'], row.payload['unit_registry'])
        self.assertEqual(state, read_evidence_state(self.patient, registry_id=self.registry.pk))

    def test_retirement_blocks_new_use_but_preserves_history(self):
        self.transition('APPROVED')
        self.append()
        self.transition('RETIRED')
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_NOT_APPROVED'):
            self.append()
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_NOT_APPROVED'):
            read_evidence_state(self.patient, registry_id=self.registry.pk)
        self.assertEqual(ClinicalEvidenceRevision.objects.count(), 1)
        self.assertEqual(self.registry.decisions.count(), 3)

    def test_retired_version_cannot_be_reapproved(self):
        self.transition('RETIRED')
        with self.assertRaises(ValidationError):
            self.transition('APPROVED')

    def test_content_and_decisions_cannot_be_overwritten(self):
        self.registry.units = {'synthetic': 'wrong'}
        with self.assertRaises(ValidationError):
            self.registry.save()
        with self.assertRaises(ValidationError):
            self.registry.decisions.update(state='APPROVED')

    def test_version_skew_is_blocked_even_if_units_match(self):
        self.transition('APPROVED')
        self.append()
        newer = create_unit_registry(actor=self.author, version='test-v2', units={'synthetic': 'unit'})
        transition_unit_registry(registry_id=newer.pk, actor=self.reviewer,
                                 state='APPROVED', reason='Synthetic new release')
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_VERSION_MISMATCH'):
            self.append(newer)
        self.assertEqual(ClinicalEvidenceRevision.objects.count(), 1)

    def test_invalid_unit_dictionary_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_unit_registry(actor=self.author, version='invalid', units={'synthetic': 123})

    def test_approval_requires_permission_and_reason(self):
        other = User.objects.create_user(username='unprivileged', is_staff=True)
        with self.assertRaises(PermissionDenied):
            transition_unit_registry(registry_id=self.registry.pk, actor=other,
                                     state='APPROVED', reason='Not authorized')
        with self.assertRaises(ValidationError):
            transition_unit_registry(registry_id=self.registry.pk, actor=self.reviewer,
                                     state='APPROVED', reason='')
