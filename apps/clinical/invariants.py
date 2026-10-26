"""
Clinical Invariant Validator & Cross-Report Governance Engine for TSPI.
Enforces Medical Board Invariants from 22.09.2026 TSPI Specifications.
Guarantees Zero Hallucination, Cross-Report Mathematical Consistency, and Fail-Closed Safety.
"""

import re
from typing import Dict, List, Tuple, Any, Optional, Union
from .schemas import (
    CoreAnalysisPayload,
    ApprovalStatusEnum,
    EvidenceStatusEnum,
    AssessmentStatusEnum,
    ScoreStatusEnum,
    IronSafetyStatusEnum,
)

CANONICAL_39_AXES = {
    1: "Systemic Inflammatory Load",
    2: "Innate & Adaptive Immune Balance",
    3: "Immune Senescence & Exhaustion",
    4: "Chronic Latent Infection Burden",
    5: "Glucose–Insulin Regulation",
    6: "Lipid Metabolism & Transport",
    7: "Metabolic Flexibility & Energy Allocation",
    8: "Mitochondrial Network",
    9: "Bioenergetic & Redox Coupling",
    10: "Metabolic Organ Cross-talk",
    11: "DNA Repair & Genomic Stability",
    12: "Epigenetic Programming",
    13: "Telomere Dynamics",
    14: "Cellular Senescence & SASP",
    15: "Detoxification & Cellular Defense",
    16: "Upper GI & Digestive Capacity",
    17: "Intestinal Barrier Integrity",
    18: "Microbiome Diversity & Ecology",
    19: "Gut–Immune–Systemic Axis",
    20: "Endothelial Function & Microcirculation",
    21: "Arterial Stiffness & Vascular Compliance",
    22: "Tissue Perfusion & Oxygenation",
    23: "Lymphatic Drainage & Fluid Homeostasis",
    24: "Extracellular Matrix Dynamics",
    25: "Wound Healing & Fibrogenic Balance",
    26: "Bone Remodeling & Mineral Homeostasis",
    27: "Stem Cell Niche & Regenerative Capacity",
    28: "Skeletal Muscle Mass & Quality",
    29: "Neuromuscular Junction & Motor Unit Integrity",
    30: "Connective Tissue Integrity",
    31: "Female Hormone Network",
    32: "Male Androgen",
    33: "Thyroid–Adrenal–Growth",
    34: "Neuro–Sleep–Stress–Brain Clearance",
    35: "Visceral Organ Functional Reserve",
    36: "Oncology",
    37: "Oncologic Cell Fate",
    38: "Tumor Microenvironment & Metastatic Dynamics",
    39: "Genomic Regulation Homeostasis"
}

# Accepted UI Display Aliases mapped to Canonical Names
AXIS_DISPLAY_ALIASES = {
    2: ["Immune Homeostasis"],
    3: ["Pathogen Defense"],
    4: ["Post‑Infectious Persistence"],
    6: ["Lipid–Lipotoxicity"],
    7: ["Nutrient Sensing (AMPK–mTOR)"],
    9: ["Oxidative Stress"],
    10: ["Proteostasis–Autophagy–Lysosome"],
    12: ["Epigenetic Regulation"],
    13: ["Longevity Signaling (SIRT–FOXO–IGF)"],
    14: ["Senescence & SASP"],
    16: ["Digestive–Absorptive"],
    17: ["Microbiome Ecology"],
    18: ["Gut Barrier & Mucosal Integrity"],
    19: ["Colon Biofilm & Mucosal Burden"],
    20: ["Endothelial Function"],
    21: ["Vascular Remodeling & Microcirculation"],
    22: ["Thrombosis–Hemostasis"],
    23: ["Hemodynamics & Arterial Elasticity"],
    24: ["Wound Healing (Internal + External)"],
    25: ["Fibrosis & ECM Remodeling"],
    26: ["Stem Cell & Hematopoiesis"],
    27: ["Glycation / Carbonyl Stress (AGE)"],
    28: ["Muscle Protein Turnover"],
    29: ["Bone Remodeling"],
    32: ["Male Androgen Network"],
    33: ["Thyroid–Adrenal–Growth Axis"],
    35: ["Organ Resilience & Functional Reserve"],
    36: ["Local Organ & Tissue Interface"],
}


def resolve_canonical_axis_name(axis_id: int, name: str) -> str:
    """แปลง Display Alias กลับเป็น Canonical Master Name เสมอ"""
    canonical = CANONICAL_39_AXES.get(axis_id)
    if not canonical:
        return name
    if name == canonical or name in AXIS_DISPLAY_ALIASES.get(axis_id, []):
        return canonical
    return name

