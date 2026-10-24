"""Backend-wired review artifacts; unimplemented clinical roles deliberately stop."""
from copy import deepcopy

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .agentic_orchestrator import run_workflow
from .analysis_inputs import prepare_analysis_inputs
from .canonical_state import canonical_hash
from .evidence_reports import compose_evidence_drafts, validate_evidence_drafts
from .models import AgenticArtifact
from .safety_service import preview_safety
from .scoring_history import read_scoring_run
from .unit_registry import require_permission


def _require_reviewer(actor):
    if not (actor.is_staff or actor.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists()):
        raise PermissionDenied('Unreleased review artifacts are for clinical staff only.')


def _answer(envelope, decision='PASS', *, payload=None, issues=None):
    return {'role': envelope['role'], 'input_hash': envelope['input_hash'],
            'decision': decision, 'payload': payload or {}, 'issues': issues or []}


def _adapters(preview, scoring, safety):
    def identity(envelope):
        problems = preview['issues']
        return _answer(envelope, 'STOP' if problems else 'PASS', issues=problems)

    def completeness(envelope):
        active = envelope['manifest']['canonical_state']['active_evidence_ids']
        return _answer(envelope, 'PASS' if active else 'DEFER',
                       payload={'scope': 'canonical_evidence_structure'},
                       issues=[] if active else [{'code': 'NO_ACTIVE_EVIDENCE'}])

    def scoring_check(envelope):
        passed = scoring['result'].get('status') == 'CALCULATED' and scoring['replay']['status'] == 'MATCH'
        return _answer(envelope, 'PASS' if passed else 'DEFER',
                       payload={'scoring_run_id': scoring['scoring_run_id']},
                       issues=[] if passed else [{'code': 'SCORING_NOT_ASSESSED_OR_REPLAY_FAILED'}])

    def safety_check(envelope):
        # Completeness never constitutes safety approval; the current service stays DEFER.
        return _answer(envelope, 'ESCALATE' if safety['alerts'] else 'DEFER',
                       payload={'safety_state': safety['safety_state']},
                       issues=[{'code': 'SAFETY_REVIEW_REQUIRED'}])

    def composer(envelope):
        return _answer(envelope, payload={'draft': compose_evidence_drafts(envelope['manifest'])})

    def facts_check(envelope):
        try:
            validate_evidence_drafts(envelope['draft'], envelope['manifest'])
            return _answer(envelope, payload={'reviewed_draft_hash': envelope['draft_hash']})
        except ValueError:
            return _answer(envelope, 'FAIL', payload={'reviewed_draft_hash': envelope['draft_hash']},
                           issues=[{'code': 'DRAFT_FACT_OR_PROVENANCE_MISMATCH'}])

    def structure(envelope):
        return _answer(envelope, payload={'scope': 'backend_preflight_validated',
                                          'manifest_hash': preview['manifest_hash']})

    # No fake clinical logic, research/case matching, red-team or physician approval adapters.
    implementations = {'A01': identity, 'A02': completeness, 'A03': structure,
        'A04': structure, 'A05': scoring_check, 'A06': structure, 'A08': safety_check,
        'A13': composer, 'A14': facts_check, 'A16': facts_check}
    return {key: {'version': 'backend-evidence-review-v1', 'run': handler}
            for key, handler in implementations.items()}


def _create_artifact(patient_id, actor, kind, payload):
    artifact = AgenticArtifact.objects.create(patient_id=patient_id, created_by=actor, kind=kind, payload=payload)
    return {'artifact_id': str(artifact.pk), 'kind': kind, 'integrity_hash': artifact.integrity_hash,
            'state': payload.get('workflow', {}).get('state', 'DRAFT'), 'clinical_use_authorized': False}


@transaction.atomic
def create_evidence_report_drafts(*, patient_id, actor, unit_registry_id, selection, expected_manifest_hash):
    require_permission(actor, 'patients.add_agenticartifact')
    _require_reviewer(actor)
    if not expected_manifest_hash:
        raise ValidationError('A reviewed manifest hash is required.')
    preview = prepare_analysis_inputs(patient_id=patient_id, actor=actor,
        unit_registry_id=unit_registry_id, selection=selection, expected_manifest_hash=expected_manifest_hash)
    if preview['status'] != 'INPUT_PREVIEW_VALIDATED':
        raise ValidationError('INPUT_PREFLIGHT_BLOCKED')
    packet = compose_evidence_drafts(preview['manifest'])
    validate_evidence_drafts(packet, preview['manifest'])
    return _create_artifact(patient_id, actor, 'EVIDENCE_DRAFT', {'manifest': preview['manifest'], 'packet': packet})


