"""Three evidence-only draft views. No generated clinical prose or recommendations."""
from copy import deepcopy

from .canonical_state import canonical_hash

EDITIONS = ('PHYSICIAN', 'PATIENT', 'MULTI_OMICS')
CLAIM_FIELDS = ('evidence_id', 'concept_id', 'value', 'unit', 'source_id',
                'source_type', 'source_timestamp', 'verification', 'version')


def _facts(manifest):
    canonical = manifest['canonical_state']
    if canonical.get('status') != 'VALIDATED_STRUCTURE':
        raise ValueError('Canonical evidence must pass structural validation.')
    active = set(canonical['active_evidence_ids'])
    facts = []
    for item in canonical['evidence_history']:
        if item['evidence_id'] in active:
            fact = {key: deepcopy(item[key]) for key in CLAIM_FIELDS}
            fact['claim_id'] = 'evidence:' + item['evidence_id']
            facts.append(fact)
    return sorted(facts, key=lambda item: item['claim_id'])


def compose_evidence_drafts(manifest):
    """Call only after backend preflight/authorization. This is NOT a final report.

    All editions preserve the same typed facts verbatim; patient-friendly medical
    explanation and omics recommendations require separate approved composers.
    """
    facts = _facts(manifest)
    digest = canonical_hash(manifest)
    packet = {'schema_version': 'evidence-draft-packet-v1', 'manifest_hash': digest,
              'state': 'DRAFT', 'clinical_use_authorized': False, 'editions': {}}
    for edition in EDITIONS:
        packet['editions'][edition] = {'edition': edition, 'manifest_hash': digest,
            'identity': deepcopy(manifest['identity']), 'facts': deepcopy(facts),
            'recommendations': [], 'clinical_interpretation': None,
            'notice_code': 'EVIDENCE_ONLY_UNAPPROVED_DRAFT'}
    packet['content_hash'] = canonical_hash(packet)
    return packet


def validate_evidence_drafts(packet, manifest):
    """Exact claim/source comparison; free-text assertions are not accepted here."""
    expected = compose_evidence_drafts(manifest)
    if not isinstance(packet, dict) or canonical_hash(packet) != canonical_hash(expected):
        raise ValueError('DRAFT_FACT_OR_PROVENANCE_MISMATCH')
    return {'status': 'EXACT_EVIDENCE_MATCH', 'content_hash': expected['content_hash'],
            'clinical_use_authorized': False}
