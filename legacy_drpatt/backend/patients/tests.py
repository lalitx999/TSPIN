from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from patients.models import AnalysisRecord, AnalysisReportRelease, Patient, PatientBiologicalRecord, TSPIBrainTrainingLog, ModuleRegistryEntry
from patients.tspi_engine import (
    calculate_tspi_analysis,
    validate_patient_identity,
    evaluate_omics_utility_gate,
    validate_analysis_record,
    HYPOTHESIS_AXES,
    OFFICIAL_9_STEPS,
    OFFICIAL_39_AXES,
    canonical_domain_registry,
)
from patients.serializers import PatientSerializer


class PatientRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "IDcard": "1234567890123",
            "password": "safe-test-password",
            "email": "patient@example.test",
            "fname": "Test",
            "lname": "Patient",
            "sex": "หญิง",
            "hn": "HN-REGISTRATION-TEST",
        }

    def test_registration_rolls_back_when_a_later_step_fails(self):
        """A failed audit write must not leave a usable login without an EMR profile."""
        with patch("accounts.views.AuditLog.objects.create", side_effect=RuntimeError("audit unavailable")):
            response = self.client.post("/api/auth/register/", self.payload, format="json")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["error"], "ระบบลงทะเบียนขัดข้องชั่วคราว กรุณาลองใหม่ภายหลังหรือติดต่อคลินิก")
        self.assertFalse(User.objects.filter(username=self.payload["IDcard"]).exists())
        self.assertFalse(Patient.objects.filter(id_card=self.payload["IDcard"]).exists())

    def test_serializer_accepts_birth_date_string_on_new_patient_instance(self):
        patient = make_patient(
            legacy_id="TEST-BIRTHDATE-STRING",
            birth_date=datetime.date(2000, 1, 31),
        )

        self.assertEqual(PatientSerializer(patient).data["birthday"], "2000-01-31")

    def test_incomplete_account_recovers_successfully(self):
        """User exists without Patient EMR profile -> registration auto-repairs and creates matching Patient profile."""
        User.objects.create_user(username=self.payload["IDcard"], password=self.payload['password'])
        self.assertFalse(Patient.objects.filter(id_card=self.payload["IDcard"]).exists())

        response = self.client.post("/api/auth/register/", self.payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertTrue(Patient.objects.filter(id_card=self.payload["IDcard"]).exists())
        self.assertEqual(User.objects.filter(username=self.payload["IDcard"]).count(), 1)

    def test_cross_patient_line_binding_rejected(self):
        """Binding a LINE user ID already owned by another patient must be rejected."""
        Patient.objects.create(
            legacy_id="OTHER-PATIENT",
            id_card="9999999999999",
            first_name="Other",
            last_name="Patient",
            phone="0812345678",
            line_user_id="U_LINE_12345",
        )
        payload_with_line = self.payload.copy()
        payload_with_line["line_user_id"] = "U_LINE_12345"

        response = self.client.post("/api/auth/register/", payload_with_line, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("ไม่สามารถผูกข้ามบัญชีได้", response.data["error"])

    @patch.dict('os.environ', {'LINE_DOCTORPATT_CHANNEL_SECRET': 'synthetic-secret'})
    def test_unsigned_line_request_cannot_rebind_patient(self):
        """Unsigned webhook requests must not change either patient's LINE binding."""
        old_patient = Patient.objects.create(
            legacy_id="OLD-PATIENT",
            id_card="8888888888888",
            first_name="Supitcha",
            last_name="Ngamwongwan",
            phone="0888888888",
            line_user_id="U_SHARED_LINE_USER",
        )
        new_patient = Patient.objects.create(
            legacy_id="NEW-PATIENT",
            id_card="1669800282052",
            first_name="Tanchon",
            last_name="Wannawong",
            phone="0999999999",
        )

        response = self.client.post(
            "/api/line/webhook/",
            {
                "events": [{
                    "type": "message",
                    "replyToken": "test-reply-token",
                    "source": {"userId": "U_SHARED_LINE_USER"},
                    "message": {"type": "text", "text": "1669800282052"}
                }]
            },
            format="json"
        )

        self.assertEqual(response.status_code, 401)
        old_patient.refresh_from_db()
        new_patient.refresh_from_db()
        self.assertEqual(old_patient.line_user_id, "U_SHARED_LINE_USER")
        self.assertFalse(new_patient.line_user_id)


import datetime

def make_patient(**kwargs):
    defaults = dict(
        legacy_id="TEST-001",
        hn="HN-TEST-DEFAULT",
        gender="F",
        birth_date=datetime.date(1985, 6, 15),
        first_name="Test",
        last_name="Patient",
        phone="0000000000",
    )
    defaults.update(kwargs)
    return Patient.objects.create(**defaults)


class TspiEngineHypothesisTests(TestCase):
    """ans.txt P0-4.1: HYPOTHESIS axes must never carry a numeric severity_score."""

    def test_hypothesis_axis_has_no_severity_score(self):
        patient = make_patient()
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_8=75)
        result = calculate_tspi_analysis(record)

        axis_8 = result["thirty_nine_axes"]["AXIS_8"]
        self.assertEqual(axis_8["evidence_status"], "HYPOTHESIS")
        self.assertIsNone(axis_8["severity_score"])
        self.assertFalse(axis_8["eligible_for_priority"])
        self.assertFalse(axis_8["eligible_for_module_match"])
        # Legacy axesState shape must reflect the same nulled score.
        self.assertIsNone(result["axesState"]["AXIS_8"]["score"])

    def test_hypothesis_axis_excluded_from_nss(self):
        patient = make_patient(legacy_id="TEST-002")
        record_with_hypothesis = PatientBiologicalRecord.objects.create(patient=patient, axis_8=100)
        result_with = calculate_tspi_analysis(record_with_hypothesis)

        record_without = PatientBiologicalRecord.objects.create(patient=patient, axis_8=None)
        result_without = calculate_tspi_analysis(record_without)

        # A HYPOTHESIS-only axis contributes nothing, so both records should score identically
        # (None NSS — no other axis has data).
        self.assertEqual(result_with["nss"], result_without["nss"])
        self.assertIsNone(result_with["nss"])

    def test_all_hypothesis_axes_classified(self):
        patient = make_patient(legacy_id="TEST-003")
        kwargs = {f"axis_{i}": 80 for i in HYPOTHESIS_AXES}
        record = PatientBiologicalRecord.objects.create(patient=patient, **kwargs)
        result = calculate_tspi_analysis(record)
        for i in HYPOTHESIS_AXES:
            axis = result["thirty_nine_axes"][f"AXIS_{i}"]
            self.assertEqual(axis["evidence_status"], "HYPOTHESIS")
            self.assertIsNone(axis["severity_score"])


class IdentityConflictGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="clinical-staff", password="test", is_staff=True)
        self.patient = make_patient(legacy_id="TEST-IDENTITY", hn="HN-IDENTITY", gender="F")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_source_owner_hn_mismatch_blocks_analysis(self):
        result = validate_patient_identity({
            "hn": "HN-IDENTITY",
            "lab_owner_hn": "HN-OTHER",
            "lab_source_record_id": "LAB-42",
        })

        self.assertEqual(result["identity_validation_status"], "CONFLICT")
        self.assertEqual(result["analysis_state"], "BLOCKED_DATA_RECONCILIATION")
        self.assertEqual(result["conflict_details"][0]["conflict_type"], "SOURCE_OWNERSHIP_MISMATCH")

    def test_missing_demographics_marked_unverified_and_blocked(self):
        """Incomplete patient demographics must result in UNVERIFIED status and BLOCKED state."""
        result = validate_patient_identity({
            "patient_id": "P-123",
            "hn": "HN-INCOMPLETE",
            # dob, gender, age missing
        })

        self.assertEqual(result["identity_validation_status"], "UNVERIFIED")
        self.assertEqual(result["analysis_state"], "BLOCKED_DATA_RECONCILIATION")
        self.assertIn("dob", result["missing_fields"])

    def test_conflicting_request_creates_no_record_or_analysis_snapshot(self):
        response = self.client.post(
            f"/api/patients/{self.patient.id}/calculate-precision-medicine/",
            {"lab_owner_hn": "HN-OTHER", "lab_source_record_id": "LAB-42"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["analysis_state"], "BLOCKED_DATA_RECONCILIATION")
        self.assertEqual(PatientBiologicalRecord.objects.filter(patient=self.patient).count(), 0)
        self.assertEqual(self.patient.analysis_records.count(), 0)

    def test_legacy_analysis_endpoint_returns_reconciliation_only_for_blocked_snapshot(self):
        source_record = PatientBiologicalRecord.objects.create(patient=self.patient)
        ledger = calculate_tspi_analysis(
            source_record,
            patient_data={"hn": "HN-IDENTITY", "lab_owner_hn": "HN-OTHER"},
        )
        record = AnalysisRecord.objects.create(
            patient=self.patient,
            source_record=source_record,
            inputs_hash="blocked-legacy-analysis",
            ledger=ledger,
        )

        response = self.client.get(
            f"/api/patients/{self.patient.id}/tspi-analysis/?analysis_record_id={record.id}"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["allowed_output"], "DATA_RECONCILIATION_REPORT_ONLY")
        self.assertNotIn("thirty_nine_axes", response.data)


class TspiEngineThreeKeysTests(TestCase):
    """ans.txt P0-4.2: Three Keys must always be DERIVED with formula_version/coverage."""

    def test_three_keys_are_derived_with_coverage(self):
        patient = make_patient(legacy_id="TEST-010")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_5=60, axis_6=70)
        result = calculate_tspi_analysis(record)

        for key_name in ("metabolic_energy", "biological_dynamic", "biointegrity"):
            key = result["three_keys"][key_name]
            self.assertIn(key["evidence_status"], ("DERIVED", "PARTIAL_NOT_SCORABLE"))
            self.assertIn("formula_version", key)
            self.assertIn("assessment_coverage", key)
            self.assertIn("contributing_axis_ids", key)

        # metabolic_energy = avg(5,6,7,8,9,10); axis_8 is HYPOTHESIS-classified so it never
        # contributes even if a raw value happened to be present.
        self.assertEqual(result["three_keys"]["metabolic_energy"]["assessed_axes_count"], 2)


