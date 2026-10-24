"""Tool-free workflow controller. Handlers are trusted backend code, never user input.

This module orders checks; it does not implement clinical reasoning, independent
model review, physician identity verification, or permission to publish a report.
"""
from copy import deepcopy
from datetime import datetime, timezone

from .canonical_state import canonical_hash

ROLES = (
    ('A01', 'identity_and_sources'), ('A02', 'completeness'), ('A03', 'provenance'),
    ('A04', 'registry'), ('A05', 'deterministic_scoring'), ('A06', 'contradictions'),
    ('A07', 'clinical_logic'), ('A08', 'safety'), ('A09', 'standard_of_care'),
    ('A10', 'research'), ('A11', 'cases'), ('A12', 'module_matching'),
    ('A13', 'report_composer'), ('A14', 'independent_auditor'), ('A15', 'red_team'),
    ('A16', 'cross_report_consistency'), ('A17', 'patient_communication'),
    ('A18', 'physician_approval'),
)
REVIEWERS = frozenset({'A14', 'A15', 'A16'})
DECISIONS = frozenset({'PASS', 'FAIL', 'DEFER', 'ESCALATE', 'STOP'})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _validate_result(result, role, input_hash, draft_hash):
    if not isinstance(result, dict) or set(result) != {'role', 'input_hash', 'decision', 'payload', 'issues'}:
        raise ValueError('Invalid handler output envelope.')
    if result['role'] != role or result['input_hash'] != input_hash:
        raise ValueError('Handler output does not match this role/input.')
    if not isinstance(result['decision'], str) or result['decision'] not in DECISIONS:
        raise ValueError('Invalid handler decision.')
    if not isinstance(result['payload'], dict) or not isinstance(result['issues'], list):
        raise ValueError('Handler payload/issues must be structured.')
    if any(not isinstance(issue, dict) or not isinstance(issue.get('code'), str) or not issue['code']
           for issue in result['issues']):
        raise ValueError('Every issue requires a code.')
    if result['decision'] == 'PASS' and result['issues']:
        raise ValueError('Unresolved issues cannot accompany PASS.')
    if result['decision'] != 'PASS' and not result['issues']:
        raise ValueError('Non-pass decisions require a structured reason.')
    if role != 'A13' and 'draft' in result['payload']:
        raise ValueError('Only the composer may replace the draft.')
    if result['decision'] == 'PASS' and role == 'A13':
        if not isinstance(result['payload'].get('draft'), dict) or not result['payload']['draft']:
            raise ValueError('Composer must return a non-empty structured draft.')
    if role in REVIEWERS | {'A17', 'A18'}:
        if draft_hash is None or result['payload'].get('reviewed_draft_hash') != draft_hash:
            raise ValueError('Review must bind the current draft hash.')
    canonical_hash(result)  # Also refuse non-JSON values, NaN, and infinities.