@transaction.atomic
def create_workflow_review(*, patient_id, actor, unit_registry_id, selection, expected_manifest_hash,
                           scoring_run_id, safety_policy_id):
    require_permission(actor, 'patients.add_agenticartifact')
    _require_reviewer(actor)
    if not isinstance(selection, dict) or not {'ONTOLOGY', 'SCORING', 'SAFETY'} <= set(selection):
        raise ValidationError('ONTOLOGY, SCORING and SAFETY versions are required.')
    if not expected_manifest_hash:
        raise ValidationError('A reviewed manifest hash is required.')
    preview = prepare_analysis_inputs(patient_id=patient_id, actor=actor,
        unit_registry_id=unit_registry_id, selection=selection, expected_manifest_hash=expected_manifest_hash)
    scoring = read_scoring_run(patient_id=patient_id, run_id=scoring_run_id, actor=actor)
    current, previous = preview['manifest'], scoring['manifest']
    if (canonical_hash(previous['identity']) != canonical_hash(current['identity'])
            or previous['canonical_state']['state_hash'] != current['canonical_state']['state_hash']):
        raise ValidationError('SCORING_RUN_INPUTS_STALE')
    pinned = scoring['result'].get('registry')
    if pinned != current['registry_bundle']['registries']['SCORING']:
        raise ValidationError('SCORING_REGISTRY_VERSION_MISMATCH')
    safety = preview_safety(patient_id=patient_id, actor=actor, unit_registry_id=unit_registry_id,
        selection=selection, policy_id=safety_policy_id, expected_manifest_hash=expected_manifest_hash)
    if safety['manifest_hash'] != preview['manifest_hash']:
        raise ValidationError('SAFETY_INPUTS_CHANGED')
    # Preserve alerts before a missing later adapter can hide them. This is a precheck,
    # not a claim that all 18 roles ran or that safety is complete.
    if safety['alerts']:
        trace = [{'stage': 'SAFETY_PRECHECK', 'decision': 'ESCALATE', 'safety': safety}]
        workflow = {'workflow_version': 'agentic-controller-v1', 'state': 'ESCALATED',
            'reason': 'SAFETY_PRECHECK_ALERT', 'rounds_used': 0, 'manifest_hash': preview['manifest_hash'],
            'trace': trace, 'trace_hash': canonical_hash(trace), 'clinical_use_authorized': False}
    else:
        workflow = run_workflow(manifest=preview['manifest'], handlers=_adapters(preview, scoring, safety))
    return _create_artifact(patient_id, actor, 'WORKFLOW', {'manifest': preview['manifest'],
        'workflow': workflow, 'scoring_run_id': scoring['scoring_run_id'], 'safety_preview': safety})


def read_agentic_artifact(*, patient_id, artifact_id, actor):
    require_permission(actor, 'patients.view_agenticartifact')
    _require_reviewer(actor)
    artifact = AgenticArtifact.objects.select_related('patient').get(pk=artifact_id, patient_id=patient_id)
    patient = artifact.patient
    clinical = actor.is_staff or actor.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists()
    if not clinical and (not patient.id_card or patient.id_card != actor.username):
        raise PermissionDenied('Patient access is required.')
    digest = canonical_hash({'id': str(artifact.pk), 'kind': artifact.kind,
        'patient_id': str(artifact.patient_id), 'actor_id': str(artifact.created_by_id), 'payload': artifact.payload})
    if digest != artifact.integrity_hash:
        raise ValidationError('AGENTIC_ARTIFACT_INTEGRITY_FAILURE')
    if artifact.kind == 'EVIDENCE_DRAFT':
        try:
            validate_evidence_drafts(artifact.payload['packet'], artifact.payload['manifest'])
        except ValueError as exc:
            raise ValidationError('DRAFT_FACT_OR_PROVENANCE_MISMATCH') from exc
    else:
        workflow = artifact.payload['workflow']
        if canonical_hash(workflow['trace']) != workflow['trace_hash']:
            raise ValidationError('WORKFLOW_TRACE_HASH_MISMATCH')
    return {'artifact_id': str(artifact.pk), 'kind': artifact.kind, 'payload': deepcopy(artifact.payload),
            'integrity_hash': artifact.integrity_hash, 'historical_only': True, 'clinical_use_authorized': False}
