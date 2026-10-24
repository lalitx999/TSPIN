"""Non-clinical validation rules for the 30 September correction round (P0/P1)."""

OMICS_FIELDS = (
    "clinical_question", "current_uncertainty", "decision_that_depends_on_result",
    "will_change_management", "action_if_positive", "action_if_negative",
    "patient_burden", "cost_or_resource_burden", "turnaround_time",
    "goal_concordance", "clinical_priority", "physician_decision",
)

# ── P1-D: Test evidence tiering for clinical utility gate ──────────────────────
TEST_EVIDENCE_TIERS = {
    "STANDARD_CLINICAL": {
        "label": "Standard Clinical Lab",
        "description": "CBC, Chemistry panel, FBS, HbA1c, Lipid profile, LFT, RFT — universally available",
    },
    "CLINICALLY_ACTIONABLE_ADVANCED": {
        "label": "Clinically Actionable Advanced Test",
        "description": "Ferritin, TIBC, Transferrin Sat, Hb Typing, Anti-TPO, Tumor markers — targeted by clinical question",
    },
    "OPTIONAL_ADVANCED": {
        "label": "Optional Advanced Test",
        "description": "WES, Epigenomics, Proteomics, Metabolomics — resolution layer only, not prerequisite",
    },
    "RESEARCH_ONLY": {
        "label": "Research-Only",
        "description": "Experimental assays without validated clinical cutoffs — not for clinical decision-making",
    },
}


def clinical_utility(data):
    """Completeness never implies medical approval or permission to order a test."""
    utility = data.get("omics_utility", {})
    if not isinstance(utility, dict):
        utility = {}
    missing = [key for key in OMICS_FIELDS
               if not isinstance(utility.get(key), str) or not utility[key].strip()]
    if str(utility.get("will_change_management", "")).upper() == "LOW":
        state = "DEFER"
    elif missing:
        state = "INSUFFICIENT_DATA"
    else:
        state = "PENDING_PHYSICIAN_REVIEW"
    return {"status": state, "missing_requirements": missing,
            "assessment": {key: utility.get(key) for key in OMICS_FIELDS}}


def legacy_axis_state(axis_id, raw_score, hypothesis_axes,
                      clinical_inference_axes=None,
                      evidence_present_no_scoring_rule_axes=None):
    """
    Evidence classification for one axis — single source of truth for ALL three reports.

    P0-1: Scoring Rule Registry — severity_score only when approved rule exists.
    P0-3: HYPOTHESIS never scores (severity_score = None always).
    P0-5: Separates data_availability from score_status.
          Evidence PRESENT ≠ numeric score available.
    P0-7: CLINICAL_INFERENCE axes (A27, A33) — confounded, score = None until
          current markers confirm the clinical state.
    P0-8: A5/A27 from disease history alone = confounded.
    P0-13: score_derivation = DERIVED always for Axis scores.
    """
    if clinical_inference_axes is None:
        clinical_inference_axes = set()
    if evidence_present_no_scoring_rule_axes is None:
        evidence_present_no_scoring_rule_axes = {35, 37, 38}

    present = raw_score is not None
    hypothesis = present and axis_id in hypothesis_axes
    clinical_inference = present and axis_id in clinical_inference_axes
    no_scoring_rule = present and axis_id in evidence_present_no_scoring_rule_axes

    # ── Score gating: only non-gated axes with data get a numeric score ──────
    # HYPOTHESIS:          always None (P0-3 hard invariant)
    # CLINICAL_INFERENCE:  always None (confounded, P0-7/P0-8)
    # NO_SCORING_RULE:     always None (evidence present but no formula, P0-5)
    gated = hypothesis or clinical_inference or no_scoring_rule
    severity_score = None if gated else raw_score
    severity_band = None if gated else ("Subclinical" if (raw_score or 0) < 50 else "Pathological")

    # ── Evidence status (what kind of evidence do we have?) ──────────────────
    if hypothesis:
        evidence_status = "HYPOTHESIS"
    elif clinical_inference:
        evidence_status = "CLINICAL_INFERENCE"
    elif no_scoring_rule:
        evidence_status = "EVIDENCE_PRESENT"
    elif present:
        evidence_status = "ASSESSED"
    else:
        evidence_status = "NOT_AVAILABLE"

    # ── Assessment status ────────────────────────────────────────────────────
    if hypothesis:
        assessment_status = "AXIS_CANDIDATE"
    elif clinical_inference:
        assessment_status = "ASSESSED_CONFOUNDED"
    elif present:
        assessment_status = "ASSESSED_CONTEXTUALLY"
    else:
        assessment_status = "NOT_ASSESSED"

    # ── Score status (why is there or isn't there a numeric score?) ───────────
    if hypothesis:
        score_status = "NOT_SCORED_HYPOTHESIS"
    elif clinical_inference:
        score_status = "NOT_SCORED_CONFOUNDED"
    elif no_scoring_rule:
        score_status = "NO_APPROVED_SCORING_RULE"
    elif present:
        score_status = "SCORED"
    else:
        score_status = "NOT_SCORED_NO_DATA"

    return {
        "data_availability": "PRESENT" if present else "NOT_AVAILABLE",
        "evidence_status": evidence_status,
        "assessment_status": assessment_status,
        "score_status": score_status,
        "severity_score": severity_score,
        "severity_band": severity_band,
        "eligible_for_nss": present and not gated,
        "eligible_for_priority": present and not gated,
        "eligible_for_module_match": present and not hypothesis,
        "score_derivation": "DERIVED",
        "scoring_rule_id": None,
        "scoring_rule_version": None,
        "axis_role": "CANDIDATE" if (hypothesis or clinical_inference) else ("ASSESSED" if present else "NOT_ASSESSED"),
        "marker_relation_type": "NON_SCORING" if gated else ("DIRECT_SCORING" if present else "NON_SCORING"),
        "source_type_note": "LEGACY_ESTIMATE_UNVERIFIED",
    }