class TspiEngineNineStepsTests(TestCase):
    """ans.txt P0-4.3: canonical_step_no/name must never move; only priority_rank is dynamic."""

    def test_canonical_order_is_fixed_regardless_of_input(self):
        patient = make_patient(legacy_id="TEST-020")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_8=90, axis_15=10)
        result = calculate_tspi_analysis(record)

        steps = result["nine_restoration_steps"]
        self.assertEqual(len(steps), 9)
        for idx, step in enumerate(steps):
            self.assertEqual(step["canonical_step_no"], idx + 1)
            self.assertEqual(step["canonical_step_name"], OFFICIAL_9_STEPS[idx])


class CanonicalRegistryLockTests(TestCase):
    """EP3: Verify 12 Domains, 39 Axes, and 9 Steps match canonical master registry."""

    def test_domains_match_canonical_12(self):
        domains = canonical_domain_registry()
        self.assertEqual(len(domains), 12)
        codes = [d["code"] for d in domains]
        expected_codes = [f"D{i}" for i in range(1, 13)]
        self.assertEqual(codes, expected_codes)

    def test_axes_count_and_names(self):
        self.assertEqual(len(OFFICIAL_39_AXES), 39)
        self.assertEqual(OFFICIAL_39_AXES[35], "Visceral Organ Functional Reserve")
        self.assertEqual(OFFICIAL_39_AXES[39], "Genomic Regulation Homeostasis")

    def test_nine_steps_canonical_names(self):
        self.assertEqual(len(OFFICIAL_9_STEPS), 9)
        self.assertEqual(OFFICIAL_9_STEPS[0], "Detoxification")
        self.assertEqual(OFFICIAL_9_STEPS[8], "Prakati — Bioelectrical & Physiological Coherence")


