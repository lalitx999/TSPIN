"""Read-only readiness diagnostics, never a release token or send operation."""
from django.core.exceptions import ValidationError
from django.db import transaction

from .agentic_service import read_agentic_artifact
from .analysis_inputs import prepare_analysis_inputs
from .canonical_state import canonical_hash


@transaction.atomic
def inspect_release_readiness(*, patient_id, artifact_id, actor):
    history = read_agentic_artifact(patient_id=patient_id, artifact_id=artifact_id, actor=actor)
    manifest = history['payload']['manifest']
    digest = canonical_hash(manifest)
    selection = {kind: entry['id'] for kind, entry in manifest['registry_bundle']['registries'].items()}
    issues = []
    current_hash = None
    inputs_valid = False
    try:
        current = prepare_analysis_inputs(patient_id=patient_id, actor=actor,
            unit_registry_id=manifest['canonical_state']['unit_registry']['id'],
            selection=selection, expected_manifest_hash=digest)
        current_hash = current['manifest_hash']
        inputs_valid = current['status'] == 'INPUT_PREVIEW_VALIDATED'
        issues.extend(current['issues'])
    except ValidationError:
        # Do not expose internal registry errors or mistake invalid dependencies for freshness.
        issues.append({'code': 'CURRENT_INPUT_REVALIDATION_FAILED'})
    workflow = history['payload'].get('workflow')
    if not workflow or workflow['state'] != 'WORKFLOW_CHECKS_PASSED':
        issues.append({'code': 'WORKFLOW_REVIEW_INCOMPLETE'})
    # No trusted approval/consent/delivery adapters are connected to these artifacts.
    # Model permissions, group labels and legacy releases are not substitutes.
    issues.extend({'code': code} for code in (
        'ARTIFACT_BOUND_PHYSICIAN_APPROVAL_UNAVAILABLE',
        'CURRENT_RELEASE_CONSENT_UNVERIFIED',
        'RECIPIENT_AND_CHANNEL_UNVERIFIED',
        'PRE_SEND_SAFETY_RECHECK_REQUIRED',
    ))
    return {'artifact_id': history['artifact_id'], 'state': 'BLOCKED',
            'artifact_manifest_hash': digest, 'current_manifest_hash': current_hash,
            'input_is_current': current_hash == digest and inputs_valid,
            'issues': issues, 'diagnostic_only': True, 'clinical_use_authorized': False,
            'send_allowed': False}