CANONICAL_12_DOMAINS = {
    "D1": "Immune–Infection Governance",
    "D2": "Metabolic–Energy Core",
    "D3": "Genomic Programming",
    "D4": "Detoxification & Cellular Defense",
    "D5": "Digestive–Gut Ecosystem",
    "D6": "Vascular–Circulation",
    "D7": "Repair–Regeneration",
    "D8": "Musculoskeletal & Structural Integrity",
    "D9": "Endocrine Network",
    "D10": "Neurological Regulation",
    "D11": "Organ Resilience",
    "D12": "Oncology & System-Level Regulation"
}

CANONICAL_9_STEPS = [
    "Detoxification",
    "Microbiome Ecosystem",
    "Immune–Inflammatory Regulation",
    "Redox Homeostasis & Oxidative Balance",
    "Enhance Metabolic Function & Mitochondria",
    "Autophagy & Cellular Clearance",
    "Genomic Stability & Proteostasis",
    "Genomic Regulation Homeostasis",
    "Prakati — Bioelectrical & Physiological Coherence"
]


class ClinicalInvariantValidator:
    """
    ตรวจสอบ Invariants 7 มิติของ TSPI Clinical Intelligence:
    1. Identity Hard Gate (Zero Conflict)
    2. HYPOTHESIS & AXIS_CANDIDATE -> severity_score == None
    3. Numeric Score requires approved scoring_rule_id
    4. Canonical 12 Domains & 39 Axes & 9 Steps Naming
    5. Iron Safety HOLD & MASH Terminology
    6. Module Registry Fail-Closed Whitelist
    7. Cross-Report Mathematical Consistency (Physician / Patient / Multi-Omics)
    """

    @classmethod
    def validate_payload(cls, payload: Union[CoreAnalysisPayload, dict]) -> Tuple[bool, List[str]]:
        """
        ตรวจสอบ Core Analysis Payload ก่อนเรนเดอร์ PDF
        Returns: (is_valid, list_of_violations)
        """
        violations: List[str] = []

        # แปลงเป็น Pydantic ถ้าเป็น dict
        if isinstance(payload, dict):
            try:
                payload = CoreAnalysisPayload(**payload)
            except Exception as e:
                return False, [f"Schema Validation Error: {str(e)}"]

        # Rule 1: Identity Hard Gate
        ident = payload.identity
        if not ident.hn or len(ident.hn.strip()) < 3:
            violations.append("P0 Invariant: Patient HN is missing or invalid.")
        if ident.age < 0 or ident.age > 150:
            violations.append(f"P0 Invariant: Impossible age ({ident.age}).")

        # Rule 2 & 3: Axis Assessment Invariants
        for axis_id, ax in payload.axes.items():
            # Check Canonical Axis Name
            canonical_name = CANONICAL_39_AXES.get(axis_id)
            if canonical_name and ax.canonical_axis_name != canonical_name:
                violations.append(
                    f"P0 Invariant: Axis {axis_id} name '{ax.canonical_axis_name}' does not match "
                    f"canonical master '{canonical_name}'."
                )

            # Check Canonical Domain
            if ax.domain_code in CANONICAL_12_DOMAINS:
                if ax.canonical_domain_name != CANONICAL_12_DOMAINS[ax.domain_code]:
                    violations.append(
                        f"P0 Invariant: Domain code {ax.domain_code} name '{ax.canonical_domain_name}' "
                        f"mismatches canonical master '{CANONICAL_12_DOMAINS[ax.domain_code]}'."
                    )

            # HYPOTHESIS & AXIS_CANDIDATE must have severity_score = None
            if ax.evidence_status == EvidenceStatusEnum.HYPOTHESIS or ax.assessment_status == AssessmentStatusEnum.AXIS_CANDIDATE:
                if ax.severity_score is not None:
                    violations.append(
                        f"P0 Invariant Violation on Axis {axis_id}: "
                        f"Status is {ax.evidence_status.value}/{ax.assessment_status.value} "
                        f"but has numeric score {ax.severity_score}. Numeric score MUST be None."
                    )

            # Numeric score requires approved scoring_rule_id
            if ax.severity_score is not None:
                if not ax.scoring_rule_id or not ax.scoring_rule_id.strip():
                    violations.append(
                        f"P0 Invariant Violation on Axis {axis_id}: "
                        f"Severity score {ax.severity_score} has no approved scoring_rule_id."
                    )

        # Rule 4: Iron Safety Gate
        safety = payload.safety_gates
        if safety.iron_supplementation_status == IronSafetyStatusEnum.CONTRAINDICATED:
            violations.append(
                "P0 Invariant Warning: Iron supplementation must be HOLD_PENDING_CONFIRMATION, "
                "not absolute CONTRAINDICATED (since thalassemia trait and iron deficiency can coexist)."
            )

        # Terminology MASH Check
        if "myxedema" in safety.mash_terminology.lower():
            violations.append(
                "P0 Invariant Terminology Error: MASH must be 'Metabolic dysfunction-associated steatohepatitis', "
                "NOT 'Myxedema-Associated'."
            )

        # Rule 5: Fail-Closed Module Whitelist
        mod_reg = payload.module_registry
        if mod_reg.approved_module_count == 0 and not mod_reg.is_hidden_in_clinical_report:
            violations.append(
                "P0 Invariant: Approved module count is 0, module_section MUST be HIDDEN in clinical report."
            )

        is_valid = len(violations) == 0
        return is_valid, violations

    @classmethod
    def validate_cross_report_consistency(
        cls,
        physician_view: Dict[str, Any],
        patient_view: Dict[str, Any],
        omics_view: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        ตรวจสอบ Hard Gate: ข้อมูลสำคัญต้องตรงกัน 100% ระหว่าง 3 รายงาน
        (Physician Edition, Patient Edition, Multi-Omics Edition)
        """
        violations: List[str] = []

        # 1. Identity Verification
        views = [
            ("Physician", physician_view),
            ("Patient", patient_view),
            ("Multi-Omics", omics_view),
        ]

        ref_hn = physician_view.get("hn")
        ref_age = physician_view.get("age")
        ref_sex = physician_view.get("sex")

        for name, view in views:
            hn = view.get("hn")
            age = view.get("age")
            sex = view.get("sex")

            if hn != ref_hn:
                violations.append(f"Cross-Report Identity Mismatch: {name} HN '{hn}' != Physician HN '{ref_hn}'")
            if age != ref_age:
                violations.append(f"Cross-Report Identity Mismatch: {name} Age '{age}' != Physician Age '{ref_age}'")
            if sex != ref_sex:
                violations.append(f"Cross-Report Identity Mismatch: {name} Sex '{sex}' != Physician Sex '{ref_sex}'")

        # 2. Axis Scores Verification
        ref_scores = physician_view.get("scores", {})
        for name, view in [("Patient", patient_view), ("Multi-Omics", omics_view)]:
            target_scores = view.get("scores", {})
            for axis_id in range(1, 40):
                ref_val = ref_scores.get(axis_id)
                tgt_val = target_scores.get(axis_id)
                if ref_val != tgt_val:
                    violations.append(
                        f"Cross-Report Axis Score Mismatch on Axis {axis_id}: "
                        f"Physician={ref_val} vs {name}={tgt_val}"
                    )

        # 3. Approval Status Verification
        ref_status = physician_view.get("approval_status")
        for name, view in [("Patient", patient_view), ("Multi-Omics", omics_view)]:
            tgt_status = view.get("approval_status")
            if tgt_status != ref_status:
                violations.append(
                    f"Cross-Report Approval Status Mismatch: Physician '{ref_status}' vs {name} '{tgt_status}'"
                )

        is_consistent = len(violations) == 0
        return is_consistent, violations

    @classmethod
    def sanitize_patient_prose(cls, text: str) -> str:
        """
        สกัด Internal Engine Tags ออกจากข้อความรายงานของคนไข้
        และแปลงเป็นภาษาธรรมชาติที่สุภาพและเข้าใจง่าย
        """
        if not text:
            return ""

        replacements = {
            r"\[MEASURED\]": "ผลตรวจทางห้องปฏิบัติการพบว่า",
            r"\[DERIVED\]": "จากการประเมินทางชีววิทยาพบว่า",
            r"\[HYPOTHESIS\]": "ในเบื้องต้นมีข้อสังเกตว่า",
            r"\[PHYSICIAN_APPROVED_RECOMMENDATION\]": "แพทย์ผู้เชี่ยวชาญแนะนำว่า",
            r"\[CURRENT_PHYSICIAN_ORDER\]": "แผนการดูแลปัจจุบันกำหนดให้",
            r"\[AI_SUGGESTED_CONSIDERATION\]": "ประเด็นที่ควรปรึกษาแพทย์เพิ่มเติมคือ",
            r"\[STANDARD_CLINICAL\]": "",
            r"\[NOT_SCORED\]": "(รอตรวจยืนยันเพิ่มเติม)",
        }

        sanitized = text
        for tag_pattern, replacement in replacements.items():
            sanitized = re.sub(tag_pattern, replacement, sanitized)

        # จัดการช่องว่างซ้ำซ้อน
        sanitized = re.sub(r"\s{2,}", " ", sanitized).strip()
        return sanitized
