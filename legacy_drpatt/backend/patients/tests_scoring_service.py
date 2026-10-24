"""Registry/evidence/scoring integration using synthetic arithmetic only."""
from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APIClient

from .analysis_inputs import prepare_analysis_inputs
from .evidence_service import append_evidence
from .registry_governance import create_registry, transition_registry
from .scoring_service import execute_scoring_rule
from .scoring_history import read_scoring_run, verify_run_integrity
from .models import ScoringRun
from . import tests_analysis_inputs as input_fixtures
from .tests_deterministic_scoring import synthetic_rule


class ScoringServiceTests(TestCase):
    def setUp(self):
        # Reuse the synthetic setup only, without inheriting/rerunning its test methods.
        input_fixtures.AnalysisInputPreviewTests.setUp(self)
        self.author.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='patients', codename__in=['execute_governedscoring', 'view_scoringrun']))
        self.author = User.objects.get(pk=self.author.pk)
        self.scoring = create_registry(actor=self.author, kind='SCORING', version='test-v1',
            content={'entries': [{'id': 'synthetic-rule', 'label': 'Synthetic arithmetic',
                                 'source_ids': ['test-source'], 'rule': synthetic_rule()}],
                     'dependencies': {'ONTOLOGY': {'id': str(self.ontology.pk),
                                                  'content_hash': self.ontology.content_hash}}})
        transition_registry(registry_id=self.scoring.pk, actor=self.reviewer,
                            state='APPROVED', reason='Synthetic test only')
        self.evidence, _ = append_evidence(patient_id=self.patient.pk, actor=self.author,
            registry_id=self.unit.pk, source=self.source, verify=True)
        self.selection = {'ONTOLOGY': str(self.ontology.pk), 'SCORING': str(self.scoring.pk)}
        self.preview = prepare_analysis_inputs(patient_id=self.patient.pk, actor=self.author,
            unit_registry_id=self.unit.pk, selection=self.selection)

    def execute(self, **overrides):
        args = {'patient_id': self.patient.pk, 'actor': self.author, 'unit_registry_id': self.unit.pk,
                'selection': self.selection, 'expected_manifest_hash': self.preview['manifest_hash'],
                'rule_id': 'synthetic-rule', 'evidence_ids': [str(self.evidence.pk)]}
        args.update(overrides)
        return execute_scoring_rule(**args)

    def test_approved_rule_runs_with_provenance(self):
        result = self.execute()
        self.assertEqual(result['status'], 'CALCULATED')
        self.assertEqual(result['score'], '25')
        self.assertEqual(result['contributions'][0]['source_id'], 'lab-1')
        self.assertEqual(result['manifest_hash'], self.preview['manifest_hash'])
        self.assertFalse(result['clinical_use_authorized'])
        self.assertEqual(result['result_hash'], self.execute()['result_hash'])

    def test_stale_manifest_never_calculates(self):
        result = self.execute(expected_manifest_hash='0' * 64)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIsNone(result['score'])

    def test_retired_rule_rejected_on_execution(self):
        transition_registry(registry_id=self.scoring.pk, actor=self.reviewer,
                            state='RETIRED', reason='Synthetic retirement')
        with self.assertRaises(ValidationError):
            self.execute()

    def test_unselected_or_cross_patient_evidence_rejected(self):
        with self.assertRaises(ValidationError):
            self.execute(evidence_ids=['not-an-active-evidence-id'])

    def test_explicit_execute_permission_required(self):
        with self.assertRaises(PermissionDenied):
            self.execute(actor=self.reviewer)

    def test_missing_review_hash_rejected(self):
        with self.assertRaises(ValidationError):
            self.execute(expected_manifest_hash=None)

    def test_history_contains_exact_inputs_and_replays(self):
        result = self.execute()
        run = ScoringRun.objects.get(pk=result['scoring_run_id'])
        self.assertEqual(run.manifest, self.preview['manifest'])
        self.assertEqual(run.result['score'], result['score'])
        history = read_scoring_run(patient_id=self.patient.pk, run_id=run.pk, actor=self.author)
        self.assertEqual(history['replay']['status'], 'MATCH')
        self.assertTrue(history['historical_only'])
        self.assertFalse(history['clinical_use_authorized'])

    def test_stale_block_is_persisted_without_arithmetic(self):
        result = self.execute(expected_manifest_hash='0' * 64)
        history = read_scoring_run(patient_id=self.patient.pk,
                                    run_id=result['scoring_run_id'], actor=self.author)
        self.assertEqual(history['replay']['status'], 'NOT_EXECUTED')
        self.assertEqual(history['result']['expected_manifest_hash'], '0' * 64)

    def test_history_does_not_change_after_source_correction(self):
        result = self.execute()
        append_evidence(patient_id=self.patient.pk, actor=self.author, registry_id=self.unit.pk,
            source={**self.source, 'value': 30}, verify=True, supersedes=self.evidence.pk,
            correction_reason='Synthetic correction')
        history = read_scoring_run(patient_id=self.patient.pk,
                                    run_id=result['scoring_run_id'], actor=self.author)
        self.assertEqual(history['result']['score'], '25')
        self.assertEqual(history['replay']['status'], 'MATCH')

    def test_retirement_does_not_rewrite_historical_replay(self):
        result = self.execute()
        transition_registry(registry_id=self.scoring.pk, actor=self.reviewer,
                            state='RETIRED', reason='Synthetic retirement')
        history = read_scoring_run(patient_id=self.patient.pk,
                                    run_id=result['scoring_run_id'], actor=self.author)
        self.assertEqual(history['replay']['status'], 'MATCH')
        self.assertFalse(history['clinical_use_authorized'])

    def test_history_tampering_detected(self):
        result = self.execute()
        run = ScoringRun.objects.get(pk=result['scoring_run_id'])
        run.result['score'] = '99'
        with self.assertRaises(ValidationError):
            verify_run_integrity(run)

    def test_history_cannot_be_overwritten_or_deleted(self):
        result = self.execute()
        run = ScoringRun.objects.get(pk=result['scoring_run_id'])
        with self.assertRaises(ValidationError):
            run.save()
        with self.assertRaises(ValidationError):
            ScoringRun.objects.filter(pk=run.pk).update(result={})
        with self.assertRaises(ValidationError):
            run.delete()

    def test_audit_write_failure_does_not_return_success(self):
        with patch('patients.scoring_service.ScoringRun.objects.create', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                self.execute()
        self.assertFalse(ScoringRun.objects.exists())

    def test_history_api_requires_permission(self):
        result = self.execute()
        client = APIClient()
        client.force_authenticate(self.reviewer)
        path = f'/api/patients/{self.patient.pk}/scoring-runs/{result["scoring_run_id"]}/'
        self.assertEqual(client.get(path).status_code, 403)
        client.force_authenticate(self.author)
        response = client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['replay']['status'], 'MATCH')
