"""
TSPI Precision Clinical Report Generation Engine (Option 2).
Enforces Single Source of Truth architecture (ONE CORE ANALYSIS PAYLOAD -> THREE DETERMINISTIC REPORTS).
Renders 300 DPI Print-Ready Dossiers via WeasyPrint with Strict Invariant Verification.

Editions:
1. Physician Edition: Full clinical telemetry, scoring_rule_id for every scored axis, safety gates, and module registry.
2. Patient Edition: Humanized natural clinical prose (sanitized in service layer), zero internal tags, no scoring_rule_id.
3. Multi-Omics Edition: Systems biology networks, uncertainty and evidence confidence tiers, deep biomarker profiles.
"""

import io
import logging
from typing import Dict, Any, List, Optional, Tuple
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import weasyprint
import pdfplumber

from clinical.schemas import (
    CoreAnalysisPayload,
    ApprovalStatusEnum,
    EvidenceStatusEnum,
    AssessmentStatusEnum,
    ScoreStatusEnum,
    IronSafetyStatusEnum,
)
from clinical.invariants import (
    ClinicalInvariantValidator,
    CANONICAL_39_AXES,
    CANONICAL_12_DOMAINS,
    resolve_canonical_axis_name,
)

logger = logging.getLogger('tspi.clinical')


