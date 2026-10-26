"""EP1: deterministic, fail-closed canonical evidence snapshots.

This module performs no database writes, medical inference, or unit conversion.
Callers must obtain identity and verification metadata from trusted backend records,
not accept those assertions directly from a patient request.
"""

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone


SOURCE_TYPES = frozenset({
    'PATIENT_REPORTED', 'PHYSICIAN_OBSERVED', 'LAB_MEASURED', 'DEVICE_MEASURED',
    'IMAGING_REPORTED', 'DERIVED', 'CLINICAL_INFERENCE', 'HYPOTHESIS',
    'RESEARCH_REFERENCE', 'NOT_AVAILABLE', 'NOT_ASSESSED',
})
VERIFICATION_STATES = frozenset({'UNVERIFIED', 'VERIFIED', 'REJECTED'})
REQUIRED_FIELDS = (
    'evidence_id', 'patient_id', 'hn', 'concept_id', 'source_id', 'source_type',
    'source_timestamp', 'recorded_at', 'entered_by', 'verification', 'version',
    'consent_scope', 'value', 'unit',
)


def canonical_hash(value):
    """Stable hash; refuse NaN/infinity and values that cannot be stored as JSON."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an ISO-8601 string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('Timestamp requires a timezone')
    return result.astimezone(timezone.utc)


def _observation_signature(record):
    key = (record['source_id'], record['concept_id'],
           _timestamp(record['source_timestamp']).isoformat(), record['version'])
    content = canonical_hash({'value': record['value'], 'unit': record['unit'],
                              'source_type': record['source_type'],
                              'verification': record['verification']})
    return key, content


def build_canonical_state(patient_id, hn, evidence, *, expected_units):
    """Return a reproducible snapshot, keeping all revisions for audit.

    expected_units is an explicitly supplied canonical concept -> unit mapping.
    Unknown concepts/units block instead of silently converting. Conflicts refer
    to the same concept AND observation time; longitudinal changes are not conflicts.
    BLOCKED snapshots must never be used for scoring or patient release.
    """
    problems = []
    records = {}
    duplicates = []

    def block(code, evidence_id=None):
        problems.append({'code': code, 'evidence_id': evidence_id})

    if not isinstance(patient_id, str) or not patient_id.strip() or not isinstance(hn, str) or not hn.strip():
        block('MISSING_PATIENT_IDENTITY')
    if not isinstance(evidence, list) or not isinstance(expected_units, dict):
        raise ValueError('Evidence must be a list and expected_units a mapping')

    for raw in evidence:
        if not isinstance(raw, dict):
            block('INVALID_EVIDENCE')
            continue
        record = deepcopy(raw)
        eid = record.get('evidence_id')
        if any(key not in record for key in REQUIRED_FIELDS):
            block('MISSING_PROVENANCE', eid if isinstance(eid, str) else None)
            continue
        text_fields = ('evidence_id', 'patient_id', 'hn', 'concept_id', 'source_id',
                       'source_type', 'entered_by', 'verification', 'consent_scope')
        if any(not isinstance(record[key], str) or not record[key].strip() for key in text_fields):
            block('INVALID_PROVENANCE')
            continue
        if record['patient_id'] != patient_id or record['hn'] != hn:
            block('PATIENT_IDENTITY_MISMATCH', eid)
            continue
        if record['source_type'] not in SOURCE_TYPES or record['verification'] not in VERIFICATION_STATES:
            block('INVALID_EVIDENCE_CLASSIFICATION', eid)
            continue
        if type(record['version']) is not int or record['version'] < 1:
            block('INVALID_VERSION', eid)
            continue
        try:
            _timestamp(record['source_timestamp'])
            _timestamp(record['recorded_at'])
            canonical_hash(record)
        except (ValueError, TypeError, OverflowError):
            block('INVALID_EVIDENCE_ENCODING', eid)
            continue
        if record['concept_id'] not in expected_units:
            block('UNKNOWN_CANONICAL_CONCEPT', eid)
        elif record['unit'] != expected_units[record['concept_id']]:
            block('UNIT_MISMATCH', eid)
        if record['verification'] == 'VERIFIED' and (
            not isinstance(record.get('verified_by'), str) or not record['verified_by'].strip()
        ):
            block('MISSING_VERIFIER', eid)
        if record['source_type'] in {'NOT_AVAILABLE', 'NOT_ASSESSED'} and record['value'] is not None:
            block('UNAVAILABLE_EVIDENCE_HAS_VALUE', eid)
        if eid in records:
            if records[eid] != record:
                block('EVIDENCE_ID_COLLISION', eid)
            else:
                duplicates.append(eid)
            continue
        records[eid] = record

    superseded = set()
    children = {}
    for eid, record in records.items():
        parent_id = record.get('supersedes')
        if parent_id is None:
            if record['version'] != 1:
                block('MISSING_REVISION_PARENT', eid)
            continue
        if not isinstance(parent_id, str) or parent_id not in records:
            block('UNKNOWN_REVISION_PARENT', eid)
            continue
        parent = records[parent_id]
        same_observation = all(record[key] == parent[key] for key in ('concept_id', 'source_id'))
        if (not same_observation or record['version'] != parent['version'] + 1
                or _timestamp(record['recorded_at']) <= _timestamp(parent['recorded_at'])
                or not isinstance(record.get('correction_reason'), str)
                or not record['correction_reason'].strip()
                or record['verification'] != 'VERIFIED'):
            block('INVALID_CORRECTION', eid)
            continue
        if parent_id in children:
            block('BRANCHED_CORRECTION', eid)
        children[parent_id] = eid
        superseded.add(parent_id)

    # Corrections retire the observation, including equivalent import aliases.
    # Preserve every original row in history; never retire a different source/value.
    retired_signatures = {_observation_signature(records[eid]) for eid in superseded}
    superseded.update(eid for eid, record in records.items()
                      if _observation_signature(record) in retired_signatures)

    active = []
    seen = {}
    observations = {}
    for eid in sorted(records):
        record = records[eid]
        if eid in superseded or record['verification'] == 'REJECTED':
            continue
        # Re-imports retain history but must not contribute twice to scoring.
        key, content = _observation_signature(record)
        if key in seen:
            prior_content, _ = seen[key]
            if content != prior_content:
                block('SOURCE_OBSERVATION_COLLISION', eid)
            else:
                duplicates.append(eid)
            continue
        seen[key] = (content, eid)
        active.append(eid)
        if record['verification'] == 'VERIFIED' and record['value'] is not None:
            observation = (record['concept_id'], _timestamp(record['source_timestamp']))
            value_hash = canonical_hash({'value': record['value'], 'unit': record['unit']})
            if observation in observations and observations[observation] != value_hash:
                block('CONFLICTING_VERIFIED_SOURCES', eid)
            observations[observation] = value_hash

    if not active:
        block('NO_ACTIVE_EVIDENCE')
    snapshot = {
        'schema_version': 'canonical-evidence-v2', 'patient_id': patient_id, 'hn': hn,
        'unit_contract': deepcopy(expected_units),
        'evidence_history': [records[key] for key in sorted(records)],
        'active_evidence_ids': active, 'duplicate_evidence_ids': sorted(set(duplicates)),
        'issues': sorted(problems, key=lambda p: (p['code'], p['evidence_id'] or '')),
        'status': 'BLOCKED' if problems else 'VALIDATED_STRUCTURE',
    }
    # Structural validation is not clinical verification, approval, or consent.
    snapshot['state_hash'] = canonical_hash(snapshot)
    return snapshot
