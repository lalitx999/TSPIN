# -*- coding: utf-8 -*-
"""
TSPI Clinical Output Validator (Anti-Hallucination Architecture Layer)
Authoritative post-LLM validation layer that compares generated natural-language text
against the immutable AnalysisRecord.ledger structured clinical truth.

Rule: "No Approved Source -> No Clinical Claim; No Provenance -> No Clinical Output"
"""

import re
import logging

logger = logging.getLogger(__name__)

# Machine-Readable Refusal States
REFUSAL_STATES = {
    "BLOCKED_BY_POLICY": "การสร้างข้อความถูกระงับเนื่องจากขัดต่อ นโยบายความปลอดภัยทางคลินิก (TSPI Safety Policy)",
    "INSUFFICIENT_APPROVED_INFORMATION": "ข้อมูลทางคลินิกที่มีอยู่ยังไม่เพียงพอสำหรับการสรุปผล (Insufficient Approved Information)",
    "NOT_ASSESSED": "แกนชีวภาพนี้ยังไม่ได้ผ่านการประเมินคะแนน (Not Assessed)",
    "REQUIRES_CLINICIAN_REVIEW": "ข้อความนี้ต้องได้รับการตรวจสอบและอนุมัติจากแพทย์ก่อนเปิดเผย (Requires Clinician Review)",
    "EMERGENCY_ESCALATION": "พบสัญญาณเตือนวิกฤต ต้องเข้าสู่กระบวนการพบแพทย์เร่งด่วน (Emergency Escalation Required)",
}