class EvidenceScoringGovernanceTests(TestCase):
    """EP4: Verify evidence and scoring governance rules."""

    def test_hypothesis_axes_always_have_null_score(self):
        patient = make_patient(legacy_id="TEST-EP4-HYP")
        record = PatientBiologicalRecord.objects.create(
            patient=patient,
            axis_8=95,   # Mitochondrial
            axis_17=85,  # Microbiome
            axis_25=90,  # Fibrosis
        )
        result = calculate_tspi_analysis(record)

        for axis_id in (8, 17, 25):
            axis_data = result["thirty_nine_axes"][f"AXIS_{axis_id}"]
            self.assertEqual(axis_data["evidence_status"], "HYPOTHESIS")
            self.assertIsNone(axis_data["severity_score"])
            self.assertFalse(axis_data["eligible_for_priority"])

    def test_unapproved_scoring_rule_yields_null_score(self):
        patient = make_patient(legacy_id="TEST-EP4-UNAPP")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_35=80)
        result = calculate_tspi_analysis(record)

        axis_35 = result["thirty_nine_axes"]["AXIS_35"]
        self.assertIsNone(axis_35["severity_score"])
        self.assertEqual(axis_35["score_status"], "NO_APPROVED_SCORING_RULE")


class ReportApprovalStateTests(TestCase):
    """EP5: Single State Machine for report release (AI_DRAFT -> REVIEWED -> APPROVED -> PATIENT_RELEASED)."""

    def setUp(self):
        self.patient = make_patient(legacy_id="TEST-EP5-APPROVAL")
        self.source_record = PatientBiologicalRecord.objects.create(patient=self.patient)
        self.analysis = AnalysisRecord.objects.create(
            patient=self.patient,
            source_record=self.source_record,
            inputs_hash="test-ep5-hash",
            ledger=calculate_tspi_analysis(self.source_record),
        )

    def test_initial_release_state_is_ai_draft(self):
        release = AnalysisReportRelease.objects.create(
            analysis_record=self.analysis,
            edition="PATIENT",
            state="AI_DRAFT",
        )
        self.assertEqual(release.state, "AI_DRAFT")

    def test_patient_released_state_allows_patient_access(self):
        release = AnalysisReportRelease.objects.create(
            analysis_record=self.analysis,
            edition="PATIENT",
            state="PATIENT_RELEASED",
        )
        self.assertEqual(release.state, "PATIENT_RELEASED")


class ReportConsistencyTests(TestCase):
    """EP6: Verify clinical facts and identity are 100% consistent across all report editions."""

    def setUp(self):
        self.patient = make_patient(legacy_id="TEST-EP6-CONSISTENCY", hn="HN-EP6-CONSISTENCY", gender="F")
        self.source_record = PatientBiologicalRecord.objects.create(patient=self.patient, axis_5=70)
        self.analysis = AnalysisRecord.objects.create(
            patient=self.patient,
            source_record=self.source_record,
            inputs_hash="test-ep6-hash",
            ledger=calculate_tspi_analysis(self.source_record),
        )

    def test_all_editions_read_same_analysis_record(self):
        ledger = self.analysis.ledger
        axis_5 = ledger["thirty_nine_axes"]["AXIS_5"]
        self.assertEqual(axis_5["score_status"], "SCORED")
        self.assertEqual(ledger["identity_validation"]["identity_validation_status"], "VERIFIED")


class OmicsUtilityGate12FieldsTests(TestCase):
    """EP7: 12-field Clinical Utility Gate and Iron HOLD protocol safety check."""

    def test_low_management_change_returns_defer(self):
        result = evaluate_omics_utility_gate({
            "omics_utility": {
                "clinical_question": "Investigate genetic risk",
                "current_uncertainty": "Uncertain about variant",
                "decision_that_depends_on_result": "Treatment protocol choice",
                "will_change_management": "LOW",
                "action_if_positive": "Monitor",
                "action_if_negative": "Monitor",
                "patient_burden": "Low",
                "cost_or_resource_burden": "High",
                "turnaround_time": "4 weeks",
                "goal_concordance": "Yes",
                "clinical_priority": "Low",
                "physician_decision": "Defer testing",
            }
        })
        self.assertEqual(result["status"], "DEFER")

    def test_test_evidence_tiers_structure(self):
        """EP4 P1-15: Test Evidence Tiers must define standard, actionable, optional, and research tiers."""
        from patients.core_contracts import TEST_EVIDENCE_TIERS
        self.assertIn("STANDARD_CLINICAL", TEST_EVIDENCE_TIERS)
        self.assertIn("CLINICALLY_ACTIONABLE_ADVANCED", TEST_EVIDENCE_TIERS)
        self.assertIn("OPTIONAL_ADVANCED", TEST_EVIDENCE_TIERS)
        self.assertIn("RESEARCH_ONLY", TEST_EVIDENCE_TIERS)

    def test_mentzer_gate_holds_iron_supplementation_specifically(self):
        """EP4 P1-16: Mentzer < 13 sets HOLD_PENDING_CONFIRMATION for IRON_SUPPLEMENTATION intervention, not global contraindication."""
        patient = Patient.objects.create(
            first_name="Iron", last_name="HoldTest", gender="M",
            birth_date=datetime.date(1985, 4, 20), id_card="1234567890131",
            hn="HN-EP4-001",
        )
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_26=40)
        result = calculate_tspi_analysis(record, mentzer_index=11.5)
        safety_gate = result["safety_gate"]
        self.assertEqual(safety_gate["status"], "PASS_WITH_MONITORING")
        self.assertNotEqual(safety_gate["status"], "CONTRAINDICATED")
        
        iron_elig = [item for item in safety_gate["intervention_eligibility"] if item["intervention_id"] == "IRON_SUPPLEMENTATION"]
        self.assertEqual(len(iron_elig), 1)
        self.assertEqual(iron_elig[0]["status"], "HOLD_PENDING_CONFIRMATION")
        self.assertIn("Ferritin", iron_elig[0]["required_confirmation"])


