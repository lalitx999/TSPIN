"""Synthetic arithmetic tests. No clinical thresholds or real patient records."""
from copy import deepcopy
from unittest import TestCase

from .deterministic_scoring import evaluate_rule, validate_rule


def synthetic_rule():
    return {'operation': 'WEIGHTED_SUM', 'missing_behavior': 'NOT_ASSESSED',
        'inputs': [{'concept_id': 'C1', 'unit': 'test-unit', 'weight': '2'}],
        'offset': '1', 'minimum': '0', 'maximum': '100',
        'bands': [{'lower': '0', 'label': 'TEST_LOW'}, {'lower': '50', 'label': 'TEST_HIGH'}]}


def synthetic_evidence(**changes):
    record = {'concept_id': 'C1', 'unit': 'test-unit', 'value': '24.5',
        'verification': 'VERIFIED', 'source_type': 'LAB_MEASURED',
        'source_id': 'test-source', 'evidence_id': 'test-evidence'}
    record.update(changes)
    return record


class DeterministicScoringTests(TestCase):
    def test_exact_score_and_band_boundary(self):
        result = evaluate_rule(synthetic_rule(), [synthetic_evidence()])
        self.assertEqual(result['score'], '50.0')
        self.assertEqual(result['band'], 'TEST_HIGH')
        self.assertEqual(result['contributions'][0]['weight'], '2')

    def test_missing_is_not_zero(self):
        result = evaluate_rule(synthetic_rule(), [])
        self.assertEqual(result['status'], 'NOT_ASSESSED')
        self.assertIsNone(result['score'])

    def test_numeric_zero_is_valid(self):
        result = evaluate_rule(synthetic_rule(), [synthetic_evidence(value=0)])
        self.assertEqual(result['score'], '1')

    def test_unverified_or_hypothesis_not_scored(self):
        for changes in ({'verification': 'UNVERIFIED'}, {'source_type': 'HYPOTHESIS'},
                        {'source_type': 'NOT_ASSESSED'}, {'source_type': 'DERIVED'}):
            self.assertIsNone(evaluate_rule(synthetic_rule(), [synthetic_evidence(**changes)])['score'])

    def test_wrong_unit_not_converted(self):
        self.assertIsNone(evaluate_rule(synthetic_rule(), [synthetic_evidence(unit='other')])['score'])

    def test_duplicate_observations_not_averaged(self):
        result = evaluate_rule(synthetic_rule(), [synthetic_evidence(), synthetic_evidence(evidence_id='second')])
        self.assertEqual(result['issues'][0]['code'], 'AMBIGUOUS_INPUT')

    def test_nonfinite_boolean_and_missing_values_blocked(self):
        for value in ('NaN', 'Infinity', True, None, 'text', '1e9999'):
            self.assertIsNone(evaluate_rule(synthetic_rule(), [synthetic_evidence(value=value)])['score'])

    def test_out_of_range_not_clamped(self):
        result = evaluate_rule(synthetic_rule(), [synthetic_evidence(value=100)])
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIsNone(result['score'])

    def test_no_python_expression_execution(self):
        rule = synthetic_rule()
        rule['operation'] = '__import__("os")'
        with self.assertRaises(ValueError):
            validate_rule(rule)

    def test_invalid_or_duplicate_band_bounds_rejected(self):
        rule = synthetic_rule()
        rule['bands'][1]['lower'] = '0'
        with self.assertRaises(ValueError):
            validate_rule(rule)

    def test_no_input_mutation(self):
        rule, evidence = synthetic_rule(), [synthetic_evidence()]
        before = deepcopy((rule, evidence))
        evaluate_rule(rule, evidence)
        self.assertEqual((rule, evidence), before)