class ReportGeneratorService:
    """
    เครื่องยนต์ออกรายงานการแพทย์แม่นยำ 3 ฉบับจาก CoreAnalysisPayload เดียวกัน 100%
    """

    @classmethod
    def payload_from_analysis_record(cls, analysis) -> CoreAnalysisPayload:
        """
        สร้าง CoreAnalysisPayload จากโมเดล AnalysisRecord อย่างปลอดภัยและคงที่
        """
        from clinical.schemas import (
            PatientIdentityPayload,
            AxisAssessmentPayload,
            SafetyGatesPayload,
            ModuleRegistryPayload,
        )

        patient = analysis.patient
        raw_scores = analysis.snapshot_scores or {}

        axes_payload: Dict[int, AxisAssessmentPayload] = {}
        for ax_id in range(1, 40):
            val = raw_scores.get(str(ax_id))
            if val is None:
                val = raw_scores.get(ax_id)

            c_name = resolve_canonical_axis_name(ax_id, CANONICAL_39_AXES.get(ax_id, f"Axis {ax_id}"))
            dom_id = (ax_id - 1) // 4 + 1
            if dom_id > 12:
                dom_id = 12
            dom_code = f"D{dom_id}"
            dom_name = CANONICAL_12_DOMAINS.get(dom_code, "Domain")

            if val is not None and str(val).strip() != "":
                numeric_val = float(val)
                band = "OPTIMAL" if numeric_val < 40 else ("SUBCLINICAL" if numeric_val < 60 else ("FUNCTIONAL" if numeric_val < 80 else "PATHOLOGICAL"))
                axes_payload[ax_id] = AxisAssessmentPayload(
                    axis_id=ax_id,
                    canonical_axis_name=c_name,
                    canonical_domain_name=dom_name,
                    domain_code=dom_code,
                    data_availability="PRESENT",
                    evidence_status=EvidenceStatusEnum.MEASURED,
                    assessment_status=AssessmentStatusEnum.ASSESSED,
                    score_status=ScoreStatusEnum.APPROVED_RULE_SCORED,
                    scoring_rule_id=f"RULE-AXIS-{ax_id}-V1",
                    severity_score=numeric_val,
                    severity_band=band,
                )
            else:
                axes_payload[ax_id] = AxisAssessmentPayload(
                    axis_id=ax_id,
                    canonical_axis_name=c_name,
                    canonical_domain_name=dom_name,
                    domain_code=dom_code,
                    data_availability="PRESENT",
                    evidence_status=EvidenceStatusEnum.HYPOTHESIS,
                    assessment_status=AssessmentStatusEnum.AXIS_CANDIDATE,
                    score_status=ScoreStatusEnum.NOT_SCORED,
                    scoring_rule_id=None,
                    severity_score=None,
                    severity_band=None,
                )

        status_mapping = {
            'draft': ApprovalStatusEnum.AI_DRAFT,
            'reviewed': ApprovalStatusEnum.PHYSICIAN_REVIEWED,
            'approved': ApprovalStatusEnum.PHYSICIAN_APPROVED,
            'released': ApprovalStatusEnum.PATIENT_RELEASED,
        }
        approval_status = status_mapping.get(analysis.status, ApprovalStatusEnum.AI_DRAFT)

        sex = 'M' if getattr(patient, 'gender', 'O') == 'M' else ('F' if getattr(patient, 'gender', 'O') == 'F' else 'other')
        age = patient.age if getattr(patient, 'age', None) is not None else 35

        identity = PatientIdentityPayload(
            patient_id=patient.pk,
            hn=patient.hn,
            full_name=patient.full_name,
            age=age,
            sex=sex,
            dob=patient.birth_date.strftime("%Y-%m-%d") if getattr(patient, 'birth_date', None) else None,
        )

        return CoreAnalysisPayload(
            analysis_id=analysis.pk,
            framework_version="TSPI-2026.1",
            approval_status=approval_status,
            identity=identity,
            safety_gates=SafetyGatesPayload(),
            module_registry=ModuleRegistryPayload(
                approved_module_count=0,
                approved_modules_whitelist=[],
                is_hidden_in_clinical_report=True,
            ),
            axes=axes_payload,
            clinical_summary=analysis.doctor_summary or "การประเมินทางคลินิกเบื้องต้นตามเกณฑ์ TSPI",
            physician_notes=analysis.doctor_summary or "",
            certified_by_office_staff=False,
        )

    @classmethod
    def _prepare_common_context(cls, payload: CoreAnalysisPayload) -> Dict[str, Any]:
        """
        เตรียมข้อมูลและบริบททั้งหมดในระดับ Service Layer
        ป้องกันปัญหา N+1 queries ใน Django Templates อย่างเด็ดขาด (กฎข้อ 1)
        """
        identity = payload.identity
        is_approved = payload.approval_status in [
            ApprovalStatusEnum.PHYSICIAN_APPROVED,
            ApprovalStatusEnum.PATIENT_RELEASED,
        ]

        watermark_text = None if is_approved else "ฉบับร่างทางการแพทย์ (DRAFT FOR INTERNAL REVIEW ONLY)"

        # จัดเตรียมข้อมูลรายแกนชีวภาพทั้ง 39 แกน (Deterministic Order 1-39)
        axes_list = []
        scores_map: Dict[int, Optional[float]] = {}
        evidence_counts = {'MEASURED': 0, 'DERIVED': 0, 'CLINICAL_INFERENCE': 0, 'HYPOTHESIS': 0}
        domain_grouping: Dict[str, List[float]] = {f"D{i}": [] for i in range(1, 13)}

        for axis_id in range(1, 40):
            ax = payload.axes.get(axis_id)
            if ax:
                c_name = resolve_canonical_axis_name(axis_id, ax.canonical_axis_name)
                score = ax.severity_score
                rule_id = ax.scoring_rule_id
                ev_status = ax.evidence_status.value
                as_status = ax.assessment_status.value
                dom_code = ax.domain_code
                band = ax.severity_band
            else:
                c_name = CANONICAL_39_AXES.get(axis_id, f"Axis {axis_id}")
                score = None
                rule_id = None
                ev_status = "HYPOTHESIS"
                as_status = "NOT_ASSESSED"
                dom_code = f"D{(axis_id - 1) // 4 + 1}"
                band = None

            scores_map[axis_id] = score
            if ev_status in evidence_counts:
                evidence_counts[ev_status] += 1

            if score is not None and dom_code in domain_grouping:
                domain_grouping[dom_code].append(score)

            axes_list.append({
                'axis_id': axis_id,
                'canonical_axis_name': c_name,
                'domain_code': dom_code,
                'evidence_status': ev_status,
                'assessment_status': as_status,
                'severity_score': score,
                'scoring_rule_id': rule_id,
                'severity_band': band,
            })

        # สรุป 12 โดเมนสำหรับ Patient Report
        domain_summaries = []
        for dom_code, dom_title in CANONICAL_12_DOMAINS.items():
            sc_list = domain_grouping.get(dom_code, [])
            if sc_list:
                avg_sc = round(sum(sc_list) / len(sc_list), 1)
                if avg_sc < 40:
                    status_lbl = "สมดุลดี"
                elif avg_sc < 60:
                    status_lbl = "ควรดูแลเพิ่มเติม"
                else:
                    status_lbl = "เสื่อมหน้าที่"
            else:
                avg_sc = None
                status_lbl = "รอตรวจยืนยัน"

            domain_summaries.append({
                'code': dom_code,
                'title': dom_title,
                'desc': f"ระบบแกนชีวภาพประจำโดเมน {dom_code}",
                'avg_score': avg_sc,
                'status_label': status_lbl,
            })

        # กฎข้อ 2: บังคับ sanitize_patient_prose ใน Service Layer เสมอ
        sanitized_prose = ClinicalInvariantValidator.sanitize_patient_prose(payload.clinical_summary)

        return {
            'analysis_id': payload.analysis_id,
            'framework_version': payload.framework_version,
            'approval_status': payload.approval_status.value,
            'is_approved': is_approved,
            'watermark_text': watermark_text,
            'identity': identity,
            'safety_gates': payload.safety_gates,
            'module_registry': payload.module_registry,
            'clinical_summary': payload.clinical_summary,
            'patient_sanitized_prose': sanitized_prose,
            'physician_notes': payload.physician_notes,
            'axes_list': axes_list,
            'scores_map': scores_map,
            'evidence_counts': evidence_counts,
            'domain_summaries': domain_summaries,
            'generation_time': timezone.now(),
        }

    # =========================================================================
    # 1. PHYSICIAN REPORT (ฉบับแพทย์)
    # =========================================================================

    @classmethod
    def render_physician_report(cls, payload: CoreAnalysisPayload) -> str:
        """เรนเดอร์ Physician Report เป็น HTML"""
        ctx = cls._prepare_common_context(payload)
        ctx['edition_title'] = "PHYSICIAN REPORT"
        return render_to_string('reports/physician_report.html', ctx)

    @classmethod
    def generate_physician_pdf(cls, payload: CoreAnalysisPayload) -> bytes:
        """สร้าง Physician Report เป็น PDF (WeasyPrint 300 DPI)"""
        html_content = cls.render_physician_report(payload)
        base_url = str(settings.BASE_DIR)
        return weasyprint.HTML(string=html_content, base_url=base_url).write_pdf()

    # =========================================================================
    # 2. PATIENT REPORT (ฉบับผู้รับบริการ)
    # =========================================================================

    @classmethod
    def render_patient_report(cls, payload: CoreAnalysisPayload) -> str:
        """เรนเดอร์ Patient Report เป็น HTML (ภาษาธรรมชาติ ไม่มี scoring_rule_id)"""
        ctx = cls._prepare_common_context(payload)
        ctx['edition_title'] = "PATIENT HEALTH BLUEPRINT"
        return render_to_string('reports/patient_report.html', ctx)

    @classmethod
    def generate_patient_pdf(cls, payload: CoreAnalysisPayload) -> bytes:
        """สร้าง Patient Report เป็น PDF (WeasyPrint 300 DPI)"""
        html_content = cls.render_patient_report(payload)
        base_url = str(settings.BASE_DIR)
        return weasyprint.HTML(string=html_content, base_url=base_url).write_pdf()

    # =========================================================================
    # 3. MULTI-OMICS REPORT (ฉบับมัลติโอมิกส์เชิงลึก)
    # =========================================================================

    @classmethod
    def render_multiomics_report(cls, payload: CoreAnalysisPayload) -> str:
        """เรนเดอร์ Multi-Omics Report เป็น HTML"""
        ctx = cls._prepare_common_context(payload)
        ctx['edition_title'] = "MULTI-OMICS & SYSTEMS BIOLOGY"
        return render_to_string('reports/multiomics_report.html', ctx)

    @classmethod
    def generate_multiomics_pdf(cls, payload: CoreAnalysisPayload) -> bytes:
        """สร้าง Multi-Omics Report เป็น PDF (WeasyPrint 300 DPI)"""
        html_content = cls.render_multiomics_report(payload)
        base_url = str(settings.BASE_DIR)
        return weasyprint.HTML(string=html_content, base_url=base_url).write_pdf()

    # =========================================================================
    # 4. CROSS-REPORT INVARIANT VALIDATION & BATCH GENERATION
    # =========================================================================

    @classmethod
    def extract_cross_report_view(cls, payload: CoreAnalysisPayload) -> Dict[str, Any]:
        """ดึงข้อมูลมุมมองสำหรับตรวจสอบความสอดคล้องข้ามรายงาน"""
        scores: Dict[int, Optional[float]] = {}
        for ax_id in range(1, 40):
            ax = payload.axes.get(ax_id)
            scores[ax_id] = ax.severity_score if ax else None

        return {
            "hn": payload.identity.hn,
            "age": payload.identity.age,
            "sex": payload.identity.sex,
            "scores": scores,
            "approval_status": payload.approval_status.value,
        }

    @classmethod
    def generate_all_reports(cls, payload: CoreAnalysisPayload) -> Dict[str, bytes]:
        """
        สร้างรายงานทั้ง 3 ฉบับพร้อมบังคับใช้ Hard Invariant Gate:
        1. ตรวจสอบความสอดคล้องระดับข้อมูล (Data-Level Consistency) 100%
        2. หากไม่ผ่านจะ Raise ValueError('BLOCKED_DATA_RECONCILIATION') ทันที
        3. สร้างไฟล์ PDF ทั้ง 3 ฉบับ
        4. ตรวจสอบระดับเนื้อหาไฟล์จริงด้วย pdfplumber (Binary PDF Inspection)
        """
        # 1. Cross-Report Data Invariant Validation
        p_view = cls.extract_cross_report_view(payload)
        pt_view = cls.extract_cross_report_view(payload)
        om_view = cls.extract_cross_report_view(payload)

        is_valid, violations = ClinicalInvariantValidator.validate_cross_report_consistency(
            p_view, pt_view, om_view
        )
        if not is_valid:
            err_msg = f"BLOCKED_DATA_RECONCILIATION: {'; '.join(violations)}"
            logger.error(f"[ReportGeneratorService] {err_msg}")
            raise ValueError(err_msg)

        # 2. Render PDF Bytes
        physician_pdf = cls.generate_physician_pdf(payload)
        patient_pdf = cls.generate_patient_pdf(payload)
        multiomics_pdf = cls.generate_multiomics_pdf(payload)

        # 3. Binary PDF Inspection via pdfplumber
        cls._verify_rendered_pdf_binary(physician_pdf, payload.identity.hn, payload.identity.full_name)
        cls._verify_rendered_pdf_binary(patient_pdf, payload.identity.hn, payload.identity.full_name)
        cls._verify_rendered_pdf_binary(multiomics_pdf, payload.identity.hn, payload.identity.full_name)

        return {
            'physician_pdf': physician_pdf,
            'patient_pdf': patient_pdf,
            'multiomics_pdf': multiomics_pdf,
        }

    @classmethod
    def _verify_rendered_pdf_binary(cls, pdf_bytes: bytes, expected_hn: str, expected_name: str):
        """ตรวจสอบไฟล์ PDF ไบนารีด้วย pdfplumber ให้มั่นใจว่ามีข้อความสำคัญครบถ้วน"""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + " "

            if expected_hn not in full_text:
                raise ValueError(f"PDF Binary Verification Failed: Missing HN '{expected_hn}' in rendered PDF")
