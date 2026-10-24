"""Historical verification/replay; deliberately does not authorize current clinical use."""
from copy import deepcopy

from django.core.exceptions import PermissionDenied, ValidationError

from .canonical_state import canonical_hash
from .deterministic_scoring import evaluate_rule
from .models import ScoringRun
from .unit_registry import require_permission


def verify_run_integrity(run):
    expected = canonical_hash({'id': str(run.pk), 'patient_id': str(run.patient_id),
        'actor_id': str(run.created_by_id), 'manifest': run.manifest, 'result': run.result})
    if expected != run.integrity_hash or canonical_hash(run.manifest) != run.result.get('manifest_hash'):
        raise ValidationError('SCORING_HISTORY_INTEGRITY_FAILURE')
    hashed_result = {key: value for key, value in run.result.items()
                     if key not in {'result_hash', 'executed_at', 'executed_by'}}
    if canonical_hash(hashed_result) != run.result.get('result_hash'):
        raise ValidationError('SCORING_RESULT_HASH_MISMATCH')


def replay_stored_run(run):
    """Internal helper. Caller must check patient access before returning this data."""
    verify_run_integrity(run)
    if run.result.get('execution_stage') == 'PREFLIGHT_BLOCKED':
        return {'status': 'NOT_EXECUTED', 'reason': 'Original run stopped before arithmetic.'}
    if run.result.get('executor_version') != 'weighted-sum-decimal-v1':
        return {'status': 'UNSUPPORTED_EXECUTOR_VERSION'}
    selected_ids = set(run.result['evidence_ids'])
    evidence = [item for item in run.manifest['canonical_state']['evidence_history']
                if item['evidence_id'] in selected_ids]
    replayed = evaluate_rule(run.result['rule'], evidence)
    fields = ('status', 'score', 'band', 'issues', 'contributions')
    matched = all(replayed[key] == run.result[key] for key in fields)
    return {'status': 'MATCH' if matched else 'MISMATCH', 'replayed_result': replayed}


def read_scoring_run(*, patient_id, run_id, actor):
    require_permission(actor, 'patients.view_scoringrun')
    run = ScoringRun.objects.select_related('patient').get(pk=run_id, patient_id=patient_id)
    patient = run.patient
    clinical = actor.is_staff or actor.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists()
    if not clinical and (not patient.id_card or patient.id_card != actor.username):
        raise PermissionDenied('Patient access is required.')
    replay = replay_stored_run(run)
    return {'scoring_run_id': str(run.pk), 'created_at': run.created_at.isoformat(),
            'manifest': deepcopy(run.manifest), 'result': deepcopy(run.result),
            'integrity_hash': run.integrity_hash, 'replay': replay,
            'historical_only': True, 'clinical_use_authorized': False}
