"""
TSPI M7: Deep Biological Reasoning Engine.
Uses DeepSeek-R1-671B for multi-factorial health balance analysis,
scoring across the 39 Biological Axes, and cross-referencing biochemical contraindications.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from .gateway import gateway
from .config import config

logger = logging.getLogger("tspi.reasoning")


class BiologicalReasoner:
    """Deep multi-axis reasoning and biochemical interaction engine."""

    SYSTEM_PROMPT = """คุณคือ DeepSeek-R1 ระบบคำนวณชีวเคมีและสมดุลชีวภาพระดับโมเลกุล (Biochemical Systems Engine) ของ TSPI
หน้าที่ของคุณ:
1. วิเคราะห์ข้อมูล SOAP และตัวเลขแล็บ เพื่อประเมินระดับความตึงเครียด (Strain Score: 0-100) ของ 39 แกนชีวภาพ
2. ตรวจสอบกลไกทางสรีรวิทยา เช่น เส้นทาง AMPK/mTOR, ไมโทคอนเดรีย, การล้างพิษของตับ (Phase I/II), และแกนลำไส้-สมอง
3. สรุปข้อควรระวัง (Contraindications) ทางชีวเคมี
4. ห้ามวินิจฉัยโรคเด็ดขาด ไม่ระบุชื่อโรคในมนุษย์ เน้นการวิเคราะห์สมดุลชีวภาพระดับเซลล์เท่านั้น

ตอบกลับเป็น JSON Object ตามโครงสร้างนี้:
{
  "primary_axes_strained": [
    {"axis_id": 1, "title": "การอักเสบระดับเซลล์ (Inflammation)", "strain_score": 75, "rationale": "คำอธิบายกลไก"},
    {"axis_id": 5, "title": "สมดุลน้ำตาลและอินซูลิน (Glucose/Insulin)", "strain_score": 82, "rationale": "คำอธิบายกลไก"}
  ],
  "biochemical_interactions": "คำอธิบายปฏิสัมพันธ์ระหว่างระบบ",
  "contraindications_warning": "ข้อควรระวังหรือข้อห้ามใช้ทางชีวเคมี",
  "recommended_investigation_areas": ["รายการประเด็นที่แพทย์ควรตรวจเพิ่มเติม"]
}
"""

    @classmethod
    async def evaluate_39_axes(
        cls,
        soap_data: Dict[str, Any],
        lab_markers: Optional[List[Dict[str, Any]]] = None,
        flagged_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Runs DeepSeek-R1 to analyze biological balance across 39 axes."""
        user_prompt_lines = [
            f"สรุปอาการ SOAP ทางการแพทย์:\n{json.dumps(soap_data, ensure_ascii=False, indent=2)}\n"
        ]
        if lab_markers:
            user_prompt_lines.append(f"ผลแล็บตัวเลข:\n{json.dumps(lab_markers, ensure_ascii=False, indent=2)}\n")
        if flagged_rules:
            user_prompt_lines.append(f"กฎคลินิกที่เข้าข่าย:\n{json.dumps(flagged_rules, ensure_ascii=False, indent=2)}\n")

        user_prompt = "\n".join(user_prompt_lines)

        res = await gateway.call_deepseek_reasoner(
            system_prompt=cls.SYSTEM_PROMPT,
            user_prompt=user_prompt
        )

        content = res.get("content", "")
        reasoning_chain = res.get("reasoning_content", "")

        # Fallback simulation if key not configured
        if not res.get("success") or not content or "ขออภัย" in content:
            return {
                "success": True,
                "is_fallback": True,
                "analysis": {
                    "primary_axes_strained": [
                        {"axis_id": 1, "title": "การอักเสบระดับเซลล์ (Cellular Inflammation)", "strain_score": 68, "rationale": "พบสิ่งตรวจพบที่สัมพันธ์กับการอักเสบระดับต่ำ"},
                        {"axis_id": 5, "title": "สมดุลน้ำตาลและอินซูลิน (Glucose Dynamics)", "strain_score": 74, "rationale": "มีแนวโน้มความเครียดต่อการจัดการพลังงานของเซลล์"}
                    ],
                    "biochemical_interactions": "แกนการอักเสบและเมแทบอลิซึมทำงานเชื่อมโยงกัน (Cross-talk)",
                    "contraindications_warning": "ควรระวังการเสริมสารกลุ่มกระตุ้นตับในผู้ที่มีค่าเอนไซม์ผิดปกติ",
                    "recommended_investigation_areas": ["ตรวจระดับ C-Reactive Protein (CRP)", "ตรวจระดับ HbA1c ซ้ำ"]
                },
                "deepseek_thinking": "จำลองตรรกะการวิเคราะห์ 39 แกนแบบ Deterministic (Simulated DeepSeek Reasoning Chain)",
                "gateway": "deepseek-fallback"
            }

        try:
            parsed = json.loads(content)
            return {
                "success": True,
                "is_fallback": False,
                "analysis": parsed,
                "deepseek_thinking": reasoning_chain,
                "gateway": "deepseek-r1-api"
            }
        except Exception as e:
            logger.warning(f"Failed to parse DeepSeek JSON response: {e}")
            return {
                "success": True,
                "is_fallback": True,
                "analysis": {
                    "primary_axes_strained": [],
                    "biochemical_interactions": content[:500],
                    "contraindications_warning": "กรุณาปรึกษาแพทย์ผู้เชี่ยวชาญ",
                    "recommended_investigation_areas": []
                },
                "deepseek_thinking": reasoning_chain,
                "gateway": "deepseek-r1-raw"
            }


biological_reasoner = BiologicalReasoner()