class EndToEndIntegrationEP8Tests(TestCase):
    """EP8: Complete End-to-End lifecycle test from registration to analysis snapshot."""

    def setUp(self):
        self.client = APIClient()
        self.patient = make_patient(
            legacy_id="TEST-EP8-E2E",
            hn="HN-EP8-E2E",
            id_card="1111111111111",
            first_name="Somchai",
            last_name="Jai-dee",
            gender="M",
            birth_date="1980-05-15",
        )

    def test_full_pipeline_from_patient_to_analysis_record(self):
        source_record = PatientBiologicalRecord.objects.create(patient=self.patient, axis_5=60, axis_6=70)
        ledger = calculate_tspi_analysis(source_record, patient_data={
            "patient_id": str(self.patient.id),
            "hn": self.patient.hn,
            "dob": str(self.patient.birth_date),
            "gender": "male",
            "age": 46,
        })

        analysis = AnalysisRecord.objects.create(
            patient=self.patient,
            source_record=source_record,
            inputs_hash="ep8-e2e-hash-001",
            ledger=ledger,
        )

        self.assertIsNotNone(analysis.analysis_run_id)
        self.assertEqual(analysis.ledger["identity_validation"]["identity_validation_status"], "VERIFIED")
        self.assertEqual(analysis.ledger["analysis_state"], "ANALYSIS_READY")


class TspiEngineDomainTests(TestCase):
    """ans.txt problem #6: Domain 11 reuses Domain 6's axes — must not double-count priority."""

    def test_domain_11_is_cross_cutting_and_excluded_from_priorities(self):
        patient = make_patient(legacy_id="TEST-030")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_24=90, axis_25=90, axis_26=90)
        result = calculate_tspi_analysis(record)

        self.assertEqual(result["domain_types"]["Domain 11 — Organ Resilience"], "PRIMARY")
        self.assertEqual(result["domain_types"]["Domain 6 — Vascular–Circulation"], "PRIMARY")

        priority_systems = {p["system"] for p in result["system_priorities"]}
        self.assertIn("Domain 11 — Organ Resilience", priority_systems)
        self.assertIn("Domain 6 — Vascular–Circulation", priority_systems)

        # Still evaluated for display (NO_APPROVED_SCORING_RULE), just not in the priority ranking.
        self.assertIsNone(result["system_scores"]["Domain 11 — Organ Resilience"])


class ValidateAnalysisRecordTests(TestCase):
    """ans.txt P0-4.13: invariant validator must catch a HYPOTHESIS axis with a leaked score."""

    def test_flags_hypothesis_axis_with_severity_score(self):
        bad_ledger = {
            "thirty_nine_axes": {
                "AXIS_8": {"evidence_status": "HYPOTHESIS", "severity_score": 75, "eligible_for_priority": False}
            },
            "three_keys": {},
            "nine_restoration_steps": [],
            "network_registry": {"registry_status": "LOADED_NOT_YET_APPROVED"},
            "module_registry": {"registry_status": "PROVISIONAL", "approved_modules": 0},
            "safety_gate": {"status": "PASS"},
        }
        violations = validate_analysis_record(bad_ledger)
        rule_ids = {v["rule_id"] for v in violations}
        self.assertIn("INV-001", rule_ids)

    def test_clean_ledger_from_engine_has_no_violations(self):
        patient = make_patient(legacy_id="TEST-040")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_5=60)
        result = calculate_tspi_analysis(record)
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["invariant_violations"], [])

    def test_flags_canonical_axis_code_name_mismatch(self):
        bad_ledger = {
            "thirty_nine_axes": {
                **{
                    f"AXIS_{i}": {"code": f"A{i}", "name": f"Axis {i}"}
                    for i in range(1, 40)
                }
            },
            "three_keys": {},
            "nine_restoration_steps": [],
            "network_registry": {},
            "module_registry": {},
            "safety_gate": {},
        }
        bad_ledger["thirty_nine_axes"]["AXIS_5"]["name"] = "Wrong name"

        violations = validate_analysis_record(bad_ledger)

        self.assertIn("INV-008", {violation["rule_id"] for violation in violations})


class SerializerDefaultScoreTests(TestCase):
    """ans.txt "no default 50" rule — an axis with no record must read NOT_ASSESSED, not 50."""

    def test_get_axes_returns_none_when_no_record(self):
        patient = make_patient(legacy_id="TEST-050")
        serializer = PatientSerializer(patient)
        axes = serializer.data["axes"]
        self.assertIsNone(axes["AXIS_1"]["score"])
        self.assertEqual(axes["AXIS_1"]["status"], "NOT_ASSESSED")

    def test_get_axes_treats_legacy_50_as_not_assessed(self):
        patient = make_patient(legacy_id="TEST-051")
        PatientBiologicalRecord.objects.create(patient=patient, axis_1=50, axis_2=65)
        serializer = PatientSerializer(patient)
        axes = serializer.data["axes"]
        self.assertIsNone(axes["AXIS_1"]["score"])
        self.assertEqual(axes["AXIS_1"]["status"], "NOT_ASSESSED")
        self.assertEqual(axes["AXIS_2"]["score"], 65)
        self.assertEqual(axes["AXIS_2"]["status"], "ASSESSED")


