"""Replay historical assessments at their original timestamp, never today's time."""
from copy import deepcopy
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError

from .canonical_state import canonical_hash
from .models import SafetyAssessment
from .safety_contracts import evaluate_safety
from .unit_registry import require_permission


def verify_safety_integrity(assessment):
    snapshot = assessment.snapshot
    digest = canonical_hash({'id': str(assessment.pk), 'patient_id': str(assessment.patient_id),
        'actor_id': str(assessment.created_by_id), 'snapshot': snapshot})
    if digest != assessment.integrity_hash:
        raise ValidationError('SAFETY_HISTORY_INTEGRITY_FAILURE')
    result = snapshot['result']
    if canonical_hash(snapshot['manifest']) != result['manifest_hash'] or canonical_hash(snapshot['policy']) != result['policy_hash']:
        raise ValidationError('SAFETY_INPUT_HASH_MISMATCH')
    if canonical_hash({k: v for k, v in result.items() if k != 'result_hash'}) != result['result_hash']:
        raise ValidationError('SAFETY_RESULT_HASH_MISMATCH')


def replay_safety_assessment(assessment):
    verify_safety_integrity(assessment)
    snapshot = assessment.snapshot
    if snapshot['evaluator_version'] not in {'safety-completeness-v1', 'safety-completeness-v2'}:
        return {'status': 'UNSUPPORTED_EVALUATOR_VERSION'}
    canonical = snapshot['manifest']['canonical_state']
    active = set(canonical['active_evidence_ids'])
    evidence = [item for item in canonical['evidence_history'] if item['evidence_id'] in active]
    original = snapshot['result']
    replayed = evaluate_safety(snapshot['policy'], evidence,
        as_of=datetime.fromisoformat(original['assessed_at']),
        interaction_source_status=original['interaction_source_status'],
        preserve_unresolved_alerts=snapshot['evaluator_version'] == 'safety-completeness-v2')
    if snapshot['preflight_status'] == 'BLOCKED' and replayed['safety_state'] not in {'ALERT', 'EMERGENCY'}:
        replayed['safety_state'], replayed['decision'] = 'INCOMPLETE', 'DEFER'
    matches = all(original.get(key) == value for key, value in replayed.items())
    return {'status': 'MATCH' if matches else 'MISMATCH', 'replayed_result': replayed}


def read_safety_assessment(*, patient_id, assessment_id, actor):
    require_permission(actor, 'patients.view_safetyassessment')
    assessment = SafetyAssessment.objects.select_related('patient').get(pk=assessment_id, patient_id=patient_id)
    patient = assessment.patient
    clinical = actor.is_staff or actor.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists()
    if not clinical and (not patient.id_card or patient.id_card != actor.username):
        raise PermissionDenied('Patient access is required.')
    replay = replay_safety_assessment(assessment)
    return {'safety_assessment_id': str(assessment.pk), 'created_at': assessment.created_at.isoformat(),
            'created_by': str(assessment.created_by_id), 'snapshot': deepcopy(assessment.snapshot),
            'integrity_hash': assessment.integrity_hash, 'replay': replay,
            'historical_only': True, 'clinical_use_authorized': False}
