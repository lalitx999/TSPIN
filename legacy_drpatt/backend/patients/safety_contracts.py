"""Completeness and recorded-assessment gates, not a medical diagnosis engine."""
from datetime import datetime, timezone

DOMAINS = frozenset({'emergency', 'allergy', 'pregnancy', 'renal', 'hepatic',
                    'bleeding', 'interactions', 'critical_labs', 'referral', 'consent'})


def validate_safety_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {'requirements', 'soc_prerequisites'}:
        raise ValueError('Safety policy requires requirements and soc_prerequisites.')
    requirements, prerequisites = policy['requirements'], policy['soc_prerequisites']
    if not isinstance(requirements, list) or not isinstance(prerequisites, list):
        raise ValueError('Safety requirements must be lists.')
    domains, concepts = set(), set()
    for requirement in requirements:
        if not isinstance(requirement, dict) or set(requirement) != {
            'domain', 'concept_id', 'max_age_hours', 'allow_not_applicable'
        }:
            raise ValueError('Invalid safety requirement.')
        domain = requirement['domain']
        if not isinstance(domain, str) or domain not in DOMAINS or domain in domains:
            raise ValueError('Safety domains must be known and unique.')
        domains.add(domain)
        if type(requirement['allow_not_applicable']) is not bool:
            raise ValueError('allow_not_applicable must be boolean.')
        _validate_requirement(requirement, concepts)
    if domains != DOMAINS:
        raise ValueError('Safety policy must cover every required domain.')
    # An empty list is a declared policy scope, not proof that no SOC work is needed.
    for requirement in prerequisites:
        if not isinstance(requirement, dict) or set(requirement) != {'concept_id', 'max_age_hours'}:
            raise ValueError('Invalid standard-of-care prerequisite.')
        _validate_requirement(requirement, concepts)


def _validate_requirement(requirement, concepts):
    concept = requirement['concept_id']
    if not isinstance(concept, str) or not concept.strip() or concept in concepts:
        raise ValueError('Requirement concepts must be non-empty and unique.')
    concepts.add(concept)
    hours = requirement['max_age_hours']
    if type(hours) is not int or not 1 <= hours <= 87600:
        raise ValueError('A bounded, positive freshness window is required.')


def _observed_at(record):
    value = record.get('source_timestamp')
    if not isinstance(value, str):
        raise ValueError('Missing timestamp.')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if instant.utcoffset() is None:
        raise ValueError('Timezone required.')
    return instant.astimezone(timezone.utc)


def _latest(requirement, evidence, as_of):
    candidates, malformed = [], False
    for item in evidence:
        if item.get('concept_id') != requirement['concept_id']:
            continue
        try:
            instant = _observed_at(item)
        except (ValueError, TypeError, OverflowError):
            malformed = True
            continue
        candidates.append((instant, item))
    if malformed:
        return [], 'INVALID_ASSESSMENT_TIMESTAMP'
    if not candidates:
        return [], 'MISSING_ASSESSMENT'
    latest = max(instant for instant, _ in candidates)
    selected = [item for instant, item in candidates if instant == latest]
    elapsed = (as_of - latest).total_seconds()
    if elapsed < 0:
        return selected, 'FUTURE_ASSESSMENT'
    if elapsed > requirement['max_age_hours'] * 3600:
        return selected, 'STALE_ASSESSMENT'
    if len(selected) != 1:
        return selected, 'AMBIGUOUS_ASSESSMENT'
    return selected, None


def _verified(item):
    return item.get('verification') == 'VERIFIED' and all(
        isinstance(item.get(key), str) and item[key].strip()
        for key in ('evidence_id', 'source_id', 'verified_by'))


