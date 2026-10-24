"""Synthetic metadata only; these fixtures are not clinical knowledge."""
from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .registry_governance import create_registry, transition_registry, resolve_registry_bundle


class RegistryGovernanceTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='metadata-author')
        self.reviewer = User.objects.create_user(username='metadata-reviewer')
        for user in (self.author, self.reviewer):
            user.user_permissions.add(*Permission.objects.filter(content_type__app_label='patients',
                codename__in=['add_governedregistry', 'approve_governedregistry', 'view_governedregistry']))

    def create(self, kind='ONTOLOGY', version='test-v1', entries=None, dependencies=None):
        if entries is None:
            entries = [{'id': 'C1', 'label': 'Synthetic concept', 'source_ids': ['test-source']}]
        return create_registry(actor=self.author, kind=kind, version=version,
            content={'entries': entries, 'dependencies': dependencies or {}})

    def transition(self, registry, state='APPROVED'):
        return transition_registry(registry_id=registry.pk, actor=self.reviewer,
                                   state=state, reason='Synthetic test decision')

    def reference(self, registry):
        return {'id': str(registry.pk), 'content_hash': registry.content_hash}

    def network(self, ontology, concept='C1'):
        return self.create(kind='NETWORK', dependencies={'ONTOLOGY': self.reference(ontology)},
            entries=[{'id': 'N1', 'label': 'Synthetic network', 'source_ids': ['test-source'],
                      'concept_ids': [concept]}])

    def test_draft_and_provisional_not_ready(self):
        registry = self.create()
        for state in ('DRAFT', 'PROVISIONAL'):
            if state != 'DRAFT':
                self.transition(registry, state)
            with self.assertRaisesMessage(ValidationError, 'REGISTRY_NOT_READY'):
                resolve_registry_bundle({'ONTOLOGY': str(registry.pk)})

    def test_self_approval_rejected(self):
        registry = self.create()
        with self.assertRaises(PermissionDenied):
            transition_registry(registry_id=registry.pk, actor=self.author,
                                 state='APPROVED', reason='Self approval attempt')

    def test_valid_bundle_not_clinical_authorization(self):
        ontology = self.create()
        network = self.network(ontology)
        self.transition(ontology)
        self.transition(network)
        first = resolve_registry_bundle({'ONTOLOGY': str(ontology.pk), 'NETWORK': str(network.pk)})
        second = resolve_registry_bundle({'NETWORK': str(network.pk), 'ONTOLOGY': str(ontology.pk)})
        self.assertEqual(first['bundle_hash'], second['bundle_hash'])
        self.assertFalse(first['clinical_use_authorized'])

    def test_missing_dependency_blocked(self):
        ontology = self.create()
        network = self.network(ontology)
        self.transition(network)
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_VERSION_MISMATCH'):
            resolve_registry_bundle({'NETWORK': str(network.pk)})

    def test_version_skew_blocked(self):
        old = self.create()
        newer = self.create(version='test-v2')
        network = self.network(old)
        self.transition(newer)
        self.transition(network)
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_VERSION_MISMATCH'):
            resolve_registry_bundle({'ONTOLOGY': str(newer.pk), 'NETWORK': str(network.pk)})

    def test_unknown_concept_mapping_blocked(self):
        ontology = self.create()
        network = self.network(ontology, concept='UNKNOWN')
        self.transition(ontology)
        self.transition(network)
        with self.assertRaisesMessage(ValidationError, 'UNKNOWN_CANONICAL_CONCEPT'):
            resolve_registry_bundle({'ONTOLOGY': str(ontology.pk), 'NETWORK': str(network.pk)})

    def test_module_mapping_requires_known_network(self):
        ontology = self.create()
        network = self.network(ontology)
        module = self.create(kind='MODULE', dependencies={
            'ONTOLOGY': self.reference(ontology), 'NETWORK': self.reference(network)}, entries=[{
            'id': 'M1', 'label': 'Synthetic module', 'source_ids': ['test-source'],
            'concept_ids': ['C1'], 'network_ids': ['UNKNOWN']}])
        for registry in (ontology, network, module):
            self.transition(registry)
        with self.assertRaisesMessage(ValidationError, 'UNKNOWN_CANONICAL_NETWORK'):
            resolve_registry_bundle({r.kind: str(r.pk) for r in (ontology, network, module)})

    def test_research_cannot_skip_verification(self):
        research = self.create(kind='RESEARCH', entries=[{'id': 'R1', 'label': 'Synthetic study',
            'source_ids': ['test-source'], 'study_id': 'SYNTHETIC-STUDY'}])
        with self.assertRaises(ValidationError):
            self.transition(research)
        self.transition(research, 'VERIFIED')
        self.transition(research)
        self.assertEqual(resolve_registry_bundle({'RESEARCH': str(research.pk)})['status'],
                         'REGISTRY_METADATA_VALIDATED')

    def test_research_requires_study_id(self):
        with self.assertRaises(ValidationError):
            self.create(kind='RESEARCH', entries=[{'id': 'R1', 'label': 'Synthetic', 'source_ids': ['s']}])

    def test_case_unavailable_and_connected_not_validated(self):
        case = self.create(kind='CASE', entries=[{'id': 'K1', 'label': 'Synthetic connector',
            'source_ids': ['test-source'], 'connector_id': 'test-connector', 'dataset_version': 'v1'}])
        for state in ('UNAVAILABLE', 'CONNECTED'):
            if state == 'CONNECTED':
                self.transition(case, state)
            with self.assertRaisesMessage(ValidationError, 'REGISTRY_NOT_READY'):
                resolve_registry_bundle({'CASE': str(case.pk)})
        self.transition(case, 'VALIDATED')
        self.assertFalse(resolve_registry_bundle({'CASE': str(case.pk)})['clinical_use_authorized'])
        self.transition(case, 'UNAVAILABLE')
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_NOT_READY'):
            resolve_registry_bundle({'CASE': str(case.pk)})

    def test_retirement_blocks_fresh_resolve(self):
        registry = self.create()
        self.transition(registry)
        self.transition(registry, 'RETIRED')
        with self.assertRaisesMessage(ValidationError, 'REGISTRY_NOT_READY'):
            resolve_registry_bundle({'ONTOLOGY': str(registry.pk)})

    def test_source_references_required(self):
        with self.assertRaises(ValidationError):
            self.create(entries=[{'id': 'C1', 'label': 'Synthetic', 'source_ids': []}])

    def test_unknown_payload_fields_rejected(self):
        with self.assertRaises(ValidationError):
            self.create(entries=[{'id': 'C1', 'label': 'Synthetic', 'source_ids': ['s'], 'patient_id': 1}])

    def test_no_overwrite_or_decision_delete(self):
        registry = self.create()
        with self.assertRaises(ValidationError):
            registry.save()
        with self.assertRaises(ValidationError):
            registry.decisions.all().delete()

    def test_api_permission_and_read_only_resolution(self):
        registry = self.create()
        self.transition(registry)
        client = APIClient()
        unprivileged = User.objects.create_user(username='no-registry-permission', is_staff=True)
        client.force_authenticate(unprivileged)
        payload = {'selection': {'ONTOLOGY': str(registry.pk)}}
        self.assertEqual(client.post('/api/registries/validate-bundle/', payload, format='json').status_code, 403)
        client.force_authenticate(self.reviewer)
        result = client.post('/api/registries/validate-bundle/', payload, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.data['clinical_use_authorized'])
        self.assertEqual(registry.decisions.count(), 2)

    def test_invalid_selection_has_controlled_error(self):
        for selection in ({}, {'ONTOLOGY': 'not-a-uuid'}, {'UNRECOGNIZED': 'value'}):
            with self.assertRaises(ValidationError):
                resolve_registry_bundle(selection)
