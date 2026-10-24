"""Restricted arithmetic interpreter. No eval, LLM, defaults, or medical constants."""
from decimal import Decimal, InvalidOperation, localcontext


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError('Expected a finite decimal value.')
    text = str(value)
    if len(text) > 64:
        raise ValueError('Decimal value is too long.')
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError('Invalid decimal value.') from exc
    if not result.is_finite() or abs(result.adjusted()) > 100 or len(result.as_tuple().digits) > 28:
        raise ValueError('Decimal is outside supported precision/range.')
    return result


def validate_rule(rule):
    required = {'operation', 'inputs', 'offset', 'minimum', 'maximum', 'bands', 'missing_behavior'}
    if not isinstance(rule, dict) or set(rule) != required:
        raise ValueError('Invalid scoring rule schema.')
    if rule['operation'] != 'WEIGHTED_SUM' or rule['missing_behavior'] != 'NOT_ASSESSED':
        raise ValueError('Unsupported operation or missing-data policy.')
    inputs = rule['inputs']
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= 100:
        raise ValueError('Rule requires 1–100 input definitions.')
    ids = set()
    for item in inputs:
        if not isinstance(item, dict) or set(item) != {'concept_id', 'unit', 'weight'}:
            raise ValueError('Invalid rule input.')
        key = item['concept_id']
        if not isinstance(key, str) or not key.strip() or key in ids or not isinstance(item['unit'], str):
            raise ValueError('Input concepts must be unique and have explicit units.')
        ids.add(key)
        number(item['weight'])
    number(rule['offset'])
    lower, upper = number(rule['minimum']), number(rule['maximum'])
    if lower >= upper:
        raise ValueError('Invalid score range.')
    bands = rule['bands']
    if not isinstance(bands, list) or not 1 <= len(bands) <= 100:
        raise ValueError('Bands are required.')
    previous, labels = None, set()
    for band in bands:
        if not isinstance(band, dict) or set(band) != {'lower', 'label'}:
            raise ValueError('Invalid band schema.')
        boundary = number(band['lower'])
        if boundary < lower or boundary > upper or (previous is None and boundary != lower) or (
            previous is not None and boundary <= previous
        ):
            raise ValueError('Bands must start at minimum and increase strictly.')
        label = band['label']
        if not isinstance(label, str) or not label.strip() or label in labels:
            raise ValueError('Band labels must be non-empty and unique.')
        previous = boundary
        labels.add(label)


def evaluate_rule(rule, evidence):
    """Pure calculation only; caller must prove approval and evidence ownership first.

    evidence is the exact selected list, not a bag of candidate observations.
    More than one observation of a required concept is ambiguous, never averaged.
    """
    validate_rule(rule)
    if not isinstance(evidence, list) or any(not isinstance(item, dict) for item in evidence):
        raise ValueError('Evidence must be a list of objects.')
    contributions, problems = [], []
    with localcontext() as context:
        context.prec = 1024
        total = number(rule['offset'])
        for definition in rule['inputs']:
            key = definition['concept_id']
            matches = [item for item in evidence if item.get('concept_id') == key]
            if len(matches) != 1:
                problems.append({'concept_id': key, 'code': 'MISSING_INPUT' if not matches else 'AMBIGUOUS_INPUT'})
                continue
            item = matches[0]
            if item.get('verification') != 'VERIFIED' or item.get('source_type') not in {
                'LAB_MEASURED', 'DEVICE_MEASURED', 'PHYSICIAN_OBSERVED'
            }:
                problems.append({'concept_id': key, 'code': 'UNSUPPORTED_EVIDENCE'})
                continue
            if item.get('unit') != definition['unit']:
                problems.append({'concept_id': key, 'code': 'UNIT_MISMATCH'})
                continue
            if not all(isinstance(item.get(k), str) and item[k].strip() for k in ('evidence_id', 'source_id')):
                problems.append({'concept_id': key, 'code': 'MISSING_PROVENANCE'})
                continue
            try:
                value, weight = number(item.get('value')), number(definition['weight'])
            except ValueError:
                problems.append({'concept_id': key, 'code': 'INVALID_NUMERIC_INPUT'})
                continue
            contribution = value * weight
            total += contribution
            contributions.append({'concept_id': key, 'evidence_id': item['evidence_id'],
                'source_id': item['source_id'], 'value': str(value), 'unit': item['unit'],
                'weight': str(weight), 'contribution': str(contribution)})
        if problems:
            return {'status': 'NOT_ASSESSED', 'score': None, 'band': None,
                    'issues': problems, 'contributions': contributions}
        if not number(rule['minimum']) <= total <= number(rule['maximum']):
            return {'status': 'BLOCKED', 'score': None, 'band': None,
                    'issues': [{'code': 'SCORE_OUT_OF_RANGE'}], 'contributions': contributions}
        band = next(b['label'] for b in reversed(rule['bands']) if total >= number(b['lower']))
        return {'status': 'CALCULATED', 'score': str(total), 'band': band,
                'issues': [], 'contributions': contributions}
