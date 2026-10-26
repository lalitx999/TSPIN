"""
Integration and Unit Tests for TSPI Multi-Report Generation Engine (Option 2).
Tests Service Layer (ReportGeneratorService), HTML Templates, WeasyPrint PDF Generation (300 DPI),
Zero Hallucination prose sanitization, and Cross-Report Invariant Validation with pdfplumber.
"""

import io
from django.test import TestCase, SimpleTestCase
from django.utils import timezone
import pdfplumber

from clinical.schemas import (
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
from clinical.services.report_generator import ReportGeneratorService
from clinical.invariants import ClinicalInvariantValidator
from patients.models import Patient
from clinical.models import AnalysisRecord
from django.contrib.auth import get_user_model

User = get_user_model()


class ReportGeneratorServiceUnitTests(SimpleTestCase):
    """Unit tests for ReportGeneratorService using in-memory payloads"""

    def setUp(self):
        self.identity = PatientIdentityPayload(
            patient_id=202,
            hn="HN-TSPI-88990",
            full_name="คุณกานดา สุขสมบูรณ์",
            age=42,
            sex="F",
            dob="1984-08-20"
        )

        # Build sample axes: Axis 1 (Scored), Axis 8 (Unscored HYPOTHESIS)
        self.axes = {
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
                severity_score=68.5,
                severity_band="FUNCTIONAL"
            ),
            8: AxisAssessmentPayload(
                axis_id=8,
                canonical_axis_name="Mitochondrial Network",
                canonical_domain_name="Metabolic–Energy Core",
                domain_code="D2",
                data_availability="PRESENT",
                evidence_status=EvidenceStatusEnum.HYPOTHESIS,
                assessment_status=AssessmentStatusEnum.AXIS_CANDIDATE,
                score_status=ScoreStatusEnum.NOT_SCORED,
                scoring_rule_id=None,
                severity_score=None,
                severity_band=None
            )
        }

        self.payload = CoreAnalysisPayload(
            analysis_id=777,
            approval_status=ApprovalStatusEnum.PHYSICIAN_APPROVED,
            identity=self.identity,
            axes=self.axes,
            safety_gates=SafetyGatesPayload(
                iron_supplementation_status=IronSafetyStatusEnum.HOLD_PENDING_CONFIRMATION,
                iron_clinical_guidance="Do not start empirical iron supplementation until iron status is assessed."
            ),
            module_registry=ModuleRegistryPayload(
                approved_module_count=0,
                approved_modules_whitelist=[],
                is_hidden_in_clinical_report=True
            ),
            clinical_summary="[MEASURED] ตรวจพบระดับการอักเสบสูง [HYPOTHESIS] ควรตรวจไมโตคอนเดรียเพิ่มเติม [DERIVED] ระบบชีวภาพตอบสนองดี",
            physician_notes="ผู้ป่วยควรหลีกเลี่ยงอาหารแปรรูป และตรวจซ้ำในอีก 3 เดือน",
            certified_by_office_staff=True
        )

    def test_physician_report_generation(self):
        """Phase 1 & 2: Physician Edition must include technical terms, scoring_rule_id, and safety gates"""
        html = ReportGeneratorService.render_physician_report(self.payload)
        self.assertIn("PHYSICIAN CLINICAL DOSSIER", html)
        self.assertIn("HN-TSPI-88990", html)
        self.assertIn("RULE-AXIS-01-V2", html)
        self.assertIn("HOLD_PENDING_CONFIRMATION", html)
        self.assertIn("Fail-Closed Policy", html)

        # PDF Generation (300 DPI)
        pdf_bytes = ReportGeneratorService.generate_physician_pdf(self.payload)
        self.assertTrue(len(pdf_bytes) > 5000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_patient_report_has_no_internal_tags(self):
        """Phase 2: Patient Edition must have ZERO internal tags and NO scoring rule IDs"""
        html = ReportGeneratorService.render_patient_report(self.payload)
        self.assertIn("PATIENT HEALTH BLUEPRINT", html)
        self.assertIn("HN-TSPI-88990", html)

        # Internal tags must be sanitized completely
        self.assertNotIn("[MEASURED]", html)
        self.assertNotIn("[HYPOTHESIS]", html)
        self.assertNotIn("[DERIVED]", html)
        self.assertNotIn("[CLINICAL_INFERENCE]", html)

        # Scoring rule IDs must NOT appear in patient edition
        self.assertNotIn("RULE-AXIS-01-V2", html)
        self.assertNotIn("scoring_rule_id", html)

        # PDF Generation
        pdf_bytes = ReportGeneratorService.generate_patient_pdf(self.payload)
        self.assertTrue(len(pdf_bytes) > 5000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_unscored_axis_shows_waiting_status(self):
        """P0 Rule: Axis with score=None must render 'รอการตรวจยืนยันเพิ่มเติม' and NOT '0'"""
        html = ReportGeneratorService.render_patient_report(self.payload)
        self.assertIn("รอการตรวจยืนยันเพิ่มเติม", html)

    def test_multiomics_report_shows_uncertainty(self):
        """Multi-Omics Edition must show uncertainty levels and systems biology evidence distribution"""
        html = ReportGeneratorService.render_multiomics_report(self.payload)
        self.assertIn("MULTI-OMICS & SYSTEMS BIOLOGY", html)
        self.assertIn("Evidence Confidence & Uncertainty Profile", html)
        self.assertIn("MEASURED", html)
        self.assertIn("HYPOTHESIS", html)

        # PDF Generation
        pdf_bytes = ReportGeneratorService.generate_multiomics_pdf(self.payload)
        self.assertTrue(len(pdf_bytes) > 5000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_cross_report_consistency_pass(self):
        """Phase 4: generate_all_reports must pass cross-report invariants and return 3 valid PDFs"""
        reports = ReportGeneratorService.generate_all_reports(self.payload)
        self.assertIn('physician_pdf', reports)
        self.assertIn('patient_pdf', reports)
        self.assertIn('multiomics_pdf', reports)

        for name, pdf_bytes in reports.items():
            self.assertTrue(len(pdf_bytes) > 5000, f"{name} is too small")
            self.assertTrue(pdf_bytes.startswith(b"%PDF"), f"{name} is not a valid PDF")

    def test_cross_report_blocked_when_mismatch(self):
        """Phase 4: If views mismatch on HN, age, or axis scores, it must raise BLOCKED_DATA_RECONCILIATION"""
        p_view = ReportGeneratorService.extract_cross_report_view(self.payload)
        pt_view = ReportGeneratorService.extract_cross_report_view(self.payload)
        om_view = ReportGeneratorService.extract_cross_report_view(self.payload)

        # Artificially tamper with Patient View HN
        pt_tampered = dict(pt_view)
        pt_tampered['hn'] = "HN-TAMPERED-999"

        is_valid, violations = ClinicalInvariantValidator.validate_cross_report_consistency(
            p_view, pt_tampered, om_view
        )
        self.assertFalse(is_valid)
        self.assertTrue(any("mismatch" in v.lower() for v in violations))

    def test_pdf_binary_inspection_with_pdfplumber(self):
        """Phase 4: Binary PDF Inspection with pdfplumber must locate exact patient HN in rendered pages"""
        physician_pdf = ReportGeneratorService.generate_physician_pdf(self.payload)
        with pdfplumber.open(io.BytesIO(physician_pdf)) as pdf:
            extracted_text = " ".join([page.extract_text() or "" for page in pdf.pages])
            self.assertIn("HN-TSPI-88990", extracted_text)

        # Test failure when expected HN is not in PDF
        with self.assertRaises(ValueError) as ctx:
            ReportGeneratorService._verify_rendered_pdf_binary(physician_pdf, "HN-NONEXISTENT", "Nobody")
        self.assertIn("PDF Binary Verification Failed", str(ctx.exception))


class ReportGeneratorIntegrationTests(TestCase):
    """Integration tests connecting Django DB models (AnalysisRecord) to ReportGeneratorService"""

    def setUp(self):
        self.doctor = User.objects.create_user(
            username="dr_report_test",
            password="securePassword123!",
            role="doctor"
        )
        self.patient = Patient.objects.create(
            hn="HN-INTEG-55443",
            first_name="สมหวัง",
            last_name="ใจมั่น",
            gender="M",
            phone="0819998877",
            status="medicine"
        )
        self.analysis = AnalysisRecord.objects.create(
            patient=self.patient,
            physician=self.doctor,
            status="approved",
            snapshot_scores={
                "1": 72.0,
                "2": 45.0,
                "5": 30.0,
            },
            doctor_summary="ตรวจพบความเสื่อมในระบบภูมิคุ้มกัน ควรเพิ่มสารอาหารกลุ่มต้านอนุมูลอิสระ",
            approved_at=timezone.now()
        )

    def test_payload_from_analysis_record_and_pdf_generation(self):
        """Must convert DB AnalysisRecord to CoreAnalysisPayload and generate all 3 PDFs without error"""
        payload = ReportGeneratorService.payload_from_analysis_record(self.analysis)
        self.assertEqual(payload.identity.hn, "HN-INTEG-55443")
        self.assertEqual(payload.identity.full_name, "สมหวัง ใจมั่น")
        self.assertEqual(payload.axes[1].severity_score, 72.0)
        self.assertEqual(payload.axes[1].evidence_status, EvidenceStatusEnum.MEASURED)
        self.assertIsNone(payload.axes[8].severity_score)
        self.assertEqual(payload.axes[8].evidence_status, EvidenceStatusEnum.HYPOTHESIS)

        # Batch generation with binary verification
        reports = ReportGeneratorService.generate_all_reports(payload)
        self.assertEqual(len(reports), 3)

        # Verify that HN is present in patient PDF using pdfplumber
        with pdfplumber.open(io.BytesIO(reports['patient_pdf'])) as pdf:
            text = " ".join([page.extract_text() or "" for page in pdf.pages])
            self.assertIn("HN-INTEG-55443", text)
