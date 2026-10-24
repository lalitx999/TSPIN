"""Internal approval preflight, not licence verification or a signing service.

Credential and approval snapshots MUST come from trusted server-side adapters.
Never pass request JSON directly here. No endpoint currently accepts these records.
Even an eligible result does not authorize clinical use or delivery.
"""
from datetime import datetime, timezone
import re

from .canonical_state import canonical_hash


def _instant(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('Timezone required')
    return result.astimezone(timezone.utc)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def inspect_physician_approval(*, actor_id, patient_id, artifact_id,
                              artifact_hash, manifest_hash, credential,
                              approval, as_of):
    """Check exact artifact binding and credential validity at signing AND now.

    The caller supplies the clock and immutable hashes loaded from verified storage.
    No role/group, client checkbox or old report state grants approval here.
    """
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError('An explicit timezone-aware evaluation clock is required')
    issues = []
    context = dict(actor_id=actor_id, patient_id=patient_id, artifact_id=artifact_id,
                   artifact_hash=artifact_hash, manifest_hash=manifest_hash)
    valid_context = all(_text(context[key]) for key in ('actor_id', 'patient_id', 'artifact_id'))
    valid_context = valid_context and all(
        isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)
        for value in (artifact_hash, manifest_hash))
    if not valid_context:
        issues.append('INVALID_REVIEW_CONTEXT')

    signed_at = None
    if not isinstance(approval, dict):
        issues.append('ARTIFACT_BOUND_APPROVAL_MISSING')
    else:
        if approval.get('decision') != 'APPROVE':
            issues.append('APPROVAL_NOT_GRANTED')
        if any(approval.get(key) != value for key, value in context.items()):
            issues.append('APPROVAL_CONTEXT_MISMATCH')
        if not _text(approval.get('id')):
            issues.append('APPROVAL_AUDIT_REFERENCE_MISSING')
        try:
            signed_at = _instant(approval.get('signed_at'))
            if signed_at > as_of:
                issues.append('APPROVAL_IN_FUTURE')
        except (ValueError, TypeError, OverflowError):
            issues.append('INVALID_APPROVAL_TIMESTAMP')

    if not isinstance(credential, dict):
        issues.append('TRUSTED_PHYSICIAN_CREDENTIAL_UNAVAILABLE')
    else:
        if credential.get('status') != 'VERIFIED' or credential.get('revoked_at') is not None:
            issues.append('PHYSICIAN_CREDENTIAL_NOT_CURRENT')
        if credential.get('actor_id') != actor_id:
            issues.append('PHYSICIAN_ACCOUNT_MISMATCH')
        if not all(_text(credential.get(key)) for key in
                   ('id', 'authority', 'verification_reference', 'licence_number')):
            issues.append('PHYSICIAN_VERIFICATION_PROVENANCE_MISSING')
        if not isinstance(approval, dict) or approval.get('credential_id') != credential.get('id'):
            issues.append('APPROVAL_CREDENTIAL_MISMATCH')
        try:
            start = _instant(credential.get('valid_from'))
            end = _instant(credential.get('valid_until'))
            checked = _instant(credential.get('verified_at'))
            if not start <= checked <= as_of or not start <= as_of < end:
                issues.append('PHYSICIAN_CREDENTIAL_OUTSIDE_VALIDITY')
            if signed_at is not None and not checked <= signed_at < end:
                issues.append('PHYSICIAN_CREDENTIAL_INVALID_AT_SIGNING')
        except (ValueError, TypeError, OverflowError):
            issues.append('INVALID_CREDENTIAL_TIMESTAMP')

    return {
        'state': 'BLOCKED' if issues else 'APPROVAL_PREFLIGHT_PASSED',
        'issues': issues,
        'review_context_hash': canonical_hash(context) if valid_context else None,
        'diagnostic_only': True,
        'clinical_use_authorized': False,
        'send_allowed': False,
    }