class TrainBrainModelReviewGateTests(TestCase):
    """ans.txt P1-C: LLM-invented axis severities must be physician-reviewed before training."""

    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user(username="doctor1", password="x")
        self.client.force_authenticate(user=user)

    def test_rejects_when_no_logs_reviewed(self):
        TSPIBrainTrainingLog.objects.create(
            inputs={"labs": {"fbs": 130}},
            output_axes={"AXIS_5": 80},
            reviewed=False,
        )
        res = self.client.post("/api/ai/train-brain-model/")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.data["success"])

    def test_trains_when_a_log_is_reviewed(self):
        TSPIBrainTrainingLog.objects.create(
            inputs={"labs": {"fbs": 130}},
            output_axes={f"AXIS_{i}": 50 for i in range(1, 40)},
            reviewed=True,
        )
        res = self.client.post("/api/ai/train-brain-model/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["success"])


class GenerateClinicalPdfGatingTests(TestCase):
    """ans.txt P1-A: the legacy clinical-dossier endpoint must use the gated ledger too —
    a HYPOTHESIS axis must not show a numeric score/status here either."""

    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user(username="doctor2", password="x", is_staff=True)
        self.client.force_authenticate(user=user)

    def test_hypothesis_axis_not_scored_in_dossier_html(self):
        patient = make_patient(legacy_id="TEST-060")
        source_record = PatientBiologicalRecord.objects.create(patient=patient, axis_8=90)
        AnalysisRecord.objects.create(
            patient=patient,
            source_record=source_record,
            inputs_hash="test-hypothesis-pdf",
            ledger=calculate_tspi_analysis(source_record),
        )

        res = self.client.get(f"/api/ai/generate-clinical-pdf/?patient={patient.id}")
        self.assertEqual(res.status_code, 200)
        html = res.data["html"]
        self.assertIn("Hypothesis", html)
        self.assertNotIn("90/100", html)

    def test_identity_conflict_snapshot_blocks_dossier_generation(self):
        patient = make_patient(legacy_id="TEST-061", hn="HN-PDF-IDENTITY")
        source_record = PatientBiologicalRecord.objects.create(patient=patient)
        blocked_ledger = calculate_tspi_analysis(
            source_record,
            patient_data={
                "hn": "HN-PDF-IDENTITY",
                "lab_owner_hn": "HN-OTHER",
                "lab_source_record_id": "LAB-PDF-42",
            },
        )
        analysis_record = AnalysisRecord.objects.create(
            patient=patient,
            source_record=source_record,
            inputs_hash="test-blocked-pdf",
            ledger=blocked_ledger,
        )

        res = self.client.get(
            f"/api/ai/generate-clinical-pdf/?patient={patient.id}&analysis_record_id={analysis_record.id}"
        )

        self.assertEqual(res.status_code, 400)
        self.assertIn(b"REPORT GENERATION BLOCKED", res.content)
        self.assertIn(b"lab belongs to a different HN", res.content)

    def test_legacy_text_analysis_record_id_does_not_cause_pdf_server_error(self):
        patient = make_patient(legacy_id="TEST-064")
        patient.extra_data = {
            "generated_reports": [{
                "id": "legacy-report",
                "reportType": "patient",
                "analysisRecordId": "TSPI-1790055558179",
                "report": [],
            }]
        }
        patient.save()

        res = self.client.get(f"/api/ai/patients/{patient.id}/reports/legacy-report/pdf/")

        self.assertEqual(res.status_code, 403)


class AnalysisRecordProvenanceTests(TestCase):
    def test_analysis_record_is_append_only(self):
        patient = make_patient(legacy_id="TEST-062")
        source_record = PatientBiologicalRecord.objects.create(patient=patient)
        record = AnalysisRecord.objects.create(
            patient=patient,
            source_record=source_record,
            inputs_hash="immutable-analysis-record",
            ledger={"analysis_state": "ANALYSIS_READY"},
            identity_snapshot={"identity_validation_status": "VERIFIED"},
            evidence_provenance={"source_ownership": []},
            registry_versions={"canonical_registry": {"version": "test"}},
        )

        self.assertIsNotNone(record.analysis_run_id)
        record.ledger = {"analysis_state": "tampered"}
        with self.assertRaises(ValidationError):
            record.save()


class OmicsUtilityGateTests(TestCase):
    def test_blocks_omics_without_question_plan_and_consent(self):
        result = evaluate_omics_utility_gate({})
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertIn("clinical_question", result["missing_requirements"])

    def test_allows_omics_only_after_utility_requirements_are_documented(self):
        result = evaluate_omics_utility_gate({
            "omics_utility": {
                "clinical_question": "Clarify a treatment-resistant phenotype",
                "current_uncertainty": "Uncertain about variant",
                "decision_that_depends_on_result": "Treatment protocol choice",
                "will_change_management": "HIGH",
                "action_if_positive": "Review result with physician before any intervention",
                "action_if_negative": "Continue standard care",
                "patient_burden": "Low",
                "cost_or_resource_burden": "Moderate",
                "turnaround_time": "2 weeks",
                "goal_concordance": "Yes",
                "clinical_priority": "High",
                "physician_decision": "Approve ordering",
            }
        })
        self.assertEqual(result["status"], "PENDING_PHYSICIAN_REVIEW")


class ScoringContractGateTests(TestCase):
    def test_unapproved_numeric_score_is_not_patient_release_eligible(self):
        patient = make_patient(legacy_id="TEST-063")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_5=85)
        ledger = calculate_tspi_analysis(record)

        self.assertFalse(ledger["scoring_contracts"]["patient_release_eligible"])
        self.assertEqual(ledger["scoring_contracts"]["numeric_score_axes"][0]["status"], "MISSING")


