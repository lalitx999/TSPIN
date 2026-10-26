"""
TSPI AI Copilot Context Builder & Guardrails Service (Option 4).
Extracts grounded patient context from the Single Source of Truth,
enforces strict Token Budgets (preventing Token Overflow),
filters out unscored/HYPOTHESIS axes, and formats authoritative clinical prompts.
"""

import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone

from patients.models import Patient
from clinical.models import AnalysisRecord, BiologicalRecord
from clinical.invariants import CANONICAL_39_AXES, CANONICAL_12_DOMAINS

logger = logging.getLogger('tspi.clinical.copilot')


class CopilotContextBuilder:
    """
    คลาสเตรียมบริบท (Context Builder) สำหรับ AI Medical Copilot
    ดึงข้อมูลจากแหล่งความจริงเดียว คัดกรองเฉพาะแกนที่มีคะแนน และจำกัดความยาวเพื่อป้องกัน Token Overflow
    """

    MAX_CONTEXT_CHARACTERS = 3500  # Token Budget Guard (ป้องกัน Context ยาวเกิน)

    @classmethod
    def build_context(cls, patient_id: Optional[int] = None) -> Dict[str, Any]:
        """
        สร้าง Structured Context และ System Prompt ข้อความเต็มสำหรับส่งต่อให้ AI Microservice
        """
        if not patient_id:
            return {
                'patient_hn': None,
                'patient_name': None,
                'has_patient_context': False,
                'context_text': "ไม่มีการระบุตัวตนผู้ป่วย (General Clinical Assistant Mode)",
                'scored_axes_count': 0,
                'safety_alerts': ["ตรวจสอบประวัติการแพ้และค่าตับไตก่อนสั่งการรักษา"],
            }

        patient = Patient.objects.filter(pk=patient_id, is_deleted=False).first()
        if not patient:
            return {
                'patient_hn': None,
                'patient_name': None,
                'has_patient_context': False,
                'context_text': f"ไม่พบข้อมูลผู้ป่วยรหัส ID {patient_id} ในระบบ",
                'scored_axes_count': 0,
                'safety_alerts': [],
            }

        # 1. Identity Context
        age_str = f"{patient.age} ปี" if patient.age is not None else "ไม่ระบุอายุ"
        gender_map = {'M': 'ชาย (Male)', 'F': 'หญิง (Female)', 'O': 'อื่นๆ'}
        gender_str = gender_map.get(patient.gender, patient.gender)

        # 2. Scored 39 Axes (คัดกรองเฉพาะแกนที่มีคะแนน ไม่เอา HYPOTHESIS / Null)
        scored_axes: List[Dict[str, Any]] = []
        latest_analysis = patient.analysis_records.filter(is_deleted=False).order_by('-analysis_date').first()
        raw_scores = {}

        if latest_analysis and latest_analysis.snapshot_scores:
            raw_scores = latest_analysis.snapshot_scores
        else:
            latest_bio = patient.biological_records.filter(is_deleted=False).order_by('-record_date').first()
            if latest_bio:
                raw_scores = latest_bio.to_scores_dict()

        for ax_id in range(1, 40):
            score_val = raw_scores.get(str(ax_id))
            if score_val is None:
                score_val = raw_scores.get(ax_id)

            if score_val is not None:
                try:
                    num_score = float(score_val)
                    if num_score > 0:
                        ax_name = CANONICAL_39_AXES.get(ax_id, f"Axis {ax_id}")
                        dom_id = (ax_id - 1) // 4 + 1
                        dom_code = f"D{min(dom_id, 12)}"
                        dom_title = CANONICAL_12_DOMAINS.get(dom_code, "Domain")

                        band = "สมบูรณ์ (Optimal)" if num_score < 40 else (
                            "ควรดูแล (Subclinical)" if num_score < 60 else (
                                "เสื่อมหน้าที่ (Functional)" if num_score < 80 else "รุนแรง (Pathological)"
                            )
                        )
                        scored_axes.append({
                            'axis_id': ax_id,
                            'name': ax_name,
                            'domain': f"{dom_code}: {dom_title}",
                            'score': num_score,
                            'band': band,
                        })
                except (ValueError, TypeError):
                    pass

        # จัดอันดับแกนที่มีความเสื่อมสูงสุด (Priority Dysfunctions)
        scored_axes_sorted = sorted(scored_axes, key=lambda x: x['score'], reverse=True)

        # 3. Clinical Safety Gates & Allergies
        safety_alerts = [
            "Iron Safety Gate: HOLD PENDING CONFIRMATION (ห้ามสั่งเสริมธาตุเหล็กจนกว่าจะมีผลตรวจ Ferritin, TIBC, Saturation ครบถ้วน)",
            "Terminology Check: MASH = Metabolic dysfunction-associated steatohepatitis (ห้ามใช้คำว่า Myxedema)",
        ]
        if patient.allergies:
            safety_alerts.append(f"ประวัติการแพ้: {patient.allergies}")
        else:
            safety_alerts.append("ประวัติการแพ้: ไม่ระบุ (ควรสอบถามซ้ำก่อนสั่งจ่าย)")

        # 4. Recent Clinical History (SOAP ล่าสุด 5 ครั้ง)
        recent_histories = []
        for hist in patient.histories.filter(is_deleted=False).order_by('-visit_date')[:5]:
            v_date = hist.visit_date.strftime("%d/%m/%Y") if hist.visit_date else "ไม่ระบุวัน"
            soap_text = f"[{v_date}] "
            if hist.subjective:
                soap_text += f"S: {hist.subjective[:100]} | "
            if hist.assessment:
                soap_text += f"A: {hist.assessment[:100]} | "
            if hist.plan:
                soap_text += f"P: {hist.plan[:100]}"
            recent_histories.append(soap_text)

        # 5. Assemble Context String with Length Guard (Token Budget)
        ctx_parts = [
            f"=== ข้อมูลผู้ป่วย (SINGLE SOURCE OF TRUTH) ===",
            f"HN: {patient.hn} | ชื่อ-สกุล: {patient.full_name} | อายุ: {age_str} | เพศ: {gender_str}",
            f"สถานะปัจจุบัน: {patient.get_status_display()}",
            "",
            "=== เกณฑ์ความปลอดภัยทางคลินิก (SAFETY GATES) ===",
        ]
        for alert in safety_alerts:
            ctx_parts.append(f"- {alert}")

        ctx_parts.append("")
        ctx_parts.append(f"=== ผลคะแนนแกนชีวภาพที่มีการตรวจยืนยัน ({len(scored_axes_sorted)} แกน) ===")
        if scored_axes_sorted:
            # ดึงแกนที่เสื่อมมากที่สุด 10 อันดับแรกเพื่อประหยัด Token
            top_axes = scored_axes_sorted[:10]
            for ax in top_axes:
                ctx_parts.append(f"- Axis {ax['axis_id']} ({ax['name']}): คะแนน {ax['score']} [{ax['band']}] | {ax['domain']}")
            if len(scored_axes_sorted) > 10:
                ctx_parts.append(f"... และแกนชีวภาพอื่นอีก {len(scored_axes_sorted) - 10} แกนที่มีผลปกติ")
        else:
            ctx_parts.append("- ยังไม่มีผลการบันทึกคะแนนแกนชีววิทยาที่อนุมัติแล้ว (ทุกแกนเป็น HYPOTHESIS)")

        if recent_histories:
            ctx_parts.append("")
            ctx_parts.append("=== ประวัติการรักษาล่าสุด (SOAP NOTES) ===")
            for h in recent_histories:
                ctx_parts.append(f"- {h}")

        raw_context = "\n".join(ctx_parts)
        if len(raw_context) > cls.MAX_CONTEXT_CHARACTERS:
            raw_context = raw_context[:cls.MAX_CONTEXT_CHARACTERS] + "\n...[ตัดทอนข้อมูลเพื่อความปลอดภัยของ Context Window]..."

        return {
            'patient_id': patient.pk,
            'patient_hn': patient.hn,
            'patient_name': patient.full_name,
            'has_patient_context': True,
            'context_text': raw_context,
            'scored_axes_count': len(scored_axes),
            'safety_alerts': safety_alerts,
        }
