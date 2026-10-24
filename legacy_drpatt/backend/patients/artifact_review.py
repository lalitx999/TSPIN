"""Internal reviewer feedback service; clinical approval is deliberately absent."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from uuid import UUID

from .agentic_service import read_agentic_artifact
from .models import AgenticArtifact, ArtifactReviewEvent
from .permissions import can_review_clinical_reports
from .unit_registry import require_permission


@transaction.atomic
def record_artifact_review(*, patient_id, artifact_id, actor, expected_artifact_hash,
                           decision, reason, request_id=None):
    if not can_review_clinical_reports(actor):
        raise PermissionDenied('Clinical review access required.')
    require_permission(actor, 'patients.add_artifactreviewevent')
    require_permission(actor, 'patients.view_agenticartifact')
    if request_id is not None:
        try:
            request_id = UUID(str(request_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError('Invalid review request ID.') from exc
    # Reuse scope and integrity verification. A client supplies no actor or stored hash.
    artifact = AgenticArtifact.objects.select_for_update().get(pk=artifact_id, patient_id=patient_id)
    history = read_agentic_artifact(patient_id=patient_id, artifact_id=artifact_id, actor=actor)
    if expected_artifact_hash != history['integrity_hash']:
        raise ValidationError('Artifact changed or the reviewed version does not match.')
    # The artifact row lock serializes concurrent submissions on PostgreSQL.
    # A unique DB constraint also protects request identity at storage level.
    event = ArtifactReviewEvent.objects.filter(artifact=artifact, actor=actor,
        request_id=request_id).first() if request_id is not None else None
    replayed = event is not None
    if event is not None:
        if (event.artifact_hash, event.decision, event.reason) != (expected_artifact_hash, decision, reason):
            raise ValidationError('Review request ID already used for different content.')
    else:
        event = ArtifactReviewEvent.objects.create(artifact=artifact, actor=actor,
            artifact_hash=history['integrity_hash'], decision=decision, reason=reason,
            request_id=request_id)
    return {'review_event_id': event.pk, 'decision': event.decision,
            'artifact_id': str(artifact.pk), 'artifact_hash': event.artifact_hash,
            'replayed': replayed, 'clinical_use_authorized': False, 'send_allowed': False}


def list_artifact_reviews(*, patient_id, artifact_id, actor, before_id=None):
    if not can_review_clinical_reports(actor):
        raise PermissionDenied('Clinical review access required.')
    require_permission(actor, 'patients.view_artifactreviewevent')
    history = read_agentic_artifact(patient_id=patient_id, artifact_id=artifact_id, actor=actor)
    if before_id is not None and (type(before_id) is not int or before_id < 1):
        raise ValidationError('Invalid review cursor.')
    rows = ArtifactReviewEvent.objects.filter(artifact_id=artifact_id).order_by('-id')
    if before_id is not None:
        rows = rows.filter(id__lt=before_id)
    page = list(rows[:51])
    results = [{'id': row.pk, 'actor_id': row.actor_id, 'decision': row.decision,
                'reason': row.reason, 'created_at': row.created_at.isoformat(),
                'artifact_hash': row.artifact_hash} for row in page[:50]]
    return {'results': results, 'next_before_id': results[-1]['id'] if len(page) > 50 else None,
            'artifact_hash': history['integrity_hash'], 'clinical_use_authorized': False,
            'send_allowed': False}