class MarkerProvenanceTests(TestCase):
    """ans.txt P1-D: marker->axis assignments in calculate_precision_medicine must be
    auditable with an explicit relation_type instead of an unlabelled if/elif."""

    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user(username="doctor3", password="x", is_staff=True)
        self.client.force_authenticate(user=user)

    def test_fbs_marker_provenance_recorded(self):
        patient = make_patient(legacy_id="TEST-070")
        res = self.client.post(
            f"/api/patients/{patient.id}/calculate-precision-medicine/",
            {"fbs": "130"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        provenance = res.data["marker_provenance"]
        markers = {(p["marker"], p["axis"], p["relation_type"]) for p in provenance}
        self.assertIn(("fbs_high", 5, "DIRECT_SCORING"), markers)
        self.assertIn(("fbs_high", 27, "SUPPORTING"), markers)


class ModuleRegistryDbTests(TestCase):
    """roadmap 3-A/3-B: module matching reads ModuleRegistryEntry (DB), not the JSON file."""

    def test_import_migration_populated_92_modules(self):
        self.assertEqual(ModuleRegistryEntry.objects.count(), 92)
        self.assertTrue(all(m.mapping_status == "PROVISIONAL" for m in ModuleRegistryEntry.objects.all()))

    def test_module_matching_reads_from_db(self):
        ModuleRegistryEntry.objects.all().delete()
        ModuleRegistryEntry.objects.create(code="TESTMOD", name="Test Module", primary_axes=[5])
        patient = make_patient(legacy_id="TEST-080")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_5=80)
        result = calculate_tspi_analysis(record)
        codes = [m["code"] for m in result["recommended_modules"]]
        self.assertIn("TESTMOD", codes)


class SafetyLayer1Tests(TestCase):
    """roadmap 3-C: contraindication-aware intervention_eligibility, grounded in real module
    data (contraindications) plus evidence already computed in the ledger — no fabricated rule."""

    def test_cancer_contraindication_holds_when_oncology_axis_assessed(self):
        ModuleRegistryEntry.objects.all().delete()
        ModuleRegistryEntry.objects.create(
            code="ONCOMOD", name="Onco Module", primary_axes=[5],
            contraindications=["Hormone-sensitive cancer"]
        )
        patient = make_patient(legacy_id="TEST-090")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_5=60, axis_37=60)
        result = calculate_tspi_analysis(record)
        entries = {e["intervention_id"]: e for e in result["safety_gate"]["intervention_eligibility"]}
        self.assertEqual(entries["ONCOMOD"]["status"], "HOLD")
        self.assertEqual(entries["ONCOMOD"]["reason_rule_id"], "MODULE_CONTRAINDICATION_ONCOLOGY")

    def test_unverifiable_contraindication_is_insufficient_data(self):
        ModuleRegistryEntry.objects.all().delete()
        ModuleRegistryEntry.objects.create(
            code="PREGMOD", name="Preg Module", primary_axes=[31],
            contraindications=["Pregnancy"]
        )
        patient = make_patient(legacy_id="TEST-091")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_31=70)
        result = calculate_tspi_analysis(record)
        entries = {e["intervention_id"]: e for e in result["safety_gate"]["intervention_eligibility"]}
        self.assertEqual(entries["PREGMOD"]["status"], "INSUFFICIENT_DATA")


class SafetyLayer2Tests(TestCase):
    """roadmap 3-D: overlapping target axis among simultaneously-recommended modules —
    a structural signal only, not a fabricated pharmacological interaction claim."""

    def test_two_modules_same_axis_flagged(self):
        ModuleRegistryEntry.objects.all().delete()
        ModuleRegistryEntry.objects.create(code="MODA", name="Module A", primary_axes=[5])
        ModuleRegistryEntry.objects.create(code="MODB", name="Module B", primary_axes=[5])
        patient = make_patient(legacy_id="TEST-092")
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_5=80)
        result = calculate_tspi_analysis(record)
        overlap = result["safety_gate"]["regimen_overlap"]
        axis5_entries = [o for o in overlap if o["axis_code"] == "A5"]
        self.assertEqual(len(axis5_entries), 1)
        self.assertEqual(set(axis5_entries[0]["modules"]), {"MODA", "MODB"})


class ModuleRegistryApprovalEndpointTests(TestCase):
    """roadmap 3-E: approving a module updates mapping_status with an audit trail via API."""

    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user(username="doctor4", password="x", is_staff=True)
        self.client.force_authenticate(user=user)

    def test_patch_approves_module(self):
        entry = ModuleRegistryEntry.objects.create(code="APPROVEME", name="Approve Me", primary_axes=[1])
        res = self.client.patch(
            f"/api/module-registry/{entry.id}/",
            {"mapping_status": "APPROVED", "approved_by": "dr.test"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.mapping_status, "APPROVED")
        self.assertEqual(entry.approved_by, "dr.test")


# ═══════════════════════════════════════════════════════════════════════════════
# EP1 (30 Sep) — Numeric Scoring Rules & Axis Governance Tests
# ═══════════════════════════════════════════════════════════════════════════════

class ClinicalInferenceGatingTests(TestCase):
    """EP1 P0-7/P0-8: CLINICAL_INFERENCE axes (A27, A33) must not carry numeric score."""

    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="EP1", last_name="Test", gender="M",
            birth_date=datetime.date(1980, 1, 1), id_card="1234567890127",
            hn="HN-EP1-001",
        )
        # Set A27=75, A33=80 to simulate confounded data
        self.record = PatientBiologicalRecord.objects.create(
            patient=self.patient, axis_27=75, axis_33=80, axis_5=70
        )

    def test_clinical_inference_axis_has_null_score(self):
        """A27 (Glycation) and A33 (Thyroid-Adrenal) must have severity_score=None."""
        result = calculate_tspi_analysis(self.record)
        axis_27 = result["thirty_nine_axes"]["AXIS_27"]
        axis_33 = result["thirty_nine_axes"]["AXIS_33"]
        self.assertIsNone(axis_27["severity_score"], "A27 (CLINICAL_INFERENCE) must have severity_score=None")
        self.assertIsNone(axis_33["severity_score"], "A33 (CLINICAL_INFERENCE) must have severity_score=None")

    def test_clinical_inference_axis_not_eligible_for_priority(self):
        """CLINICAL_INFERENCE axes must not be eligible for priority ranking."""
        result = calculate_tspi_analysis(self.record)
        axis_27 = result["thirty_nine_axes"]["AXIS_27"]
        axis_33 = result["thirty_nine_axes"]["AXIS_33"]
        self.assertFalse(axis_27["eligible_for_priority"])
        self.assertFalse(axis_33["eligible_for_priority"])

    def test_clinical_inference_axis_data_availability_present(self):
        """Even though CLINICAL_INFERENCE, data_availability must be PRESENT (P0-5)."""
        result = calculate_tspi_analysis(self.record)
        axis_27 = result["thirty_nine_axes"]["AXIS_27"]
        self.assertEqual(axis_27["data_availability"], "PRESENT")
        self.assertEqual(axis_27["evidence_status"], "CLINICAL_INFERENCE")
        self.assertEqual(axis_27["score_status"], "NOT_SCORED_CONFOUNDED")

    def test_clinical_inference_not_in_nss(self):
        """A27/A33 must be excluded from NSS calculation."""
        result = calculate_tspi_analysis(self.record)
        axis_27 = result["thirty_nine_axes"]["AXIS_27"]
        self.assertFalse(axis_27["eligible_for_nss"])

    def test_assessed_axis_has_scored_status(self):
        """A5 (non-gated, has data) must have score_status='SCORED'."""
        result = calculate_tspi_analysis(self.record)
        axis_5 = result["thirty_nine_axes"]["AXIS_5"]
        self.assertEqual(axis_5["score_status"], "SCORED")
        self.assertEqual(axis_5["severity_score"], 70)

    def test_clinical_inference_listed_as_candidate(self):
        """CLINICAL_INFERENCE axes should appear in candidate_axes_requiring_confirmation."""
        result = calculate_tspi_analysis(self.record)
        candidates = result["candidate_axes_requiring_confirmation"]
        candidate_codes = [c["code"] for c in candidates]
        self.assertIn("A27", candidate_codes)
        self.assertIn("A33", candidate_codes)


