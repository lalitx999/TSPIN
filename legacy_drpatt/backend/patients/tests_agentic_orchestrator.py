"""Synthetic workflow-control tests; handlers below do not perform clinical review."""
from copy import deepcopy
from unittest import TestCase

from .agentic_orchestrator import ROLES, REVIEWERS, run_workflow


def output(envelope, decision='PASS'):
    role = envelope['role']
    payload = {}
    if role == 'A13':
        payload['draft'] = {'synthetic_round': envelope['round']}
    if role in REVIEWERS | {'A17', 'A18'}:
        payload['reviewed_draft_hash'] = envelope['draft_hash']
    return {'role': role, 'input_hash': envelope['input_hash'], 'decision': decision,
            'payload': payload, 'issues': [] if decision == 'PASS' else [{'code': 'SYNTHETIC_FAILURE'}]}


def handlers():
    return {role: {'version': 'synthetic-v1', 'run': output} for role, _ in ROLES}


class AgenticOrchestratorTests(TestCase):
    def run_case(self, adapters=None, **kwargs):
        return run_workflow(manifest={'patient_id': 'SYNTHETIC'},
                            handlers=handlers() if adapters is None else adapters, **kwargs)

    def test_all_roles_run_in_order_but_do_not_authorize_publication(self):
        result = self.run_case()
        self.assertEqual(result['state'], 'WORKFLOW_CHECKS_PASSED')
        self.assertEqual([row['role'] for row in result['trace']], [role for role, _ in ROLES])
        self.assertFalse(result['clinical_use_authorized'])
        self.assertEqual(result['rounds_used'], 1)

    def test_missing_handler_never_passes(self):
        result = self.run_case({})
        self.assertEqual(result['state'], 'HUMAN_REVIEW_REQUIRED')
        self.assertEqual(result['reason'], 'HANDLER_NOT_CONFIGURED:A01')

    def test_missing_auditor_stops_before_patient_communication(self):
        adapters = handlers()
        del adapters['A14']
        result = self.run_case(adapters)
        self.assertNotIn('A17', [row['role'] for row in result['trace']])
        self.assertEqual(result['state'], 'HUMAN_REVIEW_REQUIRED')

    def test_red_team_failure_retries_three_times_then_escalates(self):
        adapters = handlers()
        adapters['A15']['run'] = lambda envelope: output(envelope, 'FAIL')
        result = self.run_case(adapters)
        self.assertEqual(result['reason'], 'MAX_ROUNDS_REACHED')
        self.assertEqual(result['rounds_used'], 3)
        self.assertEqual(sum(row['role'] == 'A15' for row in result['trace']), 3)
        self.assertEqual(sum(row['role'] == 'A14' for row in result['trace']), 3)
        self.assertEqual(sum(row['role'] == 'A16' for row in result['trace']), 3)
        self.assertNotIn('A17', [row['role'] for row in result['trace']])

    def test_revised_draft_rechecked_by_all_auditors(self):
        adapters = handlers()
        feedback = []
        def composer(envelope):
            feedback.append(envelope['revision_feedback'])
            return output(envelope)
        adapters['A13']['run'] = composer
        adapters['A14']['run'] = lambda envelope: output(envelope, 'FAIL' if envelope['round'] == 1 else 'PASS')
        result = self.run_case(adapters)
        self.assertEqual(result['state'], 'WORKFLOW_CHECKS_PASSED')
        self.assertEqual(result['rounds_used'], 2)
        self.assertTrue(feedback[1])
        hashes = [row['reviewed_draft_hash'] for row in result['trace'] if row['role'] == 'A16']
        self.assertNotEqual(hashes[0], hashes[1])

    def test_safety_escalation_never_retries(self):
        adapters = handlers()
        adapters['A08']['run'] = lambda envelope: output(envelope, 'ESCALATE')
        result = self.run_case(adapters)
        self.assertEqual(result['state'], 'ESCALATED')
        self.assertEqual(result['rounds_used'], 1)
        self.assertEqual(result['trace'][-1]['role'], 'A08')

    def test_identity_failure_is_not_repaired_by_reasoning_retry(self):
        adapters = handlers()
        adapters['A01']['run'] = lambda envelope: output(envelope, 'FAIL')
        result = self.run_case(adapters)
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertEqual(len(result['trace']), 1)

    def test_stale_output_input_hash_is_rejected(self):
        adapters = handlers()
        adapters['A01']['run'] = lambda envelope: {**output(envelope), 'input_hash': 'stale'}
        self.assertEqual(self.run_case(adapters)['state'], 'BLOCKED')

    def test_review_of_previous_draft_rejected(self):
        adapters = handlers()
        def stale(envelope):
            result = output(envelope)
            result['payload']['reviewed_draft_hash'] = 'old-draft'
            return result
        adapters['A15']['run'] = stale
        self.assertEqual(self.run_case(adapters)['state'], 'BLOCKED')

    def test_patient_communication_cannot_replace_reviewed_draft(self):
        adapters = handlers()
        def mutation(envelope):
            result = output(envelope)
            result['payload']['draft'] = {'new_claim': 'not reviewed'}
            return result
        adapters['A17']['run'] = mutation
        self.assertEqual(self.run_case(adapters)['state'], 'BLOCKED')

    def test_handler_mutation_does_not_change_input_or_other_roles(self):
        source = {'patient_id': 'SYNTHETIC', 'value': 1}
        original = deepcopy(source)
        adapters = handlers()
        def mutation(envelope):
            envelope['manifest']['value'] = 99
            return output(envelope)
        adapters['A01']['run'] = mutation
        def check(envelope):
            self.assertEqual(envelope['manifest']['value'], 1)
            return output(envelope)
        adapters['A02']['run'] = check
        result = run_workflow(manifest=source, handlers=adapters)
        self.assertEqual(source, original)
        self.assertEqual(result['state'], 'WORKFLOW_CHECKS_PASSED')

    def test_exception_details_not_copied_into_trace(self):
        adapters = handlers()
        def broken(envelope):
            raise RuntimeError('SENSITIVE-TEST-STRING')
        adapters['A01']['run'] = broken
        result = self.run_case(adapters)
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertNotIn('SENSITIVE-TEST-STRING', str(result))

    def test_retry_limit_cannot_be_disabled(self):
        for count in (0, 4, True, -1):
            with self.assertRaises(ValueError):
                self.run_case(max_rounds=count)

    def test_pass_with_unresolved_issues_is_rejected(self):
        adapters = handlers()
        adapters['A01']['run'] = lambda envelope: {**output(envelope), 'issues': [{'code': 'UNRESOLVED'}]}
        self.assertEqual(self.run_case(adapters)['state'], 'BLOCKED')