def run_workflow(*, manifest, handlers, max_rounds=3):
    """Run at most three complete attempts against one immutable input manifest.

    Only failed A14–A16 draft checks can request a revision. Every revision reruns
    all roles from fresh inputs. Missing adapters/invalid output/errors never PASS.
    Adapters must be bounded/time-limited and side-effect-free; this synchronous
    controller does not forcibly interrupt an adapter or execute external tools.
    """
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError('An explicit input manifest is required.')
    if type(max_rounds) is not int or not 1 <= max_rounds <= 3:
        raise ValueError('max_rounds must be an integer from 1 to 3.')
    if not isinstance(handlers, dict) or not set(handlers) <= {role for role, _ in ROLES}:
        raise ValueError('Unknown handler roles.')
    source = deepcopy(manifest)
    manifest_hash = canonical_hash(source)
    trace, feedback = [], []
    draft, draft_hash = None, None

    def finish(state, reason, round_number):
        outcome = {'workflow_version': 'agentic-controller-v1', 'state': state, 'reason': reason,
            'rounds_used': round_number, 'manifest_hash': manifest_hash,
            'draft': deepcopy(draft), 'draft_hash': draft_hash, 'trace': deepcopy(trace),
            'clinical_use_authorized': False}
        outcome['trace_hash'] = canonical_hash(trace)
        return outcome

    for attempt in range(1, max_rounds + 1):
        outputs, failures = {}, []
        draft, draft_hash = None, None
        for role, label in ROLES:
            # Do not pass a failed draft to patient communication or physician approval.
            if role == 'A17' and failures:
                break
            envelope = {'role': role, 'round': attempt, 'manifest': deepcopy(source),
                'manifest_hash': manifest_hash, 'prior_outputs': deepcopy(outputs),
                'revision_feedback': deepcopy(feedback), 'draft': deepcopy(draft), 'draft_hash': draft_hash}
            input_hash = canonical_hash(envelope)
            envelope['input_hash'] = input_hash
            adapter = handlers.get(role)
            started_at = _now()
            if adapter is None:
                trace.append({'role': role, 'round': attempt, 'decision': 'DEFER',
                    'input_hash': input_hash, 'code': 'HANDLER_NOT_CONFIGURED', 'started_at': started_at})
                return finish('HUMAN_REVIEW_REQUIRED', 'HANDLER_NOT_CONFIGURED:' + role, attempt)
            if (not isinstance(adapter, dict) or set(adapter) != {'version', 'run'}
                    or not isinstance(adapter['version'], str) or not adapter['version'].strip()
                    or not callable(adapter['run'])):
                trace.append({'role': role, 'round': attempt, 'decision': 'STOP',
                              'input_hash': input_hash, 'code': 'INVALID_HANDLER', 'started_at': started_at})
                return finish('BLOCKED', 'INVALID_HANDLER:' + role, attempt)
            try:
                raw = adapter['run'](deepcopy(envelope))
                result = deepcopy(raw)
                _validate_result(result, role, input_hash, draft_hash)
            except Exception:
                # Never copy exception text: provider errors may contain PHI or tokens.
                trace.append({'role': role, 'round': attempt, 'handler_version': adapter['version'],
                    'decision': 'STOP', 'input_hash': input_hash, 'code': 'HANDLER_FAILED_OR_INVALID_OUTPUT',
                    'started_at': started_at, 'finished_at': _now()})
                return finish('BLOCKED', 'HANDLER_FAILED_OR_INVALID_OUTPUT:' + role, attempt)
            trace.append({'role': role, 'label': label, 'round': attempt,
                'handler_version': adapter['version'], 'input_hash': input_hash,
                'output_hash': canonical_hash(result), 'reviewed_draft_hash': draft_hash,
                'decision': result['decision'], 'output': deepcopy(result),
                'started_at': started_at, 'finished_at': _now()})
            outputs[role] = result
            decision = result['decision']
            if decision in {'STOP', 'ESCALATE', 'DEFER'}:
                states = {'STOP': 'BLOCKED', 'ESCALATE': 'ESCALATED', 'DEFER': 'HUMAN_REVIEW_REQUIRED'}
                return finish(states[decision], decision + ':' + role, attempt)
            if decision == 'FAIL':
                if role not in REVIEWERS:
                    return finish('BLOCKED', 'NON_RETRYABLE_FAILURE:' + role, attempt)
                failures.append({'role': role, 'draft_hash': draft_hash, 'issues': result['issues'],
                                 'payload': deepcopy(result['payload'])})
            if role == 'A13' and decision == 'PASS':
                draft = deepcopy(result['payload']['draft'])
                draft_hash = canonical_hash(draft)
        if not failures:
            return finish('WORKFLOW_CHECKS_PASSED', 'NO_PUBLICATION_AUTHORITY', attempt)
        feedback = failures
    return finish('HUMAN_REVIEW_REQUIRED', 'MAX_ROUNDS_REACHED', max_rounds)
