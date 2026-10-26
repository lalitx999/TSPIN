"""
Unit Tests for TSPI Clinical Invariants & Cross-Report Governance Engine.
Verifies Medical Board requirements from 22.09.2026 specifications.
"""

from django.test import SimpleTestCase
from .schemas import (
    CoreAnalysisPayload,
    PatientIdentityPayload,
    AxisAssessmentPayload,
    SafetyGatesPayload,
    ModuleRegistryPayload,
    ApprovalStatusEnum,
    EvidenceStatusEnum,
    AssessmentStatusEnum,
    ScoreStatusEnum,
    IronSafetyStatusEnum,
)
from .invariants import ClinicalInvariantValidator, CANONICAL_39_AXES


class ClinicalInvariantValidatorTests(SimpleTestCase):
    """ทดสอบ Hard Invariants และ Cross-Report Validation"""

    def setUp(self):
        # สร้าง Payload ผู้ป่วยตัวอย่างที่สมบูรณ์ถูกต้องตามเกณฑ์
        self.valid_identity = PatientIdentityPayload(
            patient_id=101,
            hn="HN-TSPI-00123",
            full_name="คุณสมชาย ใจดี",
            age=45,
            sex="M",
            dob="1981-05-14"
        )

        # แกนตัวอย่างที่ถูกต้อง
        self.valid_axes = {
            1: AxisAssessmentPayload(
                axis_id=1,
                canonical_axis_name="Systemic Inflammatory Load",
                canonical_domain_name="Immune–Infection Governance",
                domain_code="D1",
                data_availability="PRESENT",
                evidence_status=EvidenceStatusEnum.MEASURED,
                assessment_status=AssessmentStatusEnum.ASSESSED,
                score_status=ScoreStatusEnum.APPROVED_RULE_SCORED,
                scoring_rule_id="RULE-AXIS-01-V2",
                severity_score=65.0,
                severity_band="FUNCTIONAL"
            ),
            8: AxisAssessmentPayload(
                axis_id=8,
                canonical_axis_name="Mitochondrial Network",
                canonical_domain_name="Metabolic–Energy Core",
                domain_code="D2",
                data_availability="PRESENT",
                evidence_status=EvidenceStatusEnum.HYPOTHESIS,
                assessment_status=AssessmentStatusEnum.ASSESSED,
                score_status=ScoreStatusEnum.NOT_SCORED,
                scoring_rule_id=None,
                severity_score=None,  # HYPOTHESIS must have None
                severity_band=None
            )
        }

    def test_valid_payload_passes_validation(self):
        """Payload ที่ถูกต้องตามกฎทั้งหมดต้องผ่าน 100% ไม่มี violations"""
        payload = CoreAnalysisPayload(
            analysis_id=999,
            approval_status=ApprovalStatusEnum.AI_DRAFT,
            identity=self.valid_identity,
            axes=self.valid_axes,
            safety_gates=SafetyGatesPayload(),
            module_registry=ModuleRegistryPayload(approved_module_count=0, is_hidden_in_clinical_report=True)
        )

        is_valid, violations = ClinicalInvariantValidator.validate_payload(payload)
        self.assertTrue(is_valid)
        self.assertEqual(len(violations), 0)

    def test_hypothesis_with_numeric_score_is_rejected(self):
        """P0 Rule: HYPOTHESIS ที่มีคะแนนตัวเลข (เช่น 75/100) ต้องถูกปฏิเสธทันที"""
        with self.assertRaises(ValueError) as ctx:
            # Pydantic Model Validator จะดักจับตั้งแต่การสร้าง Object
            AxisAssessmentPayload(
                axis_id=8,
                canonical_axis_name="Mitochondrial Network",
                canonical_domain_name="Metabolic–Energy Core",
                domain_code="D2",
                evidence_status=EvidenceStatusEnum.HYPOTHESIS,
                scoring_rule_id="RULE-TEMP",
                severity_score=75.0  # ผิดกฎ! HYPOTHESIS ห้ามมีคะแนน
            )
        self.assertIn("HYPOTHESIS or AXIS_CANDIDATE must have severity_score=None", str(ctx.exception))

    def test_axis_candidate_with_numeric_score_is_rejected(self):
        """P0 Rule: AXIS_CANDIDATE ที่มีคะแนนตัวเลขต้องถูกปฏิเสธทันที"""
        with self.assertRaises(ValueError) as ctx:
            AxisAssessmentPayload(
                axis_id=16,
                canonical_axis_name="Upper GI & Digestive Capacity",
                canonical_domain_name="Digestive–Gut Ecosystem",
                domain_code="D5",
                assessment_status=AssessmentStatusEnum.AXIS_CANDIDATE,
                scoring_rule_id="RULE-TEMP",
                severity_score=70.0  # ผิดกฎ!
            )
        self.assertIn("HYPOTHESIS or AXIS_CANDIDATE must have severity_score=None", str(ctx.exception))

    def test_score_without_scoring_rule_id_is_rejected(self):
        """P0 Rule: มีคะแนนตัวเลขแต่ไม่มี scoring_rule_id ที่ได้รับการอนุมัติ ต้องถูกปฏิเสธ"""
        with self.assertRaises(ValueError) as ctx:
            AxisAssessmentPayload(
                axis_id=1,
                canonical_axis_name="Systemic Inflammatory Load",
                canonical_domain_name="Immune–Infection Governance",
                domain_code="D1",
                evidence_status=EvidenceStatusEnum.MEASURED,
                scoring_rule_id=None,  # ไม่มี Rule ID!
                severity_score=60.0
            )
        self.assertIn("Numeric score 60.0 provided without approved scoring_rule_id", str(ctx.exception))

    def test_cross_report_identity_mismatch_fails_validator(self):
        """P0 Rule: หากอายุ, เพศ หรือ HN ระหว่าง 3 รายงานไม่ตรงกัน ต้อง Fail ทันที"""
        physician_view = {"hn": "HN-TSPI-00123", "age": 52, "sex": "F", "scores": {1: 50}, "approval_status": "DRAFT"}
        patient_view = {"hn": "HN-TSPI-00123", "age": 52, "sex": "F", "scores": {1: 50}, "approval_status": "DRAFT"}
        omics_view = {"hn": "HN-TSPI-00123", "age": 39, "sex": "F", "scores": {1: 50}, "approval_status": "DRAFT"}  # Mismatch อายุ 39 vs 52!

        is_consistent, violations = ClinicalInvariantValidator.validate_cross_report_consistency(
            physician_view, patient_view, omics_view
        )

        self.assertFalse(is_consistent)
        self.assertTrue(any("Age '39' != Physician Age '52'" in v for v in violations))

    def test_cross_report_score_mismatch_fails_validator(self):
        """P0 Rule: คะแนนในแต่ละแกนระหว่าง 3 รายงานต้องตรงกันทุกจุด"""
        physician_view = {"hn": "HN-001", "age": 40, "sex": "M", "scores": {5: 75}, "approval_status": "DRAFT"}
        patient_view = {"hn": "HN-001", "age": 40, "sex": "M", "scores": {5: 70}, "approval_status": "DRAFT"}  # Mismatch! 75 vs 70
        omics_view = {"hn": "HN-001", "age": 40, "sex": "M", "scores": {5: 75}, "approval_status": "DRAFT"}

        is_consistent, violations = ClinicalInvariantValidator.validate_cross_report_consistency(
            physician_view, patient_view, omics_view
        )

        self.assertFalse(is_consistent)
        self.assertTrue(any("Cross-Report Axis Score Mismatch on Axis 5" in v for v in violations))

    def test_sanitize_patient_prose_removes_internal_tags(self):
        """ทดสอบการถอด Internal Engine Tags ออกจากข้อความรายงานของคนไข้"""
        raw_text = "คนไข้มีค่า [MEASURED] น้ำตาลสูง และมี [HYPOTHESIS] ภาวะดื้อต่ออินซูลิน [STANDARD_CLINICAL]"
        sanitized = ClinicalInvariantValidator.sanitize_patient_prose(raw_text)

        self.assertNotIn("[MEASURED]", sanitized)
        self.assertNotIn("[HYPOTHESIS]", sanitized)
        self.assertNotIn("[STANDARD_CLINICAL]", sanitized)
        self.assertIn("ผลตรวจทางห้องปฏิบัติการพบว่า", sanitized)
        self.assertIn("ในเบื้องต้นมีข้อสังเกตว่า", sanitized)

    def test_canonical_ontology_no_drift(self):
        """
        Anti-Drift Test: ป้องกันการคลาดเคลื่อนของ Ontology Master
        ตรวจสอบว่าทุกแกนใน JSON สามารถ resolve เข้าสู่ Canonical Master ได้ 100%
        """
        import json
        from pathlib import Path
        from .invariants import CANONICAL_39_AXES, resolve_canonical_axis_name

        json_path = Path(__file__).resolve().parent / 'data' / 'tspi_39_axes.json'
        self.assertTrue(json_path.exists(), "tspi_39_axes.json must exist")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        found_axes = set()
        for dom in data.get('domains', []):
            for ax in dom.get('axes', []):
                axis_id = ax.get('axis_id')
                raw_name = ax.get('name')
                found_axes.add(axis_id)

                # ต้อง resolve กลับมาเป็น Canonical Master Name ได้
                resolved = resolve_canonical_axis_name(axis_id, raw_name)
                canonical_expected = CANONICAL_39_AXES.get(axis_id)
                self.assertEqual(
                    resolved,
                    canonical_expected,
                    f"Drift detected on Axis {axis_id}: '{raw_name}' resolves to '{resolved}' instead of '{canonical_expected}'"
                )

        # ต้องมีครบ 39 แกน
        self.assertEqual(len(found_axes), 39, "JSON must cover exactly 39 axes")
