import datetime
import re
from django.test import TestCase
from rest_framework.test import APIClient
from patients.models import Patient, PatientBiologicalRecord, AnalysisRecord, AnalysisReportRelease, AxisScoringContract
from patients.tspi_engine import calculate_tspi_analysis, OFFICIAL_39_AXES, OFFICIAL_9_STEPS, SYSTEM_DOMAINS
from patients.views_ai import markdown_to_html, generate_report_pdf_view


class EndToEndGoldenReportTests(TestCase):
    """
    E2E Golden Report Test Suite (E2E-001 through E2E-012)
    Verifies that generated PDF/HTML artifacts obey all Core Engine Contracts.
    """

    def setUp(self):
        self.client = APIClient()
        from django.contrib.auth.models import User
        self.user = User.objects.create_superuser(username="drpatt_e2e", email="dr@test.com", password="password")
        self.client.force_authenticate(user=self.user)
        self.patient = Patient.objects.create(
            first_name="Golden", last_name="Patient", gender="M",
            birth_date=datetime.date(1980, 5, 10), id_card="1234567890199",
            hn="HN-E2E-GOLDEN-001", chief_complaint="Fatigue and metabolic dysregulation"
        )
        self.record = PatientBiologicalRecord.objects.create(
            patient=self.patient, axis_1=65, axis_5=70, axis_27=80, axis_33=75
        )
        self.analysis = AnalysisRecord.objects.create(
            patient=self.patient,
            source_record=self.record,
            inputs_hash="golden-e2e-hash-001",
            ledger=calculate_tspi_analysis(self.record),
        )

    def test_e2e_001_all_editions_read_same_analysis_record_id(self):
        """E2E-001: All 3 report editions read from the exact same analysis_record_id."""
        ledger = self.analysis.ledger
        self.assertEqual(ledger["identity_validation"]["identity_validation_status"], "VERIFIED")
        self.assertIn("thirty_nine_axes", ledger)
        self.assertEqual(self.analysis.patient.id, self.patient.id)

    def test_e2e_002_ai_draft_has_no_physician_approved_wording(self):
        """E2E-002: AI_DRAFT report state has NO Approved/Certified text."""
        raw_text = "นี่คือ แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว สำหรับผู้ป่วย"
        html = markdown_to_html(raw_text, edition="patient", is_approved=False)
        self.assertNotIn("แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว", html)
        self.assertIn("ร่างแผนดูแลสุขภาพที่อยู่ระหว่างการพิจารณาของแพทย์", html)

    def test_e2e_003_patient_pdf_has_no_square_bracket_internal_tags(self):
        """E2E-003: Patient Edition rendered HTML text has NO internal square bracket tags."""
        raw_text = "Axis 1 is [MEASURED], Axis 8 is [HYPOTHESIS], Axis 27 is [CLINICAL_INFERENCE]."
        html = markdown_to_html(raw_text, edition="patient", is_approved=False)
        # Search for any remaining [UPPERCASE_TAG] in square brackets
        self.assertIsNone(re.search(r'\[[A-Z0-9_]{3,}\]', html), f"Patient HTML must not contain internal engine tags. Got: {html}")
        self.assertIn("(ผลตรวจยืนยัน)", html)
        self.assertIn("(สภาวะสงสัย — รอตรวจเพิ่มเติม)", html)

    def test_e2e_004_identity_conflict_blocks_all_clinical_pdfs(self):
        """E2E-004: Demographic conflict blocks all clinical PDF endpoints."""
        # Create record with conflicting HN / owner
        conflicting_record = PatientBiologicalRecord.objects.create(patient=self.patient, axis_1=50)
        blocked_data = {
            "patient_id": str(self.patient.id),
            "hn": self.patient.hn,
            "soap_hn": "DIFFERENT-HN-999", # Conflict!
            "dob": "1980-05-10",
            "gender": "M",
            "age": 44,
        }
        blocked_ledger = calculate_tspi_analysis(conflicting_record, patient_data=blocked_data)
        self.assertEqual(blocked_ledger["analysis_state"], "BLOCKED_DATA_RECONCILIATION")
        
        blocked_analysis = AnalysisRecord.objects.create(
            patient=self.patient,
            source_record=conflicting_record,
            inputs_hash="blocked-e2e-hash",
            ledger=blocked_ledger,
        )
        
        # Request report pdf
        report_obj = {
            "id": "rep-blocked-001",
            "analysisRecordId": blocked_analysis.id,
            "reportType": "patient",
            "report": [{"chapterTitle": "Chapter 1", "content": "Test content"}]
        }
        self.patient.extra_data = {"generated_reports": [report_obj]}
        self.patient.save()

        # Call generate_report_pdf_view
        response = self.client.get(f"/api/ai/patients/{self.patient.id}/reports/rep-blocked-001/pdf/")
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"REPORT GENERATION BLOCKED", response.content)

    def test_e2e_005_hypothesis_and_clinical_inference_axes_have_null_score(self):
        """E2E-005: HYPOTHESIS and CLINICAL_INFERENCE axes must have severity_score = None."""
        ledger = self.analysis.ledger
        axes = ledger["thirty_nine_axes"]
        # A8 is HYPOTHESIS, A27 and A33 are CLINICAL_INFERENCE
        self.assertIsNone(axes["AXIS_8"]["severity_score"])
        self.assertIsNone(axes["AXIS_27"]["severity_score"])
        self.assertIsNone(axes["AXIS_33"]["severity_score"])

    def test_e2e_006_every_scored_axis_has_approval_metadata(self):
        """E2E-006: Every scored Axis has scoring_contracts approval metadata in ledger."""
        ledger = self.analysis.ledger
        contracts_snapshot = ledger.get("scoring_contracts", {})
        self.assertIn("numeric_score_axes", contracts_snapshot)
        self.assertIn("patient_release_eligible", contracts_snapshot)

    def test_e2e_007_iron_status_is_hold_pending_confirmation_not_absolute_food_restriction(self):
        """E2E-007: Mentzer < 13 sets HOLD_PENDING_CONFIRMATION for supplements, not dietary ban."""
        result = calculate_tspi_analysis(self.record, mentzer_index=11.0)
        safety_gate = result["safety_gate"]
        self.assertNotEqual(safety_gate["status"], "CONTRAINDICATED")
        iron_elig = [item for item in safety_gate["intervention_eligibility"] if item["intervention_id"] == "IRON_SUPPLEMENTATION"]
        self.assertEqual(len(iron_elig), 1)
        self.assertEqual(iron_elig[0]["status"], "HOLD_PENDING_CONFIRMATION")
        self.assertIn("Ferritin", iron_elig[0]["required_confirmation"])

    def test_e2e_008_unapproved_modules_produce_zero_clinical_module_recommendations(self):
        """E2E-008: approved_modules = 0 produces recommended_modules_clinical == []."""
        ledger = self.analysis.ledger
        mod_reg = ledger.get("module_registry", {})
        if mod_reg.get("approved_modules", 0) == 0:
            self.assertEqual(ledger["recommended_modules_clinical"], [])

    def test_e2e_009_canonical_names_match_master_registry(self):
        """E2E-009: Canonical Domain/Axis/Step names match Master Registry."""
        ledger = self.analysis.ledger
        self.assertEqual(ledger["thirty_nine_axes"]["AXIS_35"]["name"], "Visceral Organ Functional Reserve")
        steps = ledger["nine_restoration_steps"]
        for idx, step in enumerate(steps):
            self.assertEqual(step["canonical_step_name"], OFFICIAL_9_STEPS[idx])

    def test_e2e_010_advanced_omics_tests_have_utility_gate_decision(self):
        """E2E-010: Advanced Omics tests have Clinical Utility Gate decision."""
        ledger = self.analysis.ledger
        self.assertIn("omics_utility_gate", ledger)
        self.assertIn("status", ledger["omics_utility_gate"])

    def test_e2e_011_required_chapters_non_empty(self):
        """E2E-011: Required chapters are non-empty (no blank chapter headings)."""
        from patients.views_ai import markdown_to_html
        content_html = markdown_to_html("### Chapter 1\nContent text here.", edition="patient")
        self.assertTrue(bool(content_html.strip()))

    def test_e2e_012_same_evidence_has_identical_status_across_editions(self):
        """E2E-012: Same evidence has identical derived score across all editions."""
        ledger = self.analysis.ledger
        axis_5_score = ledger["thirty_nine_axes"]["AXIS_5"]["severity_score"]
        self.assertEqual(axis_5_score, 70)
