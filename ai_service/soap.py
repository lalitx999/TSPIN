"""
TSPI M4: SOAP Clinical Structurer.
Uses Groq Cloud (Llama-3.3-70B-Versatile) for sub-second clinical synthesis
into Subjective, Objective, Assessment, Plan (SOAP) format.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from .gateway import gateway
from .config import config

logger = logging.getLogger("tspi.soap")


class SOAPStructurer:
    """Transforms raw patient multimodal intakes into medical SOAP records."""

    SYSTEM_PROMPT = """คุณเป็นบรรณารักษ์ข้อมูลทางการแพทย์ผู้เชี่ยวชาญ (Clinical Documentation Specialist)
หน้าที่ของคุณคือรับข้อมูลอาการคนไข้, ตัวเลขผลแล็บ, และข้อสังเกตจากคลิปวิดีโอ แล้วจัดหมวดหมู่ลงในรูปแบบ SOAP อย่างกระชับ แม่นยำ และเป็นมืออาชีพ

กฎเหล็กด้านจริยธรรมทางการแพทย์:
1. ห้ามทำการวินิจฉัยโรคเด็ดขาด ห้ามระบุว่าคนไข้เป็นโรคอะไร (เช่น ห้ามฟันธงว่าเป็นเบาหวาน ความดัน หรือมะเร็ง)
2. ในส่วน Assessment (A) ให้สรุปเฉพาะข้อสังเกตเชิงการทำงานของร่างกาย (เช่น 'พบลักษณะสมดุลกลูโคสบกพร่อง' หรือ 'มีสัญญาณการอักเสบระดับต่ำ')
3. ในส่วน Plan (P) ให้เสนอแนะการตรวจยืนยันเพิ่มเติม และประเด็นที่แพทย์ควรซักประวัติเพิ่มเติม

ตอบกลับเป็น JSON Object เท่านั้น ตามโครงสร้างนี้:
{
  "subjective": "สรุปอาการที่คนไข้บอกเล่า ระยะเวลา และปัจจัยกระตุ้น",
  "objective": "สรุปผลแล็บ ตัวเลข สัญญาณชีพ และสิ่งตรวจพบทางกายภาพ",
  "assessment": "บทวิเคราะห์ความสมดุลของระบบชีวภาพเบื้องต้น (ไม่มีการฟันธงชื่อโรค)",
  "plan": "ข้อเสนอแนะในการตรวจทางห้องปฏิบัติการเพิ่มเติม และคำถามสำหรับแพทย์"
}
"""

    @classmethod
    async def generate_soap(
        cls,
        patient_complaint: str,
        lab_markers: Optional[List[Dict[str, Any]]] = None,
        video_observations: Optional[str] = None,
        relevant_axes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Synthesizes multimodal evidence into a structured clinical SOAP report."""
        user_content_lines = [f"ข้อมูลอาการคนไข้ (Subjective Evidence):\n{patient_complaint}\n"]

        if lab_markers:
            user_content_lines.append(f"ผลตรวจทางห้องปฏิบัติการ (Lab Numbers):\n{json.dumps(lab_markers, ensure_ascii=False, indent=2)}\n")

        if video_observations:
            user_content_lines.append(f"ข้อสังเกตจากคลิปวิดีโอ (Video Observations):\n{video_observations}\n")

        if relevant_axes:
            axes_summary = ", ".join([f"แกน {ax.get('axis_id')}: {ax.get('title')}" for ax in relevant_axes])
            user_content_lines.append(f"แกนชีวภาพที่เกี่ยวข้อง (39 Biological Axes):\n{axes_summary}\n")

        user_content = "\n".join(user_content_lines)

        messages = [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        # Call Groq Gateway with JSON mode
        res = await gateway.call_groq_chat(
            messages=messages,
            temperature=0.1,
            max_tokens=1500,
            response_format={"type": "json_object"} if config.is_groq_available() else None
        )

        content = res.get("content", "")

        # Fallback simulation if Groq key wasn't present
        if not res.get("success") or not content or "ขออภัย" in content:
            # Deterministic Fallback simulation
            markers_desc = ", ".join([f"{m.get('marker')}={m.get('value')}" for m in (lab_markers or [])]) or "ไม่พบตัวเลขแล็บผิดปกติ"
            return {
                "success": True,
                "is_fallback": True,
                "soap": {
                    "subjective": f"คนไข้บ่นอาการ: {patient_complaint[:150]}...",
                    "objective": f"ผลตรวจทางกายภาพและแล็บ: {markers_desc}. ข้อสังเกตวิดีโอ: {video_observations or 'ไม่มี'}",
                    "assessment": "พบลักษณะความเครียดทางสรีรวิทยาเบื้องต้นของระบบชีวภาพที่เกี่ยวข้อง (แพทย์เป็นผู้ตัดสินใจวินิจฉัย)",
                    "plan": "แนะนำให้แพทย์ตรวจร่างกายซ้ำ และพิจารณาส่งตรวจระดับน้ำตาล/ไขมันเพิ่มเติม"
                },
                "gateway": "groq-fallback"
            }

        try:
            parsed_soap = json.loads(content)
            return {
                "success": True,
                "is_fallback": False,
                "soap": parsed_soap,
                "gateway": "groq-llama-3.3-70b"
            }
        except Exception as e:
            logger.warning(f"Could not parse Groq SOAP JSON: {e}. Raw content: {content}")
            return {
                "success": True,
                "is_fallback": True,
                "soap": {
                    "subjective": patient_complaint,
                    "objective": str(lab_markers or "ปกติ"),
                    "assessment": content[:300],
                    "plan": "ส่งต่อข้อมูลให้แพทย์ผู้รักษาประเมินการรักษา"
                },
                "gateway": "groq-raw-fallback"
            }


soap_structurer = SOAPStructurer()
