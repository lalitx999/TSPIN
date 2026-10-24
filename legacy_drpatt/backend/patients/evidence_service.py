"""Trusted backend evidence writes. Not an endpoint for arbitrary patient JSON."""

import uuid
from copy import deepcopy

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .canonical_state import build_canonical_state, canonical_hash
from .models import ClinicalEvidenceRevision, Patient
from .unit_registry import approved_registry


def _require(actor, permission):
    if not actor or not actor.is_authenticated or not actor.is_active or not actor.has_perm(permission):
        raise PermissionDenied('Explicit evidence permission is required.')


def _registry_state(patient, payloads, registry):
    state = build_canonical_state(str(patient.pk), patient.hn, payloads, expected_units=registry.units)
    reference = {'id': str(registry.pk), 'version': registry.version, 'content_hash': registry.content_hash}
    state['unit_registry'] = reference
    if any(payload.get('unit_registry') != reference for payload in payloads):
        state['issues'].append({'code': 'REGISTRY_VERSION_MISMATCH', 'evidence_id': None})
        state['status'] = 'BLOCKED'
    state.pop('state_hash', None)
    state['state_hash'] = canonical_hash(state)
    return state


@transaction.atomic
def read_evidence_state(patient, *, registry_id):
    """Caller must authorize patient access. Registry comes from backend storage."""
    registry = approved_registry(registry_id, lock=True)
    rows = list(patient.evidence_revisions.all())
    for row in rows:
        if canonical_hash(row.payload) != row.payload_hash:
            raise ValidationError('Stored evidence integrity check failed.')
        if str(row.unit_registry_id) != str(registry.pk):
            raise ValidationError('REGISTRY_VERSION_MISMATCH')
    return _registry_state(patient, [row.payload for row in rows], registry)


@transaction.atomic
def append_evidence(*, patient_id, actor, source, registry_id, supersedes=None,
                    correction_reason=None, verify=False):
    """Append validated evidence under a per-patient lock.

    Units are loaded from an explicitly approved backend registry version.
    This service records evidence only; it never approves a clinical report.
    Corrections require explicit source-verification permission. Draft correction
    proposals belong in a separate workflow and cannot replace active evidence.
    """
    _require(actor, 'patients.add_clinicalevidencerevision')
    if verify or supersedes:
        _require(actor, 'patients.verify_clinicalevidence')
    if type(verify) is not bool:
        raise ValidationError('verify must be a boolean.')
    if supersedes and not verify:
        raise ValidationError('A correction requires verified source evidence.')
    registry = approved_registry(registry_id, lock=True)
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    if not isinstance(source, dict):
        raise ValidationError('Source must be an object.')
    allowed = {'patient_id', 'hn', 'concept_id', 'source_id', 'source_type',
               'source_timestamp', 'consent_scope', 'value', 'unit'}
    if set(source) - allowed:
        raise ValidationError('Source contains unsupported or server-owned fields.')
    if source.get('patient_id') != str(patient.pk) or source.get('hn') != patient.hn:
        raise ValidationError('Source patient identity does not match the target patient.')
    parent = None
    if supersedes:
        try:
            parent = patient.evidence_revisions.get(pk=supersedes)
        except ClinicalEvidenceRevision.DoesNotExist as exc:
            raise ValidationError('Correction parent was not found for this patient.') from exc
        if ClinicalEvidenceRevision.objects.filter(supersedes=parent).exists():
            raise ValidationError('Evidence was already corrected; refresh before retrying.')
    eid = uuid.uuid4()
    payload = deepcopy(source)
    payload.update({
        'evidence_id': str(eid), 'recorded_at': timezone.now().isoformat(),
        'entered_by': str(actor.pk), 'verification': 'VERIFIED' if verify else 'UNVERIFIED',
        'version': parent.payload['version'] + 1 if parent else 1,
        'unit_registry': {'id': str(registry.pk), 'version': registry.version,
                          'content_hash': registry.content_hash},
    })
    if verify:
        payload['verified_by'] = str(actor.pk)
    if parent:
        payload.update(supersedes=str(parent.pk), correction_reason=correction_reason)
    existing = list(patient.evidence_revisions.all())
    if any(canonical_hash(row.payload) != row.payload_hash for row in existing):
        raise ValidationError('Stored evidence integrity check failed.')
    if any(row.unit_registry_id != registry.pk for row in existing):
        raise ValidationError('REGISTRY_VERSION_MISMATCH')
    state = _registry_state(patient, [row.payload for row in existing] + [payload], registry)
    # Preserve conflicting measurements for reconciliation, but never mark them usable.
    structural_issues = [issue for issue in state['issues']
                         if issue['code'] != 'CONFLICTING_VERIFIED_SOURCES']
    if structural_issues:
        raise ValidationError({'evidence': [issue['code'] for issue in structural_issues]})
    row = ClinicalEvidenceRevision.objects.create(
        id=eid, patient=patient, payload=payload, supersedes=parent, created_by=actor,
        unit_registry=registry,
    )
    return row, state
