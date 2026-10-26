"""Versioned unit registry governance; no medical thresholds or guessed conversions."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .canonical_state import canonical_hash
from .models import CanonicalUnitRegistry, UnitRegistryDecision


def require_permission(actor, permission):
    if not actor or not actor.is_authenticated or not actor.is_active or not actor.has_perm(permission):
        raise PermissionDenied('Explicit registry permission is required.')


@transaction.atomic
def create_unit_registry(*, actor, version, units):
    require_permission(actor, 'patients.add_canonicalunitregistry')
    if not isinstance(version, str) or not version.strip() or len(version) > 80:
        raise ValidationError('A non-empty registry version of at most 80 characters is required.')
    registry = CanonicalUnitRegistry.objects.create(version=version, units=units, created_by=actor)
    UnitRegistryDecision.objects.create(registry=registry, state='DRAFT', actor=actor, reason='Version created')
    return registry


@transaction.atomic
def transition_unit_registry(*, registry_id, actor, state, reason):
    require_permission(actor, 'patients.approve_unitregistry')
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError('A decision reason is required.')
    registry = CanonicalUnitRegistry.objects.select_for_update().get(pk=registry_id)
    previous = registry.decisions.first()
    transitions = {'DRAFT': {'PROVISIONAL', 'APPROVED', 'RETIRED'},
                   'PROVISIONAL': {'APPROVED', 'RETIRED'}, 'APPROVED': {'RETIRED'}, 'RETIRED': set()}
    if not isinstance(state, str) or not previous or state not in transitions.get(previous.state, set()):
        raise ValidationError('Invalid registry lifecycle transition.')
    if state == 'APPROVED' and registry.created_by_id == actor.pk:
        raise PermissionDenied('Registry author cannot approve their own version.')
    _check_integrity(registry)
    return UnitRegistryDecision.objects.create(registry=registry, state=state, actor=actor, reason=reason)


def _check_integrity(registry):
    if canonical_hash({'version': registry.version, 'units': registry.units}) != registry.content_hash:
        raise ValidationError('Registry integrity check failed.')


def approved_registry(registry_id, *, lock=False):
    query = CanonicalUnitRegistry.objects.select_for_update() if lock else CanonicalUnitRegistry.objects
    registry = query.get(pk=registry_id)
    _check_integrity(registry)
    decision = registry.decisions.first()
    if not decision or decision.state != 'APPROVED':
        raise ValidationError('REGISTRY_NOT_APPROVED')
    return registry