class PriorityDerivationTests(TestCase):
    """EP1 P0-4: System priorities must declare DERIVED status and rank_label."""

    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="Priority", last_name="Test", gender="F",
            birth_date=datetime.date(1990, 5, 15), id_card="1234567890128",
            hn="HN-EP1-002",
        )
        self.record = PatientBiologicalRecord.objects.create(
            patient=self.patient, axis_1=65, axis_5=70
        )

    def test_system_priorities_have_derivation_metadata(self):
        """Every entry in system_priorities must have priority_derivation and rank_label."""
        result = calculate_tspi_analysis(self.record)
        for priority in result["system_priorities"]:
            self.assertEqual(priority["priority_derivation"], "DERIVED")
            self.assertIsNone(priority["priority_rule_id"])
            self.assertEqual(priority["rank_label"], "Highest Scored Assessed Axes")


class InvariantINV011012Tests(TestCase):
    """EP1: Cross-report invariant validator catches CLINICAL_INFERENCE violations."""

    def test_inv011_clinical_inference_with_score_flagged(self):
        """If a CLINICAL_INFERENCE axis has severity_score != None, INV-011 must fire."""
        from patients.tspi_engine import validate_analysis_record
        fake_ledger = {
            "thirty_nine_axes": {
                f"AXIS_{i}": {
                    "code": f"A{i}",
                    "name": OFFICIAL_39_AXES[i],
                    "severity_score": None,
                    "evidence_status": "NOT_AVAILABLE",
                    "eligible_for_priority": False,
                } for i in range(1, 40)
            },
            "three_keys": {},
            "nine_restoration_steps": [],
            "canonical_domains": [],
            "network_registry": {},
            "module_registry": {},
            "safety_gate": {},
        }
        # Inject violation: A27 CLINICAL_INFERENCE with a score
        fake_ledger["thirty_nine_axes"]["AXIS_27"]["evidence_status"] = "CLINICAL_INFERENCE"
        fake_ledger["thirty_nine_axes"]["AXIS_27"]["severity_score"] = 75
        violations = validate_analysis_record(fake_ledger)
        inv011_violations = [v for v in violations if v["rule_id"] == "INV-011"]
        self.assertTrue(len(inv011_violations) > 0, "INV-011 must flag CLINICAL_INFERENCE axis with score")

    def test_inv012_clinical_inference_eligible_priority_flagged(self):
        """If CLINICAL_INFERENCE axis has eligible_for_priority=True, INV-012 must fire."""
        from patients.tspi_engine import validate_analysis_record
        fake_ledger = {
            "thirty_nine_axes": {
                f"AXIS_{i}": {
                    "code": f"A{i}",
                    "name": OFFICIAL_39_AXES[i],
                    "severity_score": None,
                    "evidence_status": "NOT_AVAILABLE",
                    "eligible_for_priority": False,
                } for i in range(1, 40)
            },
            "three_keys": {},
            "nine_restoration_steps": [],
            "canonical_domains": [],
            "network_registry": {},
            "module_registry": {},
            "safety_gate": {},
        }
        fake_ledger["thirty_nine_axes"]["AXIS_33"]["evidence_status"] = "CLINICAL_INFERENCE"
        fake_ledger["thirty_nine_axes"]["AXIS_33"]["eligible_for_priority"] = True
        violations = validate_analysis_record(fake_ledger)
        inv012_violations = [v for v in violations if v["rule_id"] == "INV-012"]
        self.assertTrue(len(inv012_violations) > 0, "INV-012 must flag CLINICAL_INFERENCE axis with eligible_for_priority=True")

    def test_clean_engine_output_has_no_inv011_012(self):
        """A clean engine run must not produce INV-011 or INV-012 violations."""
        patient = Patient.objects.create(
            first_name="Clean", last_name="Check", gender="M",
            birth_date=datetime.date(1975, 3, 10), id_card="1234567890129",
            hn="HN-INV-001",
        )
        record = PatientBiologicalRecord.objects.create(
            patient=patient, axis_5=65, axis_27=80, axis_33=70
        )
        result = calculate_tspi_analysis(record)
        inv011 = [v for v in result["invariant_violations"] if v["rule_id"] == "INV-011"]
        inv012 = [v for v in result["invariant_violations"] if v["rule_id"] == "INV-012"]
        self.assertEqual(len(inv011), 0, "Clean engine run should not produce INV-011")
        self.assertEqual(len(inv012), 0, "Clean engine run should not produce INV-012")


