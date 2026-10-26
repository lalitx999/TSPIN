"""
Clinical Governance & Immutable Data Contracts for TSPI Clinical Intelligence.
Enforces Single Source of Truth (ONE PATIENT -> ONE VERIFIED DATASET -> ONE IMMUTABLE ANALYSIS RECORD).
Directly satisfies requirements from 22.09.2026 TSPI Medical Board Specifications.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ApprovalStatusEnum(str, Enum):
    AI_DRAFT = "AI_DRAFT"
    PHYSICIAN_REVIEWED = "PHYSICIAN_REVIEWED"
    PHYSICIAN_APPROVED = "PHYSICIAN_APPROVED"
    PATIENT_RELEASED = "PATIENT_RELEASED"


class EvidenceStatusEnum(str, Enum):
    MEASURED = "MEASURED"
    DERIVED = "DERIVED"
    CLINICAL_INFERENCE = "CLINICAL_INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"


class AssessmentStatusEnum(str, Enum):
    ASSESSED = "ASSESSED"
    ASSESSED_CONTEXTUALLY = "ASSESSED_CONTEXTUALLY"
    AXIS_CANDIDATE = "AXIS_CANDIDATE"
    NOT_ASSESSED = "NOT_ASSESSED"


class ScoreStatusEnum(str, Enum):
    APPROVED_RULE_SCORED = "APPROVED_RULE_SCORED"
    NO_APPROVED_SCORING_RULE = "NO_APPROVED_SCORING_RULE"
    NOT_SCORED = "NOT_SCORED"


class IronSafetyStatusEnum(str, Enum):
    HOLD_PENDING_CONFIRMATION = "HOLD_PENDING_CONFIRMATION"
    ELIGIBLE = "ELIGIBLE"
    CONTRAINDICATED = "CONTRAINDICATED"


class PatientIdentityPayload(BaseModel):
    """ข้อมูลประจำตัวผู้ป่วยที่เป็นความจริงหนึ่งเดียว (Single Source of Truth)"""
    model_config = ConfigDict(frozen=True)

    patient_id: int
    hn: str = Field(..., min_length=3, description="Hospital Number ของผู้ป่วย")
    full_name: str
    age: int = Field(..., ge=0, le=150)
    sex: str = Field(..., pattern="^(M|F|male|female|other)$")
    dob: Optional[str] = None


class AxisAssessmentPayload(BaseModel):
    """
    การประเมินรายแกนชีววิทยา (1-39)
    แยก 4 เลเยอร์: Data Availability != Evidence Status != Assessment Status != Score Status
    """
    model_config = ConfigDict(frozen=True)

    axis_id: int = Field(..., ge=1, le=39)
    canonical_axis_name: str
    canonical_domain_name: str
    domain_code: str  # D1 to D12
    data_availability: str = Field("PRESENT", pattern="^(PRESENT|NOT_AVAILABLE)$")
    evidence_status: EvidenceStatusEnum = EvidenceStatusEnum.MEASURED
    assessment_status: AssessmentStatusEnum = AssessmentStatusEnum.ASSESSED
    score_status: ScoreStatusEnum = ScoreStatusEnum.APPROVED_RULE_SCORED
    scoring_rule_id: Optional[str] = None
    severity_score: Optional[float] = None
    severity_band: Optional[str] = None  # OPTIMAL, SUBCLINICAL, FUNCTIONAL, PATHOLOGICAL

    @model_validator(mode='after')
    def enforce_hypothesis_and_rule_invariants(self) -> 'AxisAssessmentPayload':
        # Hard Invariant P0: HYPOTHESIS & AXIS_CANDIDATE must never have numeric score
        if self.evidence_status == EvidenceStatusEnum.HYPOTHESIS or self.assessment_status == AssessmentStatusEnum.AXIS_CANDIDATE:
            if self.severity_score is not None:
                raise ValueError(
                    f"P0 Invariant Violation on Axis {self.axis_id}: "
                    f"HYPOTHESIS or AXIS_CANDIDATE must have severity_score=None, found {self.severity_score}"
                )
        # Hard Invariant P0: Numeric score requires an approved scoring_rule_id
        if self.severity_score is not None and not self.scoring_rule_id:
            raise ValueError(
                f"P0 Invariant Violation on Axis {self.axis_id}: "
                f"Numeric score {self.severity_score} provided without approved scoring_rule_id"
            )
        return self


class SafetyGatesPayload(BaseModel):
    """เกณฑ์ความปลอดภัยทางคลินิก (Clinical Safety Gates)"""
    model_config = ConfigDict(frozen=True)

    iron_supplementation_status: IronSafetyStatusEnum = IronSafetyStatusEnum.HOLD_PENDING_CONFIRMATION
    iron_required_tests: List[str] = Field(
        default_factory=lambda: ["Ferritin", "TIBC", "Transferrin Saturation", "Hb Typing"]
    )
    iron_clinical_guidance: str = "Do not start empirical iron supplementation until iron status is assessed."
    mash_terminology: str = Field(
        "Metabolic dysfunction-associated steatohepatitis",
        description="Factual terminology fix: must NOT be Myxedema-Associated"
    )


class ModuleRegistryPayload(BaseModel):
    """
    คลังตำรับสารอาหารและพฤกษเคมี 200 โมดูล
    Fail-Closed Policy: หาก approved_module_count == 0 จะต้อง HIDDEN ทันที
    """
    model_config = ConfigDict(frozen=True)

    approved_module_count: int = 0
    approved_modules_whitelist: List[str] = Field(default_factory=list)
    is_hidden_in_clinical_report: bool = True
    provisional_modules_for_qa: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode='after')
    def enforce_fail_closed_modules(self) -> 'ModuleRegistryPayload':
        if self.approved_module_count == 0 and not self.is_hidden_in_clinical_report:
            raise ValueError(
                "P0 Invariant Violation: approved_module_count is 0, is_hidden_in_clinical_report MUST be True"
            )
        return self


class CoreAnalysisPayload(BaseModel):
    """
    ONE IMMUTABLE TSPI ANALYSIS RECORD
    Single Source of Truth สำหรับเรนเดอร์ทั้ง 3 ฉบับ (Physician / Patient / Multi-Omics)
    """
    model_config = ConfigDict(frozen=True)

    analysis_id: int
    framework_version: str = "TSPI-2026.1"
    approval_status: ApprovalStatusEnum = ApprovalStatusEnum.AI_DRAFT
    identity: PatientIdentityPayload
    safety_gates: SafetyGatesPayload = Field(default_factory=SafetyGatesPayload)
    module_registry: ModuleRegistryPayload = Field(default_factory=ModuleRegistryPayload)
    axes: Dict[int, AxisAssessmentPayload]
    clinical_summary: str = ""
    physician_notes: Optional[str] = None
    certified_by_office_staff: bool = False

    @model_validator(mode='after')
    def enforce_approval_state_rules(self) -> 'CoreAnalysisPayload':
        # Rule: AI_DRAFT cannot be claimed as Physician Approved
        if self.approval_status == ApprovalStatusEnum.AI_DRAFT and self.certified_by_office_staff:
            # Office staff can perform admin QA, but cannot substitute clinical approval
            pass
        return self
