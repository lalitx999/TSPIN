"""Synthetic evidence persistence tests. User runs these against Django's test DB."""

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .evidence_service import append_evidence, read_evidence_state
from .models import ClinicalEvidenceRevision, Patient
from .unit_registry import create_unit_registry, transition_unit_registry


class EvidenceServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='synthetic-reviewer', is_staff=True)
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='patients', codename__in=[
                'add_clinicalevidencerevision', 'view_clinicalevidencerevision',
                'verify_clinicalevidence', 'add_canonicalunitregistry',
            ]))
        self.patient = Patient.objects.create(hn='SYNTHETIC-1', first_name='Synthetic', last_name='Only')
        self.units = {'test-analyte': 'test-unit'}
        self.registry = create_unit_registry(actor=self.user, version='synthetic-v1', units=self.units)
        approver = User.objects.create_user(username='registry-approver')
        approver.user_permissions.add(Permission.objects.get(
            content_type__app_label='patients', codename='approve_unitregistry'))
        transition_unit_registry(registry_id=self.registry.pk, actor=approver,
                                 state='APPROVED', reason='Synthetic test fixture only')
        self.source = {'patient_id': str(self.patient.pk), 'hn': self.patient.hn,
            'concept_id': 'test-analyte', 'source_id': 'lab-1', 'source_type': 'LAB_MEASURED',
            'source_timestamp': '2026-10-01T00:00:00Z', 'consent_scope': 'CARE',
            'value': 12, 'unit': 'test-unit'}

    def append(self, **kwargs):
        return append_evidence(patient_id=self.patient.pk, actor=self.user,
            source=kwargs.pop('source', self.source), registry_id=self.registry.pk, **kwargs)

    def test_persisted_state_matches_returned_state(self):
        row, state = self.append()
        self.assertEqual(row.payload['verification'], 'UNVERIFIED')
        self.assertEqual(row.payload['entered_by'], str(self.user.pk))
        self.assertEqual(state, read_evidence_state(self.patient, registry_id=self.registry.pk))

    def test_staff_flag_alone_does_not_grant_evidence_permission(self):
        staff = User.objects.create_user(username='unprivileged-staff', is_staff=True)
        with self.assertRaises(PermissionDenied):
            append_evidence(patient_id=self.patient.pk, actor=staff,
                            source=self.source, registry_id=self.registry.pk)
        self.assertFalse(ClinicalEvidenceRevision.objects.exists())

    def test_writer_cannot_self_assert_verifier(self):
        with self.assertRaises(ValidationError):
            self.append(source={**self.source, 'verified_by': 'other-doctor'})
        self.assertFalse(ClinicalEvidenceRevision.objects.exists())

    def test_verification_requires_separate_permission(self):
        writer = User.objects.create_user(username='writer')
        writer.user_permissions.add(Permission.objects.get(
            content_type__app_label='patients', codename='add_clinicalevidencerevision'))
        with self.assertRaises(PermissionDenied):
            append_evidence(patient_id=self.patient.pk, actor=writer, source=self.source,
                            registry_id=self.registry.pk, verify=True)

    def test_wrong_patient_not_relabelled(self):
        with self.assertRaises(ValidationError):
            self.append(source={**self.source, 'hn': 'OTHER'})
        self.assertFalse(ClinicalEvidenceRevision.objects.exists())

    def test_correction_preserves_original_and_changes_hash(self):
        first, before = self.append(verify=True)
        second, after = self.append(source={**self.source, 'value': 13}, verify=True,
                                    supersedes=first.pk, correction_reason='Transcription correction')
        first.refresh_from_db()
        self.assertEqual(first.payload['value'], 12)
        self.assertEqual(second.payload['version'], 2)
        self.assertEqual(after['active_evidence_ids'], [str(second.pk)])
        self.assertNotEqual(before['state_hash'], after['state_hash'])
        self.assertEqual(ClinicalEvidenceRevision.objects.count(), 2)

    def test_stale_correction_parent_rejected(self):
        first, _ = self.append(verify=True)
        self.append(verify=True, supersedes=first.pk, correction_reason='First correction')
        with self.assertRaises(ValidationError):
            self.append(verify=True, supersedes=first.pk, correction_reason='Stale correction')
        self.assertEqual(ClinicalEvidenceRevision.objects.count(), 2)

    def test_correction_cannot_change_source(self):
        first, _ = self.append(verify=True)
        with self.assertRaises(ValidationError):
            self.append(source={**self.source, 'source_id': 'different-source'},
                        verify=True, supersedes=first.pk, correction_reason='Invalid reassignment')
        self.assertEqual(ClinicalEvidenceRevision.objects.count(), 1)

    def test_unverified_correction_does_not_replace_active_evidence(self):
        first, before = self.append(verify=True)
        with self.assertRaises(ValidationError):
            self.append(supersedes=first.pk, correction_reason='Unverified proposal')
        self.assertEqual(read_evidence_state(self.patient, registry_id=self.registry.pk), before)

    def test_conflicts_preserved_but_state_blocked(self):
        self.append(verify=True)
        _, state = self.append(source={**self.source, 'source_id': 'lab-2', 'value': 14}, verify=True)
        self.assertEqual(state['status'], 'BLOCKED')
        self.assertEqual(ClinicalEvidenceRevision.objects.count(), 2)

    def test_invalid_units_rollback(self):
        with self.assertRaises(ValidationError):
            self.append(source={**self.source, 'unit': 'wrong'})
        self.assertFalse(ClinicalEvidenceRevision.objects.exists())

    def test_no_orm_overwrite_or_delete(self):
        row, _ = self.append()
        with self.assertRaises(ValidationError):
            row.save()
        with self.assertRaises(ValidationError):
            ClinicalEvidenceRevision.objects.filter(pk=row.pk).update(payload={})
        with self.assertRaises(ValidationError):
            ClinicalEvidenceRevision.objects.all().delete()
        with self.assertRaises(ValidationError):
            row.delete()

    def test_history_api_requires_explicit_permission(self):
        client = APIClient()
        staff = User.objects.create_user(username='no-evidence-view', is_staff=True)
        client.force_authenticate(staff)
        response = client.get(f'/api/patients/{self.patient.pk}/canonical-evidence/')
        self.assertEqual(response.status_code, 403)

    def test_history_api_returns_stored_hash(self):
        row, _ = self.append()
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get(f'/api/patients/{self.patient.pk}/canonical-evidence/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['payload_hash'], row.payload_hash)

    def test_state_api_uses_explicit_approved_registry(self):
        _, state = self.append()
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get(f'/api/patients/{self.patient.pk}/canonical-state/',
                              {'registry_id': str(self.registry.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state_hash'], state['state_hash'])

    def test_state_api_does_not_guess_registry(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get(f'/api/patients/{self.patient.pk}/canonical-state/')
        self.assertEqual(response.status_code, 400)

    def test_state_api_cannot_read_other_patient_with_view_permission_alone(self):
        other = User.objects.create_user(username='not-this-patient')
        other.user_permissions.add(Permission.objects.get(
            content_type__app_label='patients', codename='view_clinicalevidencerevision'))
        client = APIClient()
        client.force_authenticate(other)
        response = client.get(f'/api/patients/{self.patient.pk}/canonical-state/',
                              {'registry_id': str(self.registry.pk)})
        self.assertEqual(response.status_code, 404)
