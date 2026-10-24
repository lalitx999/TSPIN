"""Fail-closed registry metadata contracts. Never supplies medical scores or advice."""
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .canonical_state import canonical_hash
from .models import GovernedRegistry, GovernedRegistryDecision
from .unit_registry import require_permission

KINDS = frozenset({'ONTOLOGY', 'NETWORK', 'MODULE', 'RESEARCH', 'CASE', 'SCORING', 'SAFETY'})
DEPENDENCIES = {'ONTOLOGY': set(), 'NETWORK': {'ONTOLOGY'},
                'MODULE': {'ONTOLOGY', 'NETWORK'}, 'RESEARCH': set(), 'CASE': set(),
                'SCORING': {'ONTOLOGY'}, 'SAFETY': {'ONTOLOGY'}}
INITIAL = {'RESEARCH': 'UNVERIFIED', 'CASE': 'UNAVAILABLE'}
READY = {'RESEARCH': 'APPROVED', 'CASE': 'VALIDATED'}
COMMON_TRANSITIONS = {'DRAFT': {'PROVISIONAL', 'APPROVED', 'RETIRED'},
    'PROVISIONAL': {'APPROVED', 'RETIRED'}, 'APPROVED': {'RETIRED'}, 'RETIRED': set()}
TRANSITIONS = {
    'RESEARCH': {'UNVERIFIED': {'VERIFIED', 'RETIRED'}, 'VERIFIED': {'APPROVED', 'RETIRED'},
                 'APPROVED': {'RETIRED'}, 'RETIRED': set()},
    'CASE': {'UNAVAILABLE': {'CONNECTED', 'RETIRED'}, 'CONNECTED': {'VALIDATED', 'UNAVAILABLE', 'RETIRED'},
             'VALIDATED': {'UNAVAILABLE', 'RETIRED'}, 'RETIRED': set()},
}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_registry_content(kind, version, content):
    if not isinstance(kind, str) or kind not in KINDS or not _text(version) or len(version) > 80:
        raise ValidationError('Invalid registry kind or version.')
    if not isinstance(content, dict) or set(content) != {'entries', 'dependencies'}:
        raise ValidationError('Registry requires entries and dependencies only.')
    entries, deps = content['entries'], content['dependencies']
    if not isinstance(entries, list) or not isinstance(deps, dict) or set(deps) != DEPENDENCIES[kind]:
        raise ValidationError('Registry dependency contract mismatch.')
    for reference in deps.values():
        if not isinstance(reference, dict) or set(reference) != {'id', 'content_hash'}:
            raise ValidationError('Dependency requires exact registry ID and hash.')
        try:
            uuid.UUID(reference['id'])
        except (ValueError, TypeError, AttributeError):
            raise ValidationError('Invalid dependency ID.')
        digest = reference['content_hash']
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValidationError('Invalid dependency hash.')
    extra = {'ONTOLOGY': set(), 'NETWORK': {'concept_ids'},
             'MODULE': {'concept_ids', 'network_ids'}, 'RESEARCH': {'study_id'},
             'CASE': {'connector_id', 'dataset_version'}, 'SCORING': {'rule'}, 'SAFETY': {'policy'}}[kind]
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'id', 'label', 'source_ids'} | extra:
            raise ValidationError('Invalid registry entry schema.')
        if not _text(entry['id']) or not _text(entry['label']) or entry['id'] in ids:
            raise ValidationError('Registry IDs and labels must be non-empty and IDs unique.')
        ids.add(entry['id'])
        sources = entry['source_ids']
        if not isinstance(sources, list) or not sources or not all(_text(s) for s in sources):
            raise ValidationError('Every registry entry requires source references.')
        for key in extra:
            value = entry[key]
            if key == 'policy':
                from .safety_contracts import validate_safety_policy
                try:
                    validate_safety_policy(value)
                except ValueError as exc:
                    raise ValidationError(str(exc)) from exc
            elif key == 'rule':
                from .deterministic_scoring import validate_rule
                try:
                    validate_rule(value)
                except ValueError as exc:
                    raise ValidationError(str(exc)) from exc
            elif key.endswith('_ids'):
                if not isinstance(value, list) or not value or not all(_text(v) for v in value) or len(set(value)) != len(value):
                    raise ValidationError('Mapping references must be non-empty unique IDs.')
            elif not _text(value):
                raise ValidationError('Research study/case connector metadata is required.')
    try:
        canonical_hash(content)
    except (ValueError, TypeError):
        raise ValidationError('Registry content must be finite JSON.')


def registry_digest(registry):
    return canonical_hash({'kind': registry.kind, 'version': registry.version, 'content': registry.content})


def _ready(registry):
    validate_registry_content(registry.kind, registry.version, registry.content)
    if registry_digest(registry) != registry.content_hash:
        raise ValidationError('REGISTRY_INTEGRITY_FAILURE')
    decision = registry.decisions.first()
    if not decision or decision.state != READY.get(registry.kind, 'APPROVED'):
        raise ValidationError('REGISTRY_NOT_READY')
    return decision


