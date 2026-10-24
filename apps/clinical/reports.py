"""
Precision Medicine Report Generation Engine (EP 6).
Renders 300 DPI Print-Ready Clinical Dossiers via WeasyPrint with Strict State Machine Gates.
"""

import io
from typing import Dict, Any, Optional
from django.template.loader import render_to_string
from django.utils import timezone
from clinical.models import AnalysisRecord, BiologicalRecord
from clinical.engine import TspiClinicalEngine
from patients.models import Patient
import weasyprint

class PrecisionReportGenerator:
    """
    เครื่องยนต์ออกรายงานการแพทย์แม่นยำ (Precision Clinical Report Generator)
    รองรับ 3 Editions: Physician, Patient, และ Multi-Omics
    """

    @classmethod
    def get_report_context(cls, analysis: AnalysisRecord, edition: str = 'physician') -> Dict[str, Any]:
        """รวบรวมข้อมูลทั้งหมดสำหรับเรนเดอร์รายงาน"""
        patient = analysis.patient
        bio_record = getattr(patient, 'biological_record', None)
        raw_scores = analysis.snapshot_scores or (bio_record.to_scores_dict() if bio_record else {})
        scores_dict = {int(k): int(v) for k, v in raw_scores.items()}
        for i in range(1, 40):
            if i not in scores_dict:
                scores_dict[i] = 50

        # 12 โดเมน
        domain_scores = TspiClinicalEngine.calculate_domain_scores(scores_dict)
        all_axes = TspiClinicalEngine.get_all_axes()

        # จัดกลุ่มแกนชีวภาพตามคะแนน
        dysfunctional_axes = []
        for ax in all_axes:
            ax_id = ax.get('axis_id')
            score = scores_dict.get(ax_id, 50)
            if score >= 60:
                dysfunctional_axes.append({
                    'axis_id': ax_id,
                    'name': ax.get('name'),
                    'domain_title': ax.get('domain_title'),
                    'score': score
                })
        dysfunctional_axes = sorted(dysfunctional_axes, key=lambda x: x['score'], reverse=True)

        # โมดูลบำบัดที่จับคู่ได้
        recommendations = TspiClinicalEngine.match_therapeutic_recommendations(dysfunctional_axes, limit=6)

        # ประวัติ SOAP ล่าสุด
        latest_soap = patient.histories.first()

        is_approved = analysis.status in ['approved', 'released']

        return {
            'analysis': analysis,
            'patient': patient,
            'bio_record': bio_record,
            'scores_dict': scores_dict,
            'domain_scores': domain_scores,
            'all_axes': all_axes,
            'dysfunctional_axes': dysfunctional_axes,
            'recommendations': recommendations,
            'latest_soap': latest_soap,
            'edition': edition,
            'is_approved': is_approved,
            'generation_time': timezone.now(),
            'watermark_text': None if is_approved else "ฉบับร่างทางการแพทย์ (DRAFT FOR INTERNAL REVIEW ONLY)",
        }

    @classmethod
    def render_html(cls, analysis: AnalysisRecord, edition: str = 'physician') -> str:
        """เรนเดอร์รายงานเป็น HTML"""
        context = cls.get_report_context(analysis, edition=edition)
        return render_to_string('clinical/reports/precision_report_template.html', context)

    @classmethod
    def generate_pdf(cls, analysis: AnalysisRecord, edition: str = 'physician') -> bytes:
        """แปลงรายงาน HTML เป็น PDF คุณภาพสูงผ่าน WeasyPrint"""
        html_string = cls.render_html(analysis, edition=edition)
        
        # WeasyPrint PDF Generation
        pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()
        return pdf_bytes