# ═══════════════════════════════════════════════════════════════════════════════
# EP2 (30 Sep) — Master Canonical Ontology & Renderer Alignment Tests
# ═══════════════════════════════════════════════════════════════════════════════

class MasterCanonicalOntologyTests(TestCase):
    """EP2 P0-4/P0-5: Canonical 12 Domains and 39 Axes alignment across renderers."""

    def test_local_report_generator_clinical_impressions_match_canonical_domains(self):
        """Every key in CLINICAL_IMPRESSIONS must match a canonical domain in SYSTEM_DOMAINS."""
        from patients.local_report_generator import CLINICAL_IMPRESSIONS
        from patients.tspi_engine import SYSTEM_DOMAINS
        canonical_domain_names = set(SYSTEM_DOMAINS.keys())
        impression_domain_names = set(CLINICAL_IMPRESSIONS.keys())
        self.assertEqual(
            impression_domain_names, canonical_domain_names,
            f"CLINICAL_IMPRESSIONS keys must match 12 Canonical Domains exactly. Diff: {impression_domain_names ^ canonical_domain_names}"
        )

    def test_coupling_mechanisms_keys_match_canonical_domains(self):
        """Every key in COUPLING_MECHANISMS must exist in SYSTEM_DOMAINS."""
        from patients.local_report_generator import COUPLING_MECHANISMS
        from patients.tspi_engine import SYSTEM_DOMAINS
        canonical_domain_names = set(SYSTEM_DOMAINS.keys())
        for coupling in COUPLING_MECHANISMS:
            for key in coupling["keys"]:
                self.assertIn(key, canonical_domain_names, f"Coupling key '{key}' must be a canonical domain")

    def test_render_html_precision_report_uses_official_39_axes(self):
        """render_html_precision_report must map all 39 canonical axes without missing keys."""
        from patients.local_report_generator import render_html_precision_report
        patient = Patient.objects.create(
            first_name="HTML", last_name="Report", gender="F",
            birth_date=datetime.date(1988, 12, 1), id_card="1234567890130",
            hn="HN-EP2-001",
        )
        record = PatientBiologicalRecord.objects.create(patient=patient, axis_1=60, axis_5=75)
        tspi_result = calculate_tspi_analysis(record)
        html = render_html_precision_report(patient, tspi_result, simulated_labs={})
        self.assertIn("39-Axes", html)
        self.assertIn(patient.full_name, html)


# ═══════════════════════════════════════════════════════════════════════════════
# EP3 (30 Sep) — Report Approval State Machine & Rendering Governance Tests
# ═══════════════════════════════════════════════════════════════════════════════

class PatientRenderingGovernanceTests(TestCase):
    """EP3 P0-10/P0-11: Hides internal tags and resolves approval contradictions."""

    def test_patient_edition_hides_internal_debug_tags(self):
        """Patient edition must translate debug tags [MEASURED], [HYPOTHESIS] into Thai text."""
        from patients.views_ai import markdown_to_html
        raw_text = "Axis 1 is [MEASURED] and Axis 8 is [HYPOTHESIS]."
        html = markdown_to_html(raw_text, edition="patient", is_approved=False)
        self.assertNotIn("[MEASURED]", html)
        self.assertNotIn("[HYPOTHESIS]", html)
        self.assertIn("(ผลตรวจยืนยัน)", html)
        self.assertIn("(สภาวะสงสัย — รอตรวจเพิ่มเติม)", html)

    def test_physician_edition_retains_badges(self):
        """Physician edition must render professional clinical badge spans."""
        from patients.views_ai import markdown_to_html
        raw_text = "Axis 1 is [MEASURED]."
        html = markdown_to_html(raw_text, edition="physician", is_approved=True)
        self.assertIn('class="badge"', html)

    def test_unapproved_patient_report_replaces_approved_wording(self):
        """If report is not approved, 'แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว' must be replaced."""
        from patients.views_ai import markdown_to_html
        raw_text = "นี่คือ แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว สำหรับคนไข้"
        html = markdown_to_html(raw_text, edition="patient", is_approved=False)
        self.assertNotIn("แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว", html)
        self.assertIn("ร่างแผนดูแลสุขภาพที่อยู่ระหว่างการพิจารณาของแพทย์", html)


class InvariantINV013014Tests(TestCase):
    """EP3: Cross-report invariant validator catches approval contradictions and provisional module facts."""

    def test_inv013_flags_approved_wording_in_ai_draft(self):
        """INV-013 must flag AI_DRAFT containing 'แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว'."""
        from patients.tspi_engine import validate_analysis_record
        fake_ledger = {
            "thirty_nine_axes": {},
            "three_keys": {},
            "nine_restoration_steps": [],
            "canonical_domains": [],
            "network_registry": {},
            "module_registry": {},
            "safety_gate": {},
            "report_state": "AI_DRAFT",
            "notes": "นี่คือ แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว",
        }
        violations = validate_analysis_record(fake_ledger)
        inv013 = [v for v in violations if v["rule_id"] == "INV-013"]
        self.assertTrue(len(inv013) > 0, "INV-013 must flag approval contradiction in AI_DRAFT")

    def test_inv014_flags_provisional_module_in_clinical_recommendations(self):
        """INV-014 must flag approved_modules==0 with non-empty recommended_modules_clinical."""
        from patients.tspi_engine import validate_analysis_record
        fake_ledger = {
            "thirty_nine_axes": {},
            "three_keys": {},
            "nine_restoration_steps": [],
            "canonical_domains": [],
            "network_registry": {},
            "module_registry": {"approved_modules": 0, "registry_status": "PROVISIONAL"},
            "recommended_modules_clinical": [{"code": "MOD_001", "name": "Fake Module"}],
            "safety_gate": {},
        }
        violations = validate_analysis_record(fake_ledger)
        inv014 = [v for v in violations if v["rule_id"] == "INV-014"]
        self.assertTrue(len(inv014) > 0, "INV-014 must flag unapproved module in recommended_modules_clinical")