class ClinicalOutputValidator:
    """
    Validates any LLM-generated narrative text against the structured AnalysisRecord ledger.
    If the LLM makes claims that contradict the ledger (hallucinations), the validator sanitizes or rejects them.
    """

    @classmethod
    def validate(cls, text: str, ledger: dict, edition: str = "physician", is_approved: bool = False) -> dict:
        if not text:
            return {"is_valid": True, "sanitized_text": "", "violations": []}

        violations = []
        sanitized_text = text
        edition_str = str(edition).lower()

        thirty_nine_axes = ledger.get("thirty_nine_axes", {})
        mod_reg = ledger.get("module_registry", {})
        approved_modules_count = mod_reg.get("approved_modules", 0)
        report_state = ledger.get("report_state", "AI_DRAFT")

        # ── 1. Fabricated Axis/Domain Entity Check ────────────────────────────
        # Reject fabricated axis codes > AXIS_39 (e.g. AXIS_40, AXIS_99)
        fabricated_axes = re.findall(r'\b(AXIS_\d+|Axis\s+\d+|แกนที่\s+\d+)\b', text, flags=re.IGNORECASE)
        for match in fabricated_axes:
            num = re.sub(r'\D', '', match)
            if num and int(num) > 39:
                violations.append({
                    "rule_id": "VAL-001",
                    "severity": "REJECT",
                    "message": f"Fabricated axis entity detected: {match} (Max canonical axis is 39)."
                })
                return {
                    "is_valid": False,
                    "sanitized_text": REFUSAL_STATES["BLOCKED_BY_POLICY"],
                    "refusal_state": "BLOCKED_BY_POLICY",
                    "violations": violations,
                }

        # ── 2. Un-assessed Axis Claim Protection Check ───────────────────────
        # If an axis has severity_score = None or score_status != SCORED,
        # LLM text cannot assert a numeric score or pathological score for it.
        for axis_code, axis_data in thirty_nine_axes.items():
            num_id = axis_code.replace("AXIS_", "")
            score = axis_data.get("severity_score")
            score_status = axis_data.get("score_status")

            if score is None or score_status in ("NO_APPROVED_SCORING_RULE", "NOT_SCORED_CONFOUNDED", "NOT_SCORED_HYPOTHESIS"):
                # Check if LLM explicitly assigned a score percentage to this axis in text
                pattern = rf'(?:Axis\s+{num_id}|แกนที่\s+{num_id}).*?(\d{{1,3}}\s*%|\d{{1,3}}\s*คะแนน)'
                if re.search(pattern, sanitized_text, flags=re.IGNORECASE):
                    violations.append({
                        "rule_id": "VAL-002",
                        "severity": "SANITIZE",
                        "message": f"Axis {num_id} has no approved score in ledger, but text assigned a score to it."
                    })
                    # Sanitize out the score assignment
                    sanitized_text = re.sub(
                        rf'(Axis\s+{num_id}|แกนที่\s+{num_id})([^\.\n]*?)(\d{{1,3}}\s*%|\d{{1,3}}\s*คะแนน)',
                        rf'\1 (ยังไม่ได้ประเมินคะแนน — ไม่มีสูตรคำนวณอนุมัติ)',
                        sanitized_text,
                        flags=re.IGNORECASE
                    )

        # ── 3. Unapproved Module Recommendation Check ────────────────────────
        # If approved_modules == 0, text must not prescribe or recommend specific polyherbal modules
        if approved_modules_count == 0:
            if re.search(r'(แนะนำให้รับประทานสมุนไพร|สูตรสมุนไพรบำบัดเฉพาะทาง|Module\s+MOD_\d+)', sanitized_text, flags=re.IGNORECASE):
                violations.append({
                    "rule_id": "VAL-003",
                    "severity": "SANITIZE",
                    "message": "Module registry has 0 approved modules. Specific module recommendations sanitized."
                })
                sanitized_text = re.sub(
                    r'(แนะนำให้รับประทานสมุนไพร|สูตรสมุนไพรบำบัดเฉพาะทาง|Module\s+MOD_\d+)[^\.\n]*',
                    '(คำแนะนำสูตรสมุนไพรเฉพาะทางอยู่ระหว่างการพิจารณาอนุมัติโดยแพทย์)',
                    sanitized_text,
                    flags=re.IGNORECASE
                )

        # ── 4. Approval Wording Contradiction Resolution ──────────────────────
        if not is_approved or report_state == "AI_DRAFT":
            if "แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว" in sanitized_text or "แผนการรักษาที่แพทย์อนุมัติแล้ว" in sanitized_text:
                violations.append({
                    "rule_id": "VAL-004",
                    "severity": "SANITIZE",
                    "message": "Unapproved report text contains approval claim. Replaced with draft wording."
                })
                sanitized_text = sanitized_text.replace("แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว", "ร่างแผนดูแลสุขภาพที่อยู่ระหว่างการพิจารณาของแพทย์")
                sanitized_text = sanitized_text.replace("แผนการรักษาที่แพทย์อนุมัติแล้ว", "ร่างแผนการดูแลสุขภาพที่อยู่ระหว่างการพิจารณาของแพทย์")
                sanitized_text = sanitized_text.replace("ข้อแนะนำที่อนุมัติแล้วโดยแพทย์", "ร่างข้อแนะนำที่อยู่ระหว่างการพิจารณาของแพทย์")

        # ── 5. Absolute Iron Contraindication Correction ──────────────────────
        if "ห้ามรับประทานเนื้อแดง" in sanitized_text or "ห้ามธาตุเหล็กเด็ดขาด" in sanitized_text:
            violations.append({
                "rule_id": "VAL-005",
                "severity": "SANITIZE",
                "message": "Absolute dietary iron ban detected. Corrected to intervention-specific supplement hold."
            })
            sanitized_text = sanitized_text.replace(
                "ห้ามรับประทานเนื้อแดงและอาหารที่มีธาตุเหล็กเด็ดขาด",
                "ยังไม่ควรเริ่มอาหารเสริมธาตุเหล็กเองจนกว่าจะทราบสถานะธาตุเหล็กและชนิดของความผิดปกติของฮีโมโกลบิน"
            )
            sanitized_text = sanitized_text.replace(
                "ห้ามธาตุเหล็กเด็ดขาด",
                "ระงับเฉพาะสารเสริมอาหารธาตุเหล็ก (ชั่วคราวเพื่อรอผลแล็ปยืนยัน)"
            )

        # ── 6. Patient Edition Engine Tag Cleansing ───────────────────────────
        if edition_str == "patient":
            sanitized_text = sanitized_text.replace('[PASS]', '(ผ่านเกณฑ์)')
            sanitized_text = sanitized_text.replace('[HOLD]', '(รอการยืนยัน)')
            sanitized_text = sanitized_text.replace('[CONTRAINDICATED]', '(ไม่แนะนำ)')
            sanitized_text = sanitized_text.replace('[MEASURED]', '(ผลตรวจยืนยัน)')
            sanitized_text = sanitized_text.replace('[DERIVED]', '(คำนวณจากผลตรวจ)')
            sanitized_text = sanitized_text.replace('[HYPOTHESIS]', '(สภาวะสงสัย — รอตรวจเพิ่มเติม)')
            sanitized_text = sanitized_text.replace('[CLINICAL_INFERENCE]', '(ข้อมูลประเมินบริบท)')
            sanitized_text = sanitized_text.replace('[NOT_AVAILABLE]', '(ยังไม่มีผลตรวจ)')
            sanitized_text = sanitized_text.replace('[AI_SUGGESTED_CONSIDERATION]', '(ข้อพิจารณาเพื่อการดูแล)')
            sanitized_text = sanitized_text.replace('[PHYSICIAN_APPROVED_RECOMMENDATION]', '(คำแนะนำโดยแพทย์)')
            # Catch-all regex to strip any remaining [UPPERCASE_ENGINE_TAGS]
            sanitized_text = re.sub(r'\[[A-Z0-9_]{3,}\]', '', sanitized_text)

        return {
            "is_valid": len([v for v in violations if v["severity"] == "REJECT"]) == 0,
            "sanitized_text": sanitized_text,
            "violations": violations
        }