@transaction.atomic
def create_registry(*, actor, kind, version, content):
    require_permission(actor, 'patients.add_governedregistry')
    registry = GovernedRegistry.objects.create(kind=kind, version=version, content=content, created_by=actor)
    GovernedRegistryDecision.objects.create(registry=registry, actor=actor,
        state=INITIAL.get(kind, 'DRAFT'), reason='Version created')
    return registry


def _check_mappings(registry, selected):
    for kind, ref in registry.content['dependencies'].items():
        target = selected.get(kind)
        if target is None or str(target.pk) != str(uuid.UUID(ref['id'])) or target.content_hash != ref['content_hash']:
            raise ValidationError('REGISTRY_VERSION_MISMATCH')
    if registry.kind == 'SAFETY':
        concepts = {entry['id'] for entry in selected['ONTOLOGY'].content['entries']}
        for entry in registry.content['entries']:
            requirements = entry['policy']['requirements'] + entry['policy']['soc_prerequisites']
            if not {item['concept_id'] for item in requirements} <= concepts:
                raise ValidationError('UNKNOWN_CANONICAL_CONCEPT')
    if registry.kind == 'SCORING':
        concepts = {entry['id'] for entry in selected['ONTOLOGY'].content['entries']}
        for entry in registry.content['entries']:
            if not {item['concept_id'] for item in entry['rule']['inputs']} <= concepts:
                raise ValidationError('UNKNOWN_CANONICAL_CONCEPT')
    if registry.kind in {'NETWORK', 'MODULE'}:
        concepts = {entry['id'] for entry in selected['ONTOLOGY'].content['entries']}
        networks = {entry['id'] for entry in selected['NETWORK'].content['entries']} if registry.kind == 'MODULE' else set()
        for entry in registry.content['entries']:
            if not set(entry['concept_ids']) <= concepts:
                raise ValidationError('UNKNOWN_CANONICAL_CONCEPT')
            if registry.kind == 'MODULE' and not set(entry['network_ids']) <= networks:
                raise ValidationError('UNKNOWN_CANONICAL_NETWORK')


@transaction.atomic
def resolve_registry_bundle(selection):
    """Return metadata readiness only; CASE validation does not prove live connectivity.

    Callers must authorize access and request every registry kind their operation needs.
    Locks guarantee a coherent read, not authorization to use the bundle indefinitely.
    """
    if not isinstance(selection, dict) or not selection or not set(selection) <= KINDS:
        raise ValidationError('Explicit registry selection is required.')
    try:
        wanted = {kind: uuid.UUID(str(value)) for kind, value in selection.items()}
    except (ValueError, TypeError, AttributeError):
        raise ValidationError('Invalid registry selection ID.')
    rows = list(GovernedRegistry.objects.select_for_update().filter(pk__in=wanted.values()).order_by('id'))
    selected = {row.kind: row for row in rows}
    if set(selected) != set(wanted) or any(selected[k].pk != v for k, v in wanted.items()):
        raise ValidationError('REGISTRY_SELECTION_MISMATCH')
    # Validate every dependency before inspecting its content; UUID ordering must
    # not allow a dependent registry to read unchecked/tampered metadata first.
    decisions = {kind: _ready(registry) for kind, registry in selected.items()}
    manifest = {}
    for kind, registry in selected.items():
        decision = decisions[kind]
        _check_mappings(registry, selected)
        manifest[kind] = {'id': str(registry.pk), 'version': registry.version,
            'content_hash': registry.content_hash, 'decision_id': decision.pk,
            'state': decision.state, 'entry_count': len(registry.content['entries'])}
    return {'registries': manifest, 'bundle_hash': canonical_hash(manifest),
            'status': 'REGISTRY_METADATA_VALIDATED', 'clinical_use_authorized': False}


@transaction.atomic
def transition_registry(*, registry_id, actor, state, reason):
    require_permission(actor, 'patients.approve_governedregistry')
    if not _text(reason):
        raise ValidationError('Decision reason is required.')
    registry = GovernedRegistry.objects.select_for_update().get(pk=registry_id)
    prior = registry.decisions.first()
    transitions = TRANSITIONS.get(registry.kind, COMMON_TRANSITIONS)
    if not isinstance(state, str) or not prior or state not in transitions.get(prior.state, set()):
        raise ValidationError('Invalid lifecycle transition.')
    if state == READY.get(registry.kind, 'APPROVED') and actor.pk == registry.created_by_id:
        raise PermissionDenied('Registry author cannot approve their own release.')
    validate_registry_content(registry.kind, registry.version, registry.content)
    if registry_digest(registry) != registry.content_hash:
        raise ValidationError('REGISTRY_INTEGRITY_FAILURE')
    # Cross-registry compatibility is checked at bundle resolution, including after retirement.
    return GovernedRegistryDecision.objects.create(registry=registry, actor=actor, state=state, reason=reason)
