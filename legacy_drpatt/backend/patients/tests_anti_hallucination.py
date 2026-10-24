import datetime
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from patients.models import Patient, PatientBiologicalRecord, AnalysisRecord, AxisScoringContract
from patients.tspi_engine import calculate_tspi_analysis
from patients.output_validator import ClinicalOutputValidator, REFUSAL_STATES
from patients.views_ai import markdown_to_html


class AntiHallucinationArchitectureTests(TestCase):
    """
    Anti-Hallucination & AI Scope Control Test Suite
    Verifies that the LLM/Renderer is strictly bounded by ClinicalOutputValidator
    and cannot invent clinical claims, scores, or unsupported recommendations.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(username="drpatt_antihallucination", email="dr@test.com", password="password")
        self.client.force_authenticate(user=self.user)
        self.patient = Patient.objects.create(
            first_name="AntiHallucination", last_name="Test", gender="F",
            birth_date=datetime.date(1992, 8, 15), id_card="1234567890888",
            hn="HN-AH-001"
        )
        self.record = PatientBiologicalRecord.objects.create(
            patient=self.patient, axis_1=65, axis_5=70, axis_27=80, axis_33=75
        )
        self.ledger = calculate_tspi_analysis(self.record)
        self.analysis = AnalysisRecord.objects.create(
            patient=self.patient,
            source_record=self.record,
            inputs_hash="ah-test-hash",
            ledger=self.ledger,
        )

    def test_output_validator_rejects_fabricated_axis_entity(self):
        """Directive 6: Validator must REJECT text containing fabricated axis entities (e.g. Axis 40)."""
        hallucinated_text = "จากการวิเคราะห์พบว่า Axis 40 มีคะแนนความรุนแรง 85% ต้องได้รับการฟื้นฟู"
        res = ClinicalOutputValidator.validate(hallucinated_text, self.ledger)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["refusal_state"], "BLOCKED_BY_POLICY")
        self.assertIn("TSPI Safety Policy", res["sanitized_text"])

    def test_output_validator_sanitizes_unassessed_axis_score_claim(self):
        """Directive 6/7: Validator sanitizes text that assigns numeric scores to un-assessed/confounded axes."""
        # A14 is not scored (severity_score = None)
        hallucinated_text = "แกนที่ 14 มีคะแนนความรุนแรง 75% ซึ่งเป็นระดับ pathological"
        res = ClinicalOutputValidator.validate(hallucinated_text, self.ledger)
        self.assertNotIn("75%", res["sanitized_text"])
        self.assertIn("ยังไม่ได้ประเมินคะแนน", res["sanitized_text"])

    def test_output_validator_sanitizes_unapproved_module_prescriptions(self):
        """Directive 6/16: Validator sanitizes module prescriptions when approved_modules == 0."""
        hallucinated_text = "แนะนำให้รับประทานสมุนไพร สูตรสมุนไพรบำบัดเฉพาะทาง Module MOD_001 ทุกวัน"
        res = ClinicalOutputValidator.validate(hallucinated_text, self.ledger)
        self.assertNotIn("Module MOD_001", res["sanitized_text"])
        self.assertIn("อยู่ระหว่างการพิจารณาอนุมัติโดยแพทย์", res["sanitized_text"])

    def test_output_validator_sanitizes_absolute_dietary_iron_ban(self):
        """Directive 16: Validator replaces absolute dietary iron bans with supplement-specific hold."""
        hallucinated_text = "ตรวจพบภาวะสงสัยแฝงธาลัสซีเมีย ห้ามรับประทานเนื้อแดงและอาหารที่มีธาตุเหล็กเด็ดขาด"
        res = ClinicalOutputValidator.validate(hallucinated_text, self.ledger)
        self.assertNotIn("ห้ามรับประทานเนื้อแดง", res["sanitized_text"])
        self.assertIn("ยังไม่ควรเริ่มอาหารเสริมธาตุเหล็กเอง", res["sanitized_text"])

    def test_output_validator_corrects_approval_contradiction_in_draft(self):
        """Directive 11: Validator replaces approval claims in draft state."""
        draft_text = "เอกสารนี้คือ แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว สำหรับคนไข้"
        res = ClinicalOutputValidator.validate(draft_text, self.ledger, edition="patient", is_approved=False)
        self.assertNotIn("แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว", res["sanitized_text"])
        self.assertIn("ร่างแผนดูแลสุขภาพที่อยู่ระหว่างการพิจารณาของแพทย์", res["sanitized_text"])

    def test_markdown_to_html_integrates_output_validator(self):
        """Directive 14: markdown_to_html must automatically run ClinicalOutputValidator."""
        text_with_tag = "Axis 1 is [MEASURED] and Axis 8 is [HYPOTHESIS]."
        html = markdown_to_html(text_with_tag, edition="patient", is_approved=False, ledger=self.ledger)
        self.assertNotIn("[MEASURED]", html)
        self.assertNotIn("[HYPOTHESIS]", html)
        self.assertIn("(ผลตรวจยืนยัน)", html)

    def test_missing_data_remains_not_assessed_never_guessed_normal(self):
        """Directive 7: Missing evidence remains NOT_ASSESSED / null and is never imputed as Normal or 0."""
        axis_14 = self.ledger["thirty_nine_axes"]["AXIS_14"]
        self.assertIsNone(axis_14["severity_score"])
        self.assertIn(axis_14["score_status"], ("NOT_SCORED_NO_DATA", "NO_APPROVED_SCORING_RULE"))
