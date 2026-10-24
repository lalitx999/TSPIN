"""Trusted scoring entry point: revalidate stored inputs and registry before arithmetic."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .analysis_inputs import prepare_analysis_inputs
from .canonical_state import canonical_hash
from .deterministic_scoring import evaluate_rule
from .models import GovernedRegistry, ScoringRun
from .unit_registry import require_permission


def _persist_result(*, patient_id, actor, manifest, result):
    """Failure to persist must roll back the run; never return unaudited success."""
    result['result_hash'] = canonical_hash(result)
    result['executed_at'] = timezone.now().isoformat()
    result['executed_by'] = str(actor.pk)
    run = ScoringRun.objects.create(patient_id=patient_id, created_by=actor,
                                    manifest=manifest, result=result)
    return {**result, 'scoring_run_id': str(run.pk), 'integrity_hash': run.integrity_hash}


@transaction.atomic
def execute_scoring_rule(*, patient_id, actor, unit_registry_id, selection,
                         expected_manifest_hash, rule_id, evidence_ids):
    """Calculate and persist its audit snapshot, not a clinical report or approval.

    Caller must supply the exact observation IDs reviewed; no implicit latest-result
    selection, averaging, or reuse of legacy numeric axes is allowed.
    """
    require_permission(actor, 'patients.execute_governedscoring')
    if not isinstance(selection, dict) or not {'ONTOLOGY', 'SCORING'} <= set(selection):
        raise ValidationError('ONTOLOGY and SCORING registries are required.')
    if not isinstance(expected_manifest_hash, str) or not expected_manifest_hash:
        raise ValidationError('A reviewed manifest hash is required.')
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ValidationError('An explicit rule ID is required.')
    if (not isinstance(evidence_ids, list) or not evidence_ids
            or not all(isinstance(eid, str) and eid for eid in evidence_ids)
            or len(set(evidence_ids)) != len(evidence_ids)):
        raise ValidationError('Explicit unique evidence IDs are required.')
    preview = prepare_analysis_inputs(patient_id=patient_id, actor=actor,
        unit_registry_id=unit_registry_id, selection=selection,
        expected_manifest_hash=expected_manifest_hash)
    if preview['status'] != 'INPUT_PREVIEW_VALIDATED':
        return _persist_result(patient_id=patient_id, actor=actor, manifest=preview['manifest'], result={
            'status': 'BLOCKED', 'score': None, 'band': None, 'issues': preview['issues'],
            'manifest_hash': preview['manifest_hash'], 'clinical_use_authorized': False,
            'requested_rule_id': rule_id, 'requested_evidence_ids': sorted(evidence_ids),
            'expected_manifest_hash': expected_manifest_hash, 'execution_stage': 'PREFLIGHT_BLOCKED'})
    manifest = preview['manifest']
    reference = manifest['registry_bundle']['registries']['SCORING']
    registry = GovernedRegistry.objects.get(pk=reference['id'])
    entry = next((item for item in registry.content['entries'] if item['id'] == rule_id), None)
    if entry is None:
        raise ValidationError('Rule was not found in the approved scoring release.')
    canonical = manifest['canonical_state']
    if not set(evidence_ids) <= set(canonical['active_evidence_ids']):
        raise ValidationError('Selected evidence is not active for this patient.')
    selected = [item for item in canonical['evidence_history'] if item['evidence_id'] in evidence_ids]
    concepts = {item['concept_id'] for item in entry['rule']['inputs']}
    if any(item['concept_id'] not in concepts for item in selected):
        raise ValidationError('Selected evidence contains inputs not used by this rule.')
    for definition in entry['rule']['inputs']:
        if canonical['unit_contract'].get(definition['concept_id']) != definition['unit']:
            raise ValidationError('SCORING_UNIT_CONTRACT_MISMATCH')
    result = evaluate_rule(entry['rule'], selected)
    result.update({'executor_version': 'weighted-sum-decimal-v1',
        'rule_id': rule_id, 'rule_hash': canonical_hash(entry['rule']), 'rule': entry['rule'],
        'rule_source_ids': entry['source_ids'],
        'registry': reference, 'manifest_hash': preview['manifest_hash'],
        'patient_id': str(patient_id), 'evidence_ids': sorted(evidence_ids),
        'clinical_use_authorized': False})
    result['execution_stage'] = 'RULE_EVALUATED'
    return _persist_result(patient_id=patient_id, actor=actor, manifest=manifest, result=result)
