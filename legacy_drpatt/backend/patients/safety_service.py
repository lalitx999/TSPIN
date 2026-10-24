"""Safety completeness previews and historical snapshots. No clinical clearance."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .analysis_inputs import prepare_analysis_inputs
from .canonical_state import canonical_hash
from .models import GovernedRegistry, SafetyAssessment
from .safety_contracts import evaluate_safety
from .unit_registry import require_permission


@transaction.atomic
def _build_safety_snapshot(*, patient_id, actor, unit_registry_id, selection, policy_id,
                   expected_manifest_hash=None):
    if not isinstance(selection, dict) or not {'ONTOLOGY', 'SAFETY'} <= set(selection):
        raise ValidationError('ONTOLOGY and SAFETY registry versions are required.')
    if not isinstance(policy_id, str) or not policy_id.strip():
        raise ValidationError('An explicit safety policy ID is required.')
    preview = prepare_analysis_inputs(patient_id=patient_id, actor=actor,
        unit_registry_id=unit_registry_id, selection=selection,
        expected_manifest_hash=expected_manifest_hash)
    manifest = preview['manifest']
    reference = manifest['registry_bundle']['registries']['SAFETY']
    registry = GovernedRegistry.objects.get(pk=reference['id'])
    entry = next((item for item in registry.content['entries'] if item['id'] == policy_id), None)
    if entry is None:
        raise ValidationError('Policy not found in the approved safety registry.')
    canonical = manifest['canonical_state']
    active = set(canonical['active_evidence_ids'])
    evidence = [item for item in canonical['evidence_history'] if item['evidence_id'] in active]
    # No trusted drug-interaction adapter is connected yet. Never accept a client
    # assertion that the database is available or fabricate an all-clear result.
    result = evaluate_safety(entry['policy'], evidence, as_of=timezone.now(),
                             interaction_source_status='UNAVAILABLE')
    result.update({'policy_id': policy_id, 'policy_hash': canonical_hash(entry['policy']),
                   'policy_source_ids': entry['source_ids'], 'registry': reference,
                   'manifest_hash': preview['manifest_hash'], 'input_issues': preview['issues']})
    if preview['status'] == 'BLOCKED' and result['safety_state'] not in {'ALERT', 'EMERGENCY'}:
        result['safety_state'] = 'INCOMPLETE'
        result['decision'] = 'DEFER'
    result['result_hash'] = canonical_hash(result)
    return {'evaluator_version': 'safety-completeness-v2', 'manifest': manifest,
            'policy': entry['policy'], 'result': result, 'preflight_status': preview['status'],
            'expected_manifest_hash': expected_manifest_hash}


def preview_safety(**kwargs):
    return _build_safety_snapshot(**kwargs)['result']


@transaction.atomic
def record_safety_assessment(*, patient_id, actor, unit_registry_id, selection, policy_id,
                             expected_manifest_hash):
    require_permission(actor, 'patients.add_safetyassessment')
    if not isinstance(expected_manifest_hash, str) or not expected_manifest_hash:
        raise ValidationError('A reviewed manifest hash is required.')
    snapshot = _build_safety_snapshot(patient_id=patient_id, actor=actor,
        unit_registry_id=unit_registry_id, selection=selection, policy_id=policy_id,
        expected_manifest_hash=expected_manifest_hash)
    assessment = SafetyAssessment.objects.create(patient_id=patient_id, created_by=actor, snapshot=snapshot)
    return {'safety_assessment_id': str(assessment.pk), 'integrity_hash': assessment.integrity_hash,
            'result': snapshot['result'], 'clinical_use_authorized': False}
