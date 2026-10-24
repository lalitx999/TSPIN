"""Synthetic database/API tests for unreleased evidence artifacts."""
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from . import tests_scoring_service as fixtures
from .agentic_service import create_evidence_report_drafts, create_workflow_review, read_agentic_artifact
from .evidence_service import append_evidence
from .models import AgenticArtifact, Patient


class EvidenceArtifactServiceTests(TestCase):
    def setUp(self):
        fixtures.ScoringServiceTests.setUp(self)
        self.author.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='patients',
            codename__in=['add_agenticartifact', 'view_agenticartifact']))
        self.author = User.objects.get(pk=self.author.pk)
        self.args = dict(patient_id=self.patient.pk, actor=self.author,
                         unit_registry_id=self.unit.pk, selection=self.selection,
                         expected_manifest_hash=self.preview['manifest_hash'])

    def create(self, **overrides):
        return create_evidence_report_drafts(**{**self.args, **overrides})

    def history(self, result):
        return read_agentic_artifact(**dict(patient_id=self.patient.pk,
            artifact_id=result['artifact_id'], actor=self.author))

    def test_persisted_three_editions_are_unapproved_and_reproducible(self):
        result = self.create()
        history = self.history(result)
        packet = history['payload']['packet']
        self.assertEqual(set(packet['editions']), {'PHYSICIAN', 'PATIENT', 'MULTI_OMICS'})
        facts = [edition['facts'] for edition in packet['editions'].values()]
        self.assertTrue(all(value == facts[0] for value in facts))
        self.assertEqual(history['payload']['manifest'], self.preview['manifest'])
        self.assertEqual(result['state'], 'DRAFT')
        self.assertFalse(history['clinical_use_authorized'])
        self.assertTrue(history['historical_only'])

    def test_stale_review_hash_cannot_create_artifact(self):
        with self.assertRaises(ValidationError):
            self.create(expected_manifest_hash='0' * 64)
        self.assertFalse(AgenticArtifact.objects.exists())

    def test_source_correction_blocks_creation_but_preserves_history(self):
        result = self.create()
        before = self.history(result)
        append_evidence(patient_id=self.patient.pk, actor=self.author, registry_id=self.unit.pk,
            source={**self.source, 'value': 30}, supersedes=self.evidence.pk,
            verify=True, correction_reason='Synthetic correction')
        with self.assertRaises(ValidationError):
            self.create()
        self.assertEqual(before, self.history(result))

    def test_explicit_permission_required(self):
        with self.assertRaises(PermissionDenied):
            self.create(actor=self.reviewer)

    def test_permission_alone_does_not_release_drafts_to_nonclinical_user(self):
        self.reviewer.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='patients',
            codename__in=['add_agenticartifact', 'view_agenticartifact']))
        outsider = User.objects.get(pk=self.reviewer.pk)
        with self.assertRaises(PermissionDenied):
            self.create(actor=outsider)
        result = self.create()
        with self.assertRaises(PermissionDenied):
            read_agentic_artifact(patient_id=self.patient.pk,
                artifact_id=result['artifact_id'], actor=outsider)

    def test_write_failure_returns_no_success(self):
        with patch('patients.agentic_service.AgenticArtifact.objects.create', side_effect=RuntimeError('synthetic')):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(AgenticArtifact.objects.exists())

    def test_append_only_artifact(self):
        result = self.create()
        artifact = AgenticArtifact.objects.get(pk=result['artifact_id'])
        with self.assertRaises(ValidationError):
            artifact.save()
        with self.assertRaises(ValidationError):
            artifact.delete()
        with self.assertRaises(ValidationError):
            AgenticArtifact.objects.filter(pk=artifact.pk).update(payload={})

    def test_history_is_scoped_to_requested_patient(self):
        result = self.create()
        other = Patient.objects.create(hn='TEST-OTHER-ARTIFACT', legacy_id='TEST-OTHER-ARTIFACT',
                                       first_name='Synthetic', last_name='Other')
        with self.assertRaises(AgenticArtifact.DoesNotExist):
            read_agentic_artifact(patient_id=other.pk, artifact_id=result['artifact_id'], actor=self.author)
        client = APIClient()
        client.force_authenticate(self.author)
        response = client.get(f'/api/patients/{other.pk}/agentic-artifacts/{result["artifact_id"]}/')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('payload', response.data)

    def test_history_detects_payload_tampering(self):
        result = self.create()
        artifact = AgenticArtifact.objects.get(pk=result['artifact_id'])
        artifact.payload['packet']['clinical_use_authorized'] = True
        with patch('patients.agentic_service.AgenticArtifact.objects.select_related') as query:
            query.return_value.get.return_value = artifact
            with self.assertRaisesMessage(ValidationError, 'AGENTIC_ARTIFACT_INTEGRITY_FAILURE'):
                self.history(result)

    def test_release_readiness_is_read_only_and_never_authorizes_draft(self):
        from .release_readiness import inspect_release_readiness
        result = self.create()
        before = self.history(result)
        readiness = inspect_release_readiness(patient_id=self.patient.pk,
            artifact_id=result['artifact_id'], actor=self.author)
        self.assertTrue(readiness['input_is_current'])
        self.assertFalse(readiness['send_allowed'])
        self.assertFalse(readiness['clinical_use_authorized'])
        self.assertEqual(readiness['state'], 'BLOCKED')
        self.assertIn('ARTIFACT_BOUND_PHYSICIAN_APPROVAL_UNAVAILABLE',
                      [issue['code'] for issue in readiness['issues']])
        self.assertEqual(before, self.history(result))
        self.assertEqual(AgenticArtifact.objects.count(), 1)

    def test_release_readiness_detects_changed_patient_identity(self):
        from .release_readiness import inspect_release_readiness
        result = self.create()
        self.patient.first_name = 'Synthetic corrected name'
        self.patient.save()
        readiness = inspect_release_readiness(patient_id=self.patient.pk,
            artifact_id=result['artifact_id'], actor=self.author)
        self.assertFalse(readiness['input_is_current'])
        self.assertIn('STALE_ANALYSIS_INPUT', [issue['code'] for issue in readiness['issues']])

    def test_release_readiness_rechecks_retired_registry(self):
        from .registry_governance import transition_registry
        from .release_readiness import inspect_release_readiness
        result = self.create()
        transition_registry(registry_id=self.scoring.pk, actor=self.reviewer,
                            state='RETIRED', reason='Synthetic retirement')
        readiness = inspect_release_readiness(patient_id=self.patient.pk,
            artifact_id=result['artifact_id'], actor=self.author)
        self.assertFalse(readiness['input_is_current'])
        self.assertFalse(readiness['send_allowed'])
        self.assertIn('CURRENT_INPUT_REVALIDATION_FAILED', [issue['code'] for issue in readiness['issues']])

    def test_release_readiness_api_permissions_and_no_post(self):
        result = self.create()
        client = APIClient()
        path = f'/api/patients/{self.patient.pk}/agentic-artifacts/{result["artifact_id"]}/release-readiness/'
        client.force_authenticate(self.reviewer)
        self.assertEqual(client.get(path).status_code, 403)
        client.force_authenticate(self.author)
        response = client.get(path)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data['send_allowed'])
        self.assertEqual(client.post(path, {}, format='json').status_code, 405)

    def test_api_rejects_client_supplied_packet_and_allows_history(self):
        client = APIClient()
        client.force_authenticate(self.author)
        path = f'/api/patients/{self.patient.pk}/agentic-artifacts/'
        body = {key: value for key, value in self.args.items() if key not in {'patient_id', 'actor'}}
        body['unit_registry_id'] = str(body['unit_registry_id'])
        body['kind'] = 'EVIDENCE_DRAFT'
        self.assertEqual(client.post(path, {**body, 'packet': {}}, format='json').status_code, 400)
        response = client.post(path, body, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        history = client.get(path + response.data['artifact_id'] + '/')
        self.assertEqual(history.status_code, 200, history.data)
        self.assertFalse(history.data['clinical_use_authorized'])


class WorkflowServiceTests(TestCase):
    def setUp(self):
        from . import tests_safety_service as safety_fixtures
        from .analysis_inputs import prepare_analysis_inputs
        from .registry_governance import create_registry, transition_registry
        from .scoring_service import execute_scoring_rule
        from .tests_deterministic_scoring import synthetic_rule
        safety_fixtures.SafetyPreviewTests.setUp(self)
        self.author.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='patients', codename__in=[
                'add_agenticartifact', 'view_agenticartifact', 'execute_governedscoring', 'view_scoringrun']))
        self.author = User.objects.get(pk=self.author.pk)
        parent = self.patient.evidence_revisions.get(payload__concept_id='safety-referral')
        self.numeric_source = {**self.source, 'concept_id': 'safety-referral', 'unit': '',
                               'value': 12, 'source_timestamp': parent.payload['source_timestamp']}
        self.numeric, _ = append_evidence(patient_id=self.patient.pk, actor=self.author,
            registry_id=self.safety_units.pk, source=self.numeric_source, verify=True,
            supersedes=parent.pk, correction_reason='Synthetic arithmetic fixture only')
        rule = synthetic_rule()
        rule['inputs'][0].update(concept_id='safety-referral', unit='')
        scoring = create_registry(actor=self.author, kind='SCORING', version='workflow-test',
            content={'entries': [{'id': 'test-rule', 'label': 'Synthetic arithmetic',
                'source_ids': ['synthetic-source'], 'rule': rule}],
                'dependencies': {'ONTOLOGY': {'id': str(self.safety_ontology.pk),
                    'content_hash': self.safety_ontology.content_hash}}})
        transition_registry(registry_id=scoring.pk, actor=self.reviewer,
                            state='APPROVED', reason='Synthetic test only')
        self.selection['SCORING'] = str(scoring.pk)
        preview = prepare_analysis_inputs(patient_id=self.patient.pk, actor=self.author,
            unit_registry_id=self.safety_units.pk, selection=self.selection)
        self.args = dict(patient_id=self.patient.pk, actor=self.author,
            unit_registry_id=self.safety_units.pk, selection=self.selection,
            expected_manifest_hash=preview['manifest_hash'])
        run = execute_scoring_rule(**self.args, rule_id='test-rule', evidence_ids=[str(self.numeric.pk)])
        self.assertEqual(run['status'], 'CALCULATED')
        self.args.update(scoring_run_id=run['scoring_run_id'], safety_policy_id='test-policy')

    def test_missing_clinical_adapter_stops_and_persists_trace(self):
        result = create_workflow_review(**self.args)
        history = read_agentic_artifact(patient_id=self.patient.pk,
            artifact_id=result['artifact_id'], actor=self.author)
        workflow = history['payload']['workflow']
        self.assertEqual(workflow['state'], 'HUMAN_REVIEW_REQUIRED')
        self.assertEqual(workflow['reason'], 'HANDLER_NOT_CONFIGURED:A07')
        self.assertEqual([row['role'] for row in workflow['trace']],
                         ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07'])
        self.assertFalse(workflow['clinical_use_authorized'])

    def test_corrected_evidence_rejects_old_scoring_run(self):
        from .analysis_inputs import prepare_analysis_inputs
        append_evidence(patient_id=self.patient.pk, actor=self.author, registry_id=self.safety_units.pk,
            source={**self.numeric_source, 'value': 13}, verify=True, supersedes=self.numeric.pk,
            correction_reason='Synthetic correction')
        preview = prepare_analysis_inputs(patient_id=self.patient.pk, actor=self.author,
            unit_registry_id=self.safety_units.pk, selection=self.selection)
        with self.assertRaisesMessage(ValidationError, 'SCORING_RUN_INPUTS_STALE'):
            create_workflow_review(**{**self.args, 'expected_manifest_hash': preview['manifest_hash']})
        self.assertFalse(AgenticArtifact.objects.exists())

    def test_stale_hash_stops_before_any_clinical_role(self):
        result = create_workflow_review(**{**self.args, 'expected_manifest_hash': '0' * 64})
        history = read_agentic_artifact(patient_id=self.patient.pk,
            artifact_id=result['artifact_id'], actor=self.author)
        self.assertEqual(history['payload']['workflow']['state'], 'BLOCKED')
        self.assertEqual(history['payload']['workflow']['reason'], 'STOP:A01')

    def test_emergency_precheck_precedes_missing_clinical_adapter(self):
        from .analysis_inputs import prepare_analysis_inputs
        from .scoring_service import execute_scoring_rule
        parent = self.patient.evidence_revisions.get(payload__concept_id='safety-emergency')
        append_evidence(patient_id=self.patient.pk, actor=self.author, registry_id=self.safety_units.pk,
            source={**self.source, 'concept_id': 'safety-emergency', 'unit': '', 'value': 'EMERGENCY',
                    'source_type': 'PHYSICIAN_OBSERVED', 'source_timestamp': parent.payload['source_timestamp']},
            supersedes=parent.pk, verify=True, correction_reason='Synthetic alert fixture')
        preview = prepare_analysis_inputs(patient_id=self.patient.pk, actor=self.author,
            unit_registry_id=self.safety_units.pk, selection=self.selection)
        args = {**self.args, 'expected_manifest_hash': preview['manifest_hash']}
        scoring_args = {key: value for key, value in args.items()
                        if key not in {'scoring_run_id', 'safety_policy_id'}}
        run = execute_scoring_rule(**scoring_args, rule_id='test-rule', evidence_ids=[str(self.numeric.pk)])
        args['scoring_run_id'] = run['scoring_run_id']
        with patch('patients.agentic_service.run_workflow') as controller:
            result = create_workflow_review(**args)
            controller.assert_not_called()
        history = read_agentic_artifact(patient_id=self.patient.pk,
            artifact_id=result['artifact_id'], actor=self.author)
        workflow = history['payload']['workflow']
        self.assertEqual(workflow['state'], 'ESCALATED')
        self.assertEqual(workflow['reason'], 'SAFETY_PRECHECK_ALERT')
        self.assertEqual(workflow['rounds_used'], 0)
        self.assertEqual(workflow['trace'][0]['safety']['safety_state'], 'EMERGENCY')
        self.assertFalse(workflow['clinical_use_authorized'])
