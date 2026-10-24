"""Read-only preflight for canonical analysis inputs; never executes clinical rules."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .canonical_state import canonical_hash
from .evidence_service import read_evidence_state
from .models import GovernedRegistry, Patient
from .registry_governance import resolve_registry_bundle
from .unit_registry import approved_registry, require_permission


@transaction.atomic
def prepare_analysis_inputs(*, patient_id, actor, unit_registry_id, selection,
                            expected_manifest_hash=None):
    """Preview one consistent input set. Call again at execution time, not just UI load.

    Locks follow evidence write order: unit registry -> patient -> governed registries.
    A matching hash is a freshness check, not an approval token or scoring contract.
    """
    require_permission(actor, 'patients.view_clinicalevidencerevision')
    require_permission(actor, 'patients.view_governedregistry')
    if not isinstance(selection, dict) or 'ONTOLOGY' not in selection:
        raise ValidationError('An explicit ONTOLOGY registry is required.')
    if expected_manifest_hash is not None and (
        not isinstance(expected_manifest_hash, str) or len(expected_manifest_hash) != 64
        or any(c not in '0123456789abcdef' for c in expected_manifest_hash)
    ):
        raise ValidationError('expected_manifest_hash must be a SHA-256 hex string.')
    unit_registry = approved_registry(unit_registry_id, lock=True)
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    is_clinical = actor.is_staff or actor.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists()
    if not is_clinical and (not patient.id_card or patient.id_card != actor.username):
        raise PermissionDenied('Patient access is required.')
    canonical = read_evidence_state(patient, registry_id=unit_registry.pk)
    bundle = resolve_registry_bundle(selection)
    ontology = GovernedRegistry.objects.get(pk=bundle['registries']['ONTOLOGY']['id'])
    concepts = {entry['id'] for entry in ontology.content['entries']}
    issues = list(canonical['issues'])
    active_ids = set(canonical['active_evidence_ids'])
    for evidence in canonical['evidence_history']:
        if evidence['evidence_id'] not in active_ids:
            continue
        if evidence['concept_id'] not in concepts:
            issues.append({'code': 'EVIDENCE_CONCEPT_NOT_IN_ONTOLOGY', 'evidence_id': evidence['evidence_id']})
        if evidence['verification'] != 'VERIFIED':
            issues.append({'code': 'EVIDENCE_REQUIRES_VERIFICATION', 'evidence_id': evidence['evidence_id']})
    identity = {'patient_id': str(patient.pk), 'hn': patient.hn,
                'first_name': patient.first_name, 'last_name': patient.last_name,
                'dob': patient.birth_date.isoformat() if patient.birth_date else None,
                'gender': patient.gender}
    if not identity['hn'] or not identity['dob'] or identity['gender'] not in {'M', 'F', 'O'}:
        issues.append({'code': 'PATIENT_IDENTITY_INCOMPLETE', 'evidence_id': None})
    manifest = {'schema_version': 'analysis-input-manifest-v1', 'identity': identity,
                'canonical_state': canonical, 'registry_bundle': bundle,
                'unit_registry_decision_id': unit_registry.decisions.first().pk}
    digest = canonical_hash(manifest)
    if expected_manifest_hash is not None and expected_manifest_hash != digest:
        issues.append({'code': 'STALE_ANALYSIS_INPUT', 'evidence_id': None})
    return {'manifest': manifest, 'manifest_hash': digest,
            'status': 'BLOCKED' if issues else 'INPUT_PREVIEW_VALIDATED',
            'issues': sorted(issues, key=lambda item: (item['code'], item['evidence_id'] or '')),
            'clinical_use_authorized': False,
            'remaining_gates': ['APPROVED_SCORING_RULE', 'SAFETY', 'CONSENT', 'PHYSICIAN_APPROVAL']}
