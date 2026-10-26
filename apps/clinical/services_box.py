"""
TSPI Box Builder Service.
Assembles raw multimodal assets and AI inferences (SOAP + 39 Axes + Citations)
into a sealed, cryptographically signed Box instance.
"""

import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from clinical.models import Box
from ai_service.library import library_engine
from ai_service.guardrail import ClinicalGuardrail
from ai_service.sanitizer import TextDeidentifier

logger = logging.getLogger("tspi.box_builder")


class BoxBuilderService:
    """Enterprise service for building and sealing multimodal intake boxes."""

    @classmethod
    def assemble_box(
        cls,
        patient=None,
        source: str = "WEB",
        raw_complaint: str = "",
        lab_markers: Optional[List[Dict[str, Any]]] = None,
        video_observations: Optional[str] = None,
        voice_file_path: str = "",
        video_file_path: str = "",
        lab_image_paths: Optional[List[str]] = None,
        soap_override: Optional[Dict[str, Any]] = None
    ) -> Box:
        """
        Assembles, sanitizes, guards, and seals an intake Box.
        """
        # 1. Sanitize text complaint
        sanitized_res = TextDeidentifier.sanitize(raw_complaint)
        clean_complaint = sanitized_res["sanitized_text"]

        # 2. Match relevant 39 biological axes from Library
        relevant_axes = library_engine.search_axes(clean_complaint, top_k=3)
        
        # 3. Correlate lab markers
        lab_correlations = library_engine.evaluate_lab_markers_against_axes(lab_markers) if lab_markers else []

        # 4. Prepare SOAP structure
        if soap_override:
            soap_data = soap_override
        else:
            markers_str = ", ".join([f"{m.get('marker')}={m.get('value')} {m.get('unit', '')}" for m in (lab_markers or [])]) or "ไม่พบตัวเลขแล็บผิดปกติ"
            soap_data = {
                "subjective": clean_complaint,
                "objective": f"ผลตรวจแล็บ: {markers_str}. ข้อสังเกตวิดีโอ: {video_observations or 'ไม่มี'}",
                "assessment": "พบลักษณะความเครียดทางสรีรวิทยาเบื้องต้นของระบบชีวภาพที่เกี่ยวข้อง (แพทย์เป็นผู้ตัดสินใจวินิจฉัย)",
                "plan": "ส่งต่อข้อมูลให้แพทย์ผู้รักษาตรวจร่างกายและประเมินทางคลินิกเพิ่มเติม"
            }

        # 5. Run M8 Guardrail on Assessment
        guarded = ClinicalGuardrail.sanitize_and_guard(soap_data.get("assessment", ""))
        soap_data["assessment"] = guarded["safe_text"]

        # 6. Assemble Box Contents Dictionary
        contents = {
            "complaint": clean_complaint,
            "has_pii_redacted": sanitized_res["has_pii"],
            "soap": soap_data,
            "relevant_axes": relevant_axes,
            "lab_markers": lab_markers or [],
            "lab_correlations": lab_correlations,
            "video_observations": video_observations or "",
            "guardrail_verdict": guarded["guardrail_status"],
            "assembled_at": timezone.now().isoformat()
        }

        # 7. Create Box & Auto-Seal with HMAC
        box = Box.objects.create(
            patient=patient,
            source=source if source in Box.Source.values else Box.Source.WEB,
            status=Box.Status.DONE,
            voice_file_path=voice_file_path,
            video_file_path=video_file_path,
            lab_image_paths=lab_image_paths or [],
            contents=contents,
            processed_at=timezone.now()
        )

        logger.info(f"Box successfully assembled and sealed: {box.id} [HMAC: {box.signature[:12]}...]")
        return box


box_builder = BoxBuilderService()