def evaluate_safety(policy, evidence, *, as_of, interaction_source_status='UNAVAILABLE',
                    preserve_unresolved_alerts=True):
    """Use only stored, verified clinician assessments to mark a domain assessed.

    No lab thresholds are inferred here. Caller supplies trusted active evidence,
    approved policy and server time; integration availability is not client input.
    """
    validate_safety_policy(policy)
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError('An aware server assessment timestamp is required.')
    if not isinstance(evidence, list) or any(not isinstance(item, dict) for item in evidence):
        raise ValueError('Evidence must be a list of objects.')
    as_of = as_of.astimezone(timezone.utc)
    findings, missing, flags = [], [], []
    for requirement in policy['requirements']:
        selected, problem = _latest(requirement, evidence, as_of)
        item = selected[0] if len(selected) == 1 else None
        if problem is None and (not _verified(item) or item.get('source_type') != 'PHYSICIAN_OBSERVED'):
            problem = 'REQUIRES_VERIFIED_CLINICIAN_ASSESSMENT'
        value = item.get('value') if item else None
        if problem is None and value not in ('CLEAR', 'ALERT', 'EMERGENCY', 'NOT_APPLICABLE'):
            problem = 'NOT_ASSESSED'
        if problem is None and value == 'NOT_APPLICABLE' and not requirement['allow_not_applicable']:
            problem = 'NOT_APPLICABLE_NOT_ALLOWED'
        if requirement['domain'] == 'interactions' and interaction_source_status != 'AVAILABLE':
            problem = 'INTERACTION_SOURCE_UNAVAILABLE'
        # An unusable new assessment must not erase an existing alert. The legacy
        # switch is only for reproducing stored v1 snapshots, never live clearance.
        alert_candidates = ([row for row in evidence
                             if row.get('concept_id') == requirement['concept_id']]
                            if problem and preserve_unresolved_alerts else selected)
        for alert in alert_candidates:
            if alert.get('value') in ('ALERT', 'EMERGENCY'):
                flags.append({'domain': requirement['domain'], 'level': alert['value'],
                              'evidence_id': alert.get('evidence_id'), 'requires_clinician_review': True})
        if problem:
            missing.append({'domain': requirement['domain'], 'code': problem})
        findings.append({'domain': requirement['domain'], 'status': 'NOT_ASSESSED' if problem else value,
                         'evidence_ids': [row.get('evidence_id') for row in selected]})
    soc_missing = []
    for requirement in policy['soc_prerequisites']:
        selected, problem = _latest(requirement, evidence, as_of)
        item = selected[0] if len(selected) == 1 else None
        if problem is None and (not _verified(item) or item.get('value') in (None, '', 'NOT_ASSESSED', 'NOT_AVAILABLE')
                or item.get('source_type') not in {'LAB_MEASURED', 'DEVICE_MEASURED', 'PHYSICIAN_OBSERVED', 'IMAGING_REPORTED'}):
            problem = 'SOC_PREREQUISITE_NOT_VERIFIED'
        if problem:
            soc_missing.append({'concept_id': requirement['concept_id'], 'code': problem})
    completed = len(DOMAINS) - len(missing)
    levels = {flag['level'] for flag in flags}
    if 'EMERGENCY' in levels:
        state, decision = 'EMERGENCY', 'ESCALATE'
    elif 'ALERT' in levels:
        state, decision = 'ALERT', 'ESCALATE'
    elif missing or soc_missing:
        state, decision = ('PARTIAL' if completed else 'INCOMPLETE'), 'DEFER'
    else:
        state, decision = 'NO_RED_FLAG_IDENTIFIED_IN_AVAILABLE_DATA', 'DEFER'
    return {'safety_state': state, 'decision': decision, 'coverage': {'assessed': completed, 'required': len(DOMAINS)},
            'findings': findings, 'missing_requirements': missing, 'soc_missing': soc_missing, 'alerts': flags,
            'interaction_source_status': interaction_source_status, 'assessed_at': as_of.isoformat(),
            'required_action': 'URGENT_CLINICIAN_REVIEW' if flags else 'CLINICIAN_REVIEW',
            'clinical_use_authorized': False}
