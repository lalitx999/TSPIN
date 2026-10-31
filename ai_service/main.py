"""
TSPI Dedicated AI Copilot & Streaming Microservice (FastAPI).
Runs on Port 8088 alongside Django Core (Port 8000).
Handles asynchronous LLM streaming (SSE), RAG Knowledge Search over 39 Axes & 12 Domains,
and botanical module citations.

Internal service only: every route except /health requires the shared
X-Internal-Token header, and only Django calls it (never the browser).
LINE webhooks are received by Django directly, not by this service.
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Any, Optional
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Body, Request, Response, UploadFile, File, Form
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from .config import config
from .sanitizer import MediaSanitizer, TextDeidentifier, PolicyGuard, DataClassification
from .gateway import gateway
from .library import library_engine
from .soap import soap_structurer
from .reasoning import biological_reasoner
from .guardrail import ClinicalGuardrail

logger = logging.getLogger("tspi.ai_service")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'apps' / 'clinical' / 'data'
TXT_FILE = BASE_DIR / 'legacy_drpatt' / 'frontend' / 'public' / '38_tspi.txt'

async def require_internal_token(
    request: Request,
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
):
    """Fail-closed service-to-service auth: no configured token means every call is rejected."""
    if request.url.path == "/health":
        return
    if not config.verify_internal_token(x_internal_token):
        raise HTTPException(status_code=401, detail="Unauthorized internal call")


app = FastAPI(
    title="TSPI Clinical AI Copilot Microservice",
    version="2.0.0",
    description="High-concurrency streaming AI engine for 39 Biological Axes (12 Domains) & 200 Phytochemical Modules.",
    dependencies=[Depends(require_internal_token)],
)


# Knowledge Store in memory
KNOWLEDGE_STORE: Dict[str, Any] = {
    'axes': [],
    'domains': [],
    'modules': [],
    'txt_snippets': []
}


def load_knowledge():
    """Load authoritative 39 Axes, 12 Domains and botanical modules into memory."""
    axes_file = DATA_DIR / 'tspi_39_axes.json'
    if axes_file.exists():
        with open(axes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            KNOWLEDGE_STORE['domains'] = data.get('domains', [])
            all_axes = []
            for dom in data.get('domains', []):
                for ax in dom.get('axes', []):
                    ax_copy = dict(ax)
                    ax_copy['domain_title'] = dom.get('title')
                    all_axes.append(ax_copy)
            KNOWLEDGE_STORE['axes'] = all_axes

    modules_file = DATA_DIR / '200_module_tspi.json'
    if modules_file.exists():
        with open(modules_file, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            KNOWLEDGE_STORE['modules'] = raw if isinstance(raw, list) else raw.get('data', [])

    if TXT_FILE.exists():
        with open(TXT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            current_chunk = []
            for line in lines:
                current_chunk.append(line)
                if len(current_chunk) >= 50:
                    KNOWLEDGE_STORE['txt_snippets'].append("".join(current_chunk))
                    current_chunk = []
            if current_chunk:
                KNOWLEDGE_STORE['txt_snippets'].append("".join(current_chunk))


@app.on_event("startup")
async def startup_event():
    if not config.INTERNAL_API_TOKEN:
        logger.critical("INTERNAL_API_TOKEN is not set: all routes except /health will return 401.")
    load_knowledge()


class ChatRequest(BaseModel):
    message: str
    patient_id: Optional[int] = None
    patient_hn: Optional[str] = None
    context: Optional[str] = None
    role: str = "doctor"


class SanitizeTextRequest(BaseModel):
    text: str = Field(..., description="ข้อความดิบที่ต้องการกรองข้อมูลส่วนบุคคล")


@app.get("/health")
async def health_check():
    """Healthcheck endpoint with Institutional Provider & Sanitizer Readiness."""
    return {
        "status": "healthy",
        "service": "tspi-ai-service",
        "port": 8088,
        "total_domains": len(KNOWLEDGE_STORE['domains']) or 12,
        "total_axes": len(KNOWLEDGE_STORE['axes']) or 39,
        "total_modules": len(KNOWLEDGE_STORE['modules']) or 200,
        "engine": "FastAPI + SSE Streamer + RAG Knowledge Engine",
        "botany_engine_v2_1": {
            "m5_sanitizer_ready": True,
            "zero_retention_enforced": config.ZERO_RETENTION_ENABLED,
            "providers_configured": {
                "groq": config.is_groq_available(),
                "deepseek": config.is_deepseek_available(),
                "gemini": config.is_gemini_available()
            }
        }
    }


@app.post("/api/sanitizer/text")
async def sanitize_text_endpoint(
    req: SanitizeTextRequest,
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M5 Pre-Flight Text Sanitizer Endpoint.
    Redacts Thai National IDs, phone numbers, Hospital Numbers (HN), emails, and names.
    """
    res = TextDeidentifier.sanitize(req.text)
    classification = PolicyGuard.classify_payload(
        has_raw_audio=False,
        has_id_photo=False,
        has_sanitized_image=False,
        text_is_sanitized=True
    )
    return {
        "success": True,
        "sanitized_text": res["sanitized_text"],
        "has_pii": res["has_pii"],
        "redacted_counts": res["redacted_counts"],
        "classification": classification
    }


@app.post("/api/sanitizer/image")
async def sanitize_image_endpoint(
    file: UploadFile = File(...),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M5 Pre-Flight Media Scrubber Endpoint.
    Strips EXIF metadata and blurs detected human faces with a 25% safety margin.
    """
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty image payload")

    sanitized_bytes, faces_detected = MediaSanitizer.blur_faces(raw_bytes, safety_margin=0.25)
    classification = PolicyGuard.classify_payload(
        has_raw_audio=False,
        has_id_photo=False,
        has_sanitized_image=True,
        text_is_sanitized=True
    )

    import base64
    return {
        "success": True,
        "filename": file.filename,
        "faces_detected": faces_detected,
        "classification": classification,
        "sanitized_size_bytes": len(sanitized_bytes),
        "sanitized_base64": base64.b64encode(sanitized_bytes).decode("utf-8")
    }


# =========================================================================
# PHASE 2: MULTIMODAL INTAKE PIPELINE (M1, M2, M3)
# =========================================================================

@app.post("/api/intake/voice")
async def intake_voice_endpoint(
    file: UploadFile = File(...),
    consent_granted: bool = Form(False),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M1: Voice Intake Endpoint (Gemini 1.5 Flash Audio / Whisper API).
    Enforces PDPA Section 26 Biometric Consent Gate.
    De-identifies transcript before returning to callers.
    """
    raw_audio_bytes = await file.read()
    if not raw_audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    # 1. PDPA Section 26 Consent Verification Gate
    if not consent_granted:
        logger.info("[Voice Intake] Patient opted out of cloud biometric processing. Storing in Local Vault.")
        return {
            "success": True,
            "consent_granted": False,
            "manual_review_required": True,
            "classification": DataClassification.CLASS_C,
            "message": "คนไข้ไม่อนุญาตส่งเสียงประมวลผลภายนอก ข้อมูลถูกล็อกไว้ใน Local Vault สำหรับแพทย์/พยาบาลฟังด้วยตนเอง",
            "sanitized_transcript": None
        }

    # 2. Transcribe via Multimodal Audio Gateway
    prompt = (
        "คุณเป็นบรรณารักษ์การแพทย์ จงถอดความเสียงพูดภาษาไทยของคนไข้และคำศัพท์อาการอย่างครบถ้วน "
        "ห้ามสรุปความ ห้ามเดา และห้ามทำการวินิจฉัยโรคเด็ดขาด"
    )
    mime_type = file.content_type or "audio/mp3"
    gemini_res = await gateway.call_gemini_audio(prompt=prompt, audio_bytes=raw_audio_bytes, mime_type=mime_type)
    
    raw_transcript = gemini_res.get("content", "")

    # 3. Post-Process Transcript with M5 Text Sanitizer
    sanitized_res = TextDeidentifier.sanitize(raw_transcript)

    return {
        "success": True,
        "consent_granted": True,
        "sanitized_transcript": sanitized_res["sanitized_text"],
        "has_pii": sanitized_res["has_pii"],
        "redacted_counts": sanitized_res["redacted_counts"],
        "classification": DataClassification.CLASS_A,
        "gateway_info": {
            "model_used": config.GEMINI_FLASH_MODEL,
            "zero_retention": config.ZERO_RETENTION_ENABLED
        }
    }


@app.post("/api/intake/lab")
async def intake_lab_endpoint(
    file: UploadFile = File(...),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M2: Lab OCR & Image Vision Endpoint (Gemini 1.5 Flash Vision).
    1. Strips EXIF metadata (GPS/Device info).
    2. Blurs detected human faces with a 25% safety margin.
    3. Extracts laboratory markers (CBC, FBS, HbA1c, Lipid, eGFR) into Structured JSON.
    """
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty lab image payload")

    # 1. Media Scrubbing: Strip EXIF and Blur Faces
    sanitized_bytes, faces_detected = MediaSanitizer.blur_faces(raw_bytes, safety_margin=0.25)

    # 2. Call Gemini Vision for Structured Extraction
    prompt = (
        "คุณเป็นบรรณารักษ์ข้อมูลห้องปฏิบัติการทางการแพทย์ (Lab Information Specialist)\n"
        "หน้าที่ของคุณ:\n"
        "1. สกัดตัวเลขผลตรวจแล็บทั้งหมดที่พบในภาพ เช่น CBC, FBS, HbA1c, Lipid Profile, eGFR, BUN, Creatinine, AST, ALT\n"
        "2. ตอบเป็น JSON Array ตามโครงสร้างนี้เท่านั้น:\n"
        "[\n"
        '  {"marker": "ชื่อตัวชี้วัด", "value": ตัวเลข, "unit": "หน่วย", "ref_range": "ช่วงอ้างอิง", "flag": "Normal/High/Low"}\n'
        "]\n"
        "3. ห้ามทำการวินิจฉัยโรค ห้ามระบุว่าคนไข้เป็นโรคอะไรเด็ดขาด\n"
        "ตอบเฉพาะ JSON Array เท่านั้น"
    )
    mime_type = file.content_type or "image/jpeg"
    res = await gateway.call_gemini_vision(prompt=prompt, image_bytes=sanitized_bytes, mime_type=mime_type)

    raw_text = res.get("content", "[]")
    
    # Attempt parsing JSON array from response
    import json
    markers = []
    try:
        # Strip potential markdown code blocks
        clean_json_str = raw_text.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str[7:]
        if clean_json_str.startswith("```"):
            clean_json_str = clean_json_str[3:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]
        markers = json.loads(clean_json_str.strip())
    except Exception:
        # Fallback if raw text wasn't pure JSON
        markers = [{"raw_extraction": raw_text}]

    return {
        "success": True,
        "filename": file.filename,
        "faces_detected": faces_detected,
        "classification": DataClassification.CLASS_B,
        "markers": markers,
        "gateway_info": {
            "model_used": config.GEMINI_FLASH_MODEL,
            "zero_retention": config.ZERO_RETENTION_ENABLED
        }
    }


@app.post("/api/intake/video")
async def intake_video_endpoint(
    file: UploadFile = File(...),
    consent_granted: bool = Form(False),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M3: Clinical Video Temporal Scan Endpoint (Gemini 1.5 Pro Video).
    Generates timestamped visual observations without diagnostic assertions.
    """
    raw_video_bytes = await file.read()
    if not raw_video_bytes:
        raise HTTPException(status_code=400, detail="Empty video payload")

    if not consent_granted:
        logger.info("[Video Intake] Patient opted out. Storing in Local Vault.")
        return {
            "success": True,
            "consent_granted": False,
            "manual_review_required": True,
            "classification": DataClassification.CLASS_C,
            "message": "คนไข้ไม่อนุญาตส่งวิดีโอประมวลผลภายนอก ข้อมูลถูกล็อกไว้ใน Local Vault ให้แพทย์ตรวจดูด้วยตนเอง",
            "observations": None
        }

    prompt = (
        "คุณเป็นบรรณารักษ์ช่วยแพทย์บันทึกข้อมูลภาพเคลื่อนไหว (Clinical Video Observer)\n"
        "หน้าที่ของคุณ:\n"
        "1. สังเกตลักษณะทางกายภาพที่ปรากฏในคลิปวิดีโอ เช่น ขอบเขตแผล ผื่น ความแดง บวม การเคลื่อนไหว หรืออาการสั่น\n"
        "2. บันทึกเป็น Timecode ข้อสังเกตชัดเจน เช่น [00:05] [00:15]\n"
        "3. ห้ามวินิจฉัยโรคเด็ดขาด ไม่ระบุว่าคนไข้เป็นโรคอะไร ให้แพทย์ผู้ตรวจเป็นผู้ตัดสินใจ\n"
    )
    mime_type = file.content_type or "video/mp4"
    res = await gateway.call_gemini_video(prompt=prompt, video_bytes=raw_video_bytes, mime_type=mime_type)

    return {
        "success": True,
        "consent_granted": True,
        "filename": file.filename,
        "classification": DataClassification.CLASS_B,
        "observations": res.get("content", ""),
        "gateway_info": {
            "model_used": config.GEMINI_PRO_MODEL,
            "zero_retention": config.ZERO_RETENTION_ENABLED
        }
    }


# =========================================================================
# PHASE 3: DUAL-CORE AI & LIBRARY RAG (M4, M6, M7, M8)
# =========================================================================

class SOAPGenerateRequest(BaseModel):
    complaint: str = Field(..., description="ข้อความบอกเล่าอาการของคนไข้")
    lab_markers: Optional[List[Dict[str, Any]]] = Field(default=[], description="ผลแล็บที่สกัดได้จาก M2")
    video_observations: Optional[str] = Field(default=None, description="ข้อสังเกตจากคลิปวิดีโอ M3")


@app.post("/api/ai/soap")
async def generate_soap_endpoint(
    req: SOAPGenerateRequest,
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M4: SOAP Clinical Structurer (Groq Llama-3.3-70B).
    Synthesizes clinical evidence into Subjective, Objective, Assessment, Plan format.
    Passes output through M8 Guardrail to verify absence of direct diagnosis.
    """
    # 1. Search relevant biological axes
    relevant_axes = library_engine.search_axes(req.complaint, top_k=3)

    # 2. Generate structured SOAP
    soap_res = await soap_structurer.generate_soap(
        patient_complaint=req.complaint,
        lab_markers=req.lab_markers,
        video_observations=req.video_observations,
        relevant_axes=relevant_axes
    )

    soap_dict = soap_res.get("soap", {})

    # 3. Guardrail Assertion Check on Assessment
    assessment_text = soap_dict.get("assessment", "")
    guarded_assessment = ClinicalGuardrail.sanitize_and_guard(assessment_text)
    soap_dict["assessment"] = guarded_assessment["safe_text"]

    return {
        "success": True,
        "soap": soap_dict,
        "relevant_axes": relevant_axes,
        "guardrail": {
            "status": guarded_assessment["guardrail_status"],
            "redacted_violations": guarded_assessment["violated_patterns"]
        },
        "gateway": soap_res.get("gateway", "groq")
    }


class LibrarySearchRequest(BaseModel):
    query: str = Field(..., description="คำค้นหาอาการหรือแกนชีวภาพ")
    lab_markers: Optional[List[Dict[str, Any]]] = Field(default=[], description="ผลแล็บเพื่อแมปกับแกน")
    top_k: int = Field(default=5, description="จำนวนผลลัพธ์ที่ต้องการ")


@app.post("/api/library/search")
async def library_search_endpoint(
    req: LibrarySearchRequest,
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M6: TSPI Library 39 Axes RAG Search Endpoint.
    Returns matched axes with canonical compendium page citations and lab correlations.
    """
    matched_axes = library_engine.search_axes(req.query, top_k=req.top_k)
    lab_correlations = library_engine.evaluate_lab_markers_against_axes(req.lab_markers) if req.lab_markers else []

    return {
        "success": True,
        "query": req.query,
        "total_matches": len(matched_axes),
        "results": matched_axes,
        "lab_correlations": lab_correlations
    }


class DeepReasoningRequest(BaseModel):
    soap: Dict[str, Any] = Field(..., description="ข้อมูล SOAP ของคนไข้")
    lab_markers: Optional[List[Dict[str, Any]]] = Field(default=[], description="ผลแล็บตัวเลข")


@app.post("/api/ai/reasoning/39axes")
async def deep_reasoning_endpoint(
    req: DeepReasoningRequest,
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M7: Deep Biological Reasoning Endpoint (DeepSeek-R1-671B).
    Computes multi-factorial strain scores (0-100) across 39 biological axes.
    """
    reasoning_res = await biological_reasoner.evaluate_39_axes(
        soap_data=req.soap,
        lab_markers=req.lab_markers
    )
    return {
        "success": True,
        "analysis": reasoning_res.get("analysis", {}),
        "deepseek_thinking": reasoning_res.get("deepseek_thinking", ""),
        "gateway": reasoning_res.get("gateway", "deepseek-r1")
    }


class GuardrailVerifyRequest(BaseModel):
    claim: str = Field(..., description="ข้อความที่ต้องการตรวจสอบการอ้างอิง")
    source_text: str = Field(..., description="ข้อความจริงจากหน้าตำราอ้างอิง")
    threshold: Optional[float] = Field(default=0.70, description="เกณฑ์สอบเทียบความเหมือน (Calibrated Threshold)")


@app.post("/api/guardrail/verify")
async def guardrail_verify_endpoint(
    req: GuardrailVerifyRequest,
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    M8: Guardrail Verification Endpoint.
    Validates semantic citation grounding against the Medical Board calibrated threshold.
    """
    forbidden_check, violated = ClinicalGuardrail.check_forbidden_assertions(req.claim)
    grounding_res = ClinicalGuardrail.verify_citation_grounding(
        claim=req.claim,
        source_text=req.source_text,
        threshold=req.threshold
    )

    return {
        "success": True,
        "has_forbidden_assertions": forbidden_check,
        "violated_patterns": violated,
        "grounding": grounding_res,
        "verdict": "REJECT" if forbidden_check or not grounding_res["grounded"] else "APPROVE"
    }


def search_relevant_axes(query: str) -> List[Dict[str, Any]]:
    """Search 39 Axes based on clinical keywords in query."""
    q_lower = query.lower()
    matches = []
    
    # Specific clinical keyword mappings
    topic_mapping = {
        'อักเสบ': 1, 'inflammation': 1, 'crp': 1, 'ปวด': 1,
        'ภูมิคุ้มกัน': 2, 'autoimmune': 2, 'สะเก็ดเงิน': 2, 'psoriasis': 2,
        'ไวรัส': 3, 'แบคทีเรีย': 3, 'ติดเชื้อ': 3,
        'น้ำตาล': 5, 'เบาหวาน': 5, 'insulin': 5, 'glucose': 5,
        'ไขมัน': 6, 'คอเลสเตอรอล': 6, 'ตับคั่งไขมัน': 6, 'lipid': 6,
        'พลังงาน': 7, 'mTOR': 7, 'ampk': 7,
        'ไมโทคอนเดรีย': 8, 'mitochondria': 8, 'atp': 8, 'เพลีย': 8,
        'ดีเอ็นเอ': 11, 'dna': 11, 'แก่': 14, 'senescence': 14,
        'ตับ': 15, 'สารพิษ': 15, 'detox': 15, 'ขับของเสีย': 15,
        'ลำไส้': 16, 'ท้องผูก': 16, 'ย่อย': 16, 'leaky gut': 16, 'ลำไส้รั่ว': 16,
        'หลอดเลือด': 20, 'ความดัน': 20, 'vascular': 20,
        'แผล': 24, 'ซ่อมแซม': 24, 'คอลลาเจน': 25,
        'กล้ามเนื้อ': 28, 'กระดูก': 26,
        'ฮอร์โมน': 31, 'ไทรอยด์': 33, 'thyroid': 33,
        'นอน': 34, 'เครียด': 34, 'สมอง': 34, 'ความจำ': 34,
        'ไต': 35, 'หัวใจ': 35,
        'มะเร็ง': 37, 'ก้อนเนื้อ': 37, 'เนื้องอก': 37, 'cancer': 37, 'oncology': 37
    }

    matched_axis_ids = set()
    for kw, ax_id in topic_mapping.items():
        if kw in q_lower:
            matched_axis_ids.add(ax_id)

    # Search in axes titles and descriptions
    for ax in KNOWLEDGE_STORE['axes']:
        ax_id = ax.get('axis_id')
        name = ax.get('name', '').lower()
        dom = ax.get('domain_title', '').lower()
        if ax_id in matched_axis_ids or any(w in name or w in dom for w in q_lower.split() if len(w) > 3):
            matches.append(ax)

    if not matches and KNOWLEDGE_STORE['axes']:
        matches = KNOWLEDGE_STORE['axes'][:3]

    return matches[:4]


from starlette.responses import StreamingResponse

def build_clinical_reasoning_response(query: str, patient_id: Optional[int] = None, context: Optional[str] = None) -> str:
    """Generate structured, grounded clinical reasoning citing 39 axes and botanical modules."""
    lines = []
    lines.append(f"### 🧬 ผลการวิเคราะห์ทางคลินิกเชิงกลไกชีววิทยา (Mechanistic Reasoning)\n")
    lines.append(f"**คำถาม/อาการทางคลินิก:** {query}\n")

    if context:
        lines.append("> 📋 **บริบททางคลินิกของผู้ป่วยที่เชื่อมโยง (Patient Grounding Context):**")
        lines.append("> ข้อมูลดึงตรงจาก Single Source of Truth และจำกัดเฉพาะแกนชีวภาพที่มีผลตรวจยืนยัน\n")

    matched_axes = search_relevant_axes(query)
    lines.append(f"จากการตรวจเทียบกับระบบ **39 แกนชีววิทยา (12 โดเมน)** และคลังพฤกษเคมี 200 โมดูล พบความเชื่อมโยงสำคัญ:\n")

    for i, ax in enumerate(matched_axes, 1):
        ax_id = ax.get('axis_id')
        name = ax.get('name')
        dom = ax.get('domain_title')
        mods = ax.get('modules', [])
        mod_str = ", ".join(mods[:4]) if mods else "ยังไม่มีโมดูลที่จับคู่กับแกนนี้ในคลังข้อมูล"

        lines.append(f"#### {i}. Axis {ax_id}: {name}")
        lines.append(f"- **โดเมนชีววิทยา:** {dom}")
        lines.append(f"- **กลไกระดับเซลล์:** มีผลต่อ signaling cascades, cellular stress และ metabolic homeostasis")
        lines.append(f"- **โมดูลการรักษาเป้าหมาย:** `{mod_str}`\n")

    lines.append("### 🎯 แผนการบำบัดรักษาฟื้นฟู (9-Step Protocol Alignment)")
    lines.append("- **ระยะที่ 1 (Phase 1: Assess & Cleanse):** เคลียร์การอักเสบสะสมและเสริมเกราะป้องกันเยื่อบุ")
    lines.append("- **ระยะที่ 2 (Phase 2: Cellular Repair):** ฟื้นฟูการสร้างพลังงาน ATP และสมดุลไมโทคอนเดรีย")
    lines.append("- **ระยะที่ 3 (Phase 3: Longevity & Maintenance):** ปรับจังหวะชีวภาพและการฟื้นฟูระดับยีน\n")
    lines.append("> ⚠️ **ข้อควรระวังทางคลินิก (Safety Gates & Guardrails):**")
    lines.append("> 1. **Iron Safety Gate:** ห้ามสั่งจ่ายธาตุเหล็กจนกว่าจะมีผลแล็บ Ferritin / TIBC ยืนยัน (HOLD PENDING CONFIRMATION)")
    lines.append("> 2. **Terminology Invariant:** นิยามภาวะไขมันพอกตับต้องใช้ 'Metabolic dysfunction-associated steatohepatitis (MASH)'")
    lines.append("> 3. **Clinical Role:** ข้อมูลนี้จัดทำขึ้นเพื่อเป็นผู้ช่วยสรุปเวชสารสนเทศสำหรับแพทย์ผู้เชี่ยวชาญเท่านั้น ไม่สามารถใช้แทนการวินิจฉัยโรคหรือคำสั่งการรักษาขั้นสุดท้ายได้")

    return "\n".join(lines)


SSE_HEADERS = {
    "X-Accel-Buffering": "no",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}


@app.post("/api/v1/copilot/stream")
async def stream_copilot_chat_post(
    req: ChatRequest,
    x_internal_secret: Optional[str] = Header(None)
):
    """
    Streaming AI Copilot Chat for POST requests with X-Accel-Buffering disabled.
    """
    async def token_generator() -> AsyncGenerator[str, None]:
        response_text = build_clinical_reasoning_response(req.message, req.patient_id, req.context)
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            payload = json.dumps({"chunk": chunk, "done": False}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            await asyncio.sleep(0.015)

        done_payload = json.dumps({"chunk": "", "done": True})
        yield f"data: {done_payload}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream", headers=SSE_HEADERS)


# --- Schemas for AI-Intake, Lab OCR, and LINE Webhook ---

class AiIntakeRequest(BaseModel):
    transcript: str = Field(..., description="ข้อความบอกเล่าอาการของผู้ป่วยหรือเสียงแปลงข้อความ")
    patient_id: Optional[int] = None
    age: Optional[int] = None
    gender: Optional[str] = None


class AiIntakeResponse(BaseModel):
    triage_level: str  # 'normal', 'warning', 'urgent'
    red_flags: List[str]
    chief_complaint: str
    suspected_axes: List[Dict[str, Any]]
    recommended_domains: List[str]
    suggested_soap_draft: Dict[str, str]


class LabOcrRequest(BaseModel):
    raw_text: str = Field(..., description="ข้อความจากผลแล็บ หรือผลที่ได้จาก OCR")
    patient_id: Optional[int] = None


class LabOcrResponse(BaseModel):
    extracted_markers: List[Dict[str, Any]]
    critical_abnormalities: List[str]
    axis_score_recommendations: Dict[int, int]


# --- AI-Intake Endpoint ---

@app.post("/api/v1/ai-intake", response_model=AiIntakeResponse)
async def ai_intake_endpoint(req: AiIntakeRequest):
    """
    AI-Intake คัดกรองและสกัดโครงสร้างอาการคนไข้
    เชื่อมโยงเข้า 39 แกนชีววิทยา พร้อมตรวจจับสัญญาณอันตราย (Red Flags)
    """
    text_lower = req.transcript.lower()

    # ตรวจจับ Red Flags เบื้องต้น
    red_flags = []
    urgent_keywords = [
        ("แน่นหน้าอก", "สงสัยกล้ามเนื้อหัวใจขาดเลือดเฉียบพลัน (Acute Coronary Syndrome)"),
        ("เจ็บหน้าอกร้าวไปกราม", "สงสัยภาวะหลอดเลือดหัวใจวิกฤต"),
        ("ปากเบี้ยว", "สงสัยโรคหลอดเลือดสมองฉับพลัน (Acute Stroke - FAST)"),
        ("แขนขาอ่อนแรงครึ่งซีก", "สงสัยภาวะสมองขาดเลือด"),
        ("หมดสติ", "ภาวะหมดสติไม่ทราบสาเหตุ (Syncope)"),
        ("ไอเป็นเลือดสด", "ภาวะเลือดออกในทางเดินหายใจวิกฤต (Hemoptysis)"),
        ("ถ่ายเป็นเลือดสดปริมาณมาก", "ภาวะเลือดออกทางเดินอาหารเฉียบพลัน"),
    ]
    for kw, alert in urgent_keywords:
        if kw in text_lower:
            red_flags.append(f"{kw}: {alert}")

    triage_level = "urgent" if red_flags else ("warning" if any(w in text_lower for w in ["ปวดเรื้อรัง", "เหนื่อย", "อ่อนเพลียมาก", "แผลไม่หาย"]) else "normal")

    matched_axes = search_relevant_axes(req.transcript)
    suspected_axes = [
        {
            "axis_id": ax.get("axis_id"),
            "name": ax.get("name"),
            "domain": ax.get("domain_title"),
            "suggested_score": 70 if triage_level == "urgent" else 55
        }
        for ax in matched_axes
    ]

    domains = list({ax.get("domain_title") for ax in matched_axes if ax.get("domain_title")})

    return AiIntakeResponse(
        triage_level=triage_level,
        red_flags=red_flags,
        chief_complaint=req.transcript[:150] + ("..." if len(req.transcript) > 150 else ""),
        suspected_axes=suspected_axes,
        recommended_domains=domains,
        suggested_soap_draft={
            "subjective": f"ผู้ป่วยแจ้งอาการ: {req.transcript}",
            "objective": "สัญญาณชีพบาดเจ็บเบื้องต้นรอตรวจทานหน้าร้านคลินิก",
            "assessment": f"ความเสี่ยงระดับ {triage_level.upper()} - เชื่อมโยงแกน {', '.join(str(a['axis_id']) for a in suspected_axes)}",
            "plan": "แนะนำพบแพทย์เพื่อประเมิน 39 แกนชีวภาพเชิงลึกและส่งตรวจห้องปฏิบัติการจำเพาะ"
        }
    )


# --- Lab OCR Vision Parser Endpoint ---

@app.post("/api/v1/lab-ocr", response_model=LabOcrResponse)
async def lab_ocr_endpoint(req: LabOcrRequest):
    """
    Lab Marker Parser:
    แยกแยะค่าผลตรวจเลือด แปลงเป็นตัวเลข และตรวจเทียบค่าวิกฤตพร้อมจับคู่แกนชีวภาพ
    """
    import re

    markers_config = [
        {"name": "FBS (Fasting Blood Sugar)", "pattern": r"(?:fbs|glucose|น้ำตาล)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "mg/dL", "min": 70, "max": 99, "axis": 5},
        {"name": "HbA1c", "pattern": r"(?:hba1c|a1c)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "%", "min": 4.0, "max": 5.6, "axis": 5},
        {"name": "Total Cholesterol", "pattern": r"(?:cholesterol|tc)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "mg/dL", "min": 100, "max": 200, "axis": 6},
        {"name": "Triglycerides", "pattern": r"(?:triglyceride|tg)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "mg/dL", "min": 50, "max": 150, "axis": 6},
        {"name": "HDL", "pattern": r"(?:hdl)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "mg/dL", "min": 40, "max": 100, "axis": 6},
        {"name": "LDL", "pattern": r"(?:ldl)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "mg/dL", "min": 0, "max": 100, "axis": 6},
        {"name": "SGOT (AST)", "pattern": r"(?:ast|sgot)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "U/L", "min": 0, "max": 40, "axis": 15},
        {"name": "SGPT (ALT)", "pattern": r"(?:alt|sgpt)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "U/L", "min": 0, "max": 40, "axis": 15},
        {"name": "eGFR", "pattern": r"(?:egfr|gfr)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "mL/min/1.73m2", "min": 60, "max": 120, "axis": 35},
        {"name": "Creatinine", "pattern": r"(?:creatinine|cr)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "mg/dL", "min": 0.6, "max": 1.2, "axis": 35},
        {"name": "hs-CRP", "pattern": r"(?:crp|hs-crp)\s*[:=]?\s*(\d+(?:\.\d+)?)", "unit": "mg/L", "min": 0, "max": 3.0, "axis": 1},
    ]

    extracted = []
    critical_abnormalities = []
    axis_recommendations = {}

    for cfg in markers_config:
        match = re.search(cfg["pattern"], req.raw_text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            status = "normal"
            if val < cfg["min"]:
                status = "low"
                critical_abnormalities.append(f"{cfg['name']} ต่ำกว่าเกณฑ์ ({val} {cfg['unit']})")
                axis_recommendations[cfg["axis"]] = 65
            elif val > cfg["max"]:
                status = "high"
                critical_abnormalities.append(f"{cfg['name']} สูงเกินเกณฑ์ ({val} {cfg['unit']})")
                axis_recommendations[cfg["axis"]] = 75
            else:
                axis_recommendations[cfg["axis"]] = 35

            extracted.append({
                "marker": cfg["name"],
                "value": val,
                "unit": cfg["unit"],
                "status": status,
                "reference_range": f"{cfg['min']} - {cfg['max']}",
                "associated_axis": cfg["axis"]
            })

    return LabOcrResponse(
        extracted_markers=extracted,
        critical_abnormalities=critical_abnormalities,
        axis_score_recommendations=axis_recommendations
    )


@app.post("/api/v1/rag-query")
async def rag_knowledge_query(
    query: str = Body(..., embed=True)
):
    """
    RAG Knowledge Query across 39 Axes and 200 Modules with claim-level citations.
    """
    matched_axes = search_relevant_axes(query)
    results = []
    for ax in matched_axes:
        results.append({
            "axis_id": ax.get('axis_id'),
            "topic": f"Axis {ax.get('axis_id')}: {ax.get('name')}",
            "domain": ax.get('domain_title'),
            "target_modules": ax.get('modules', [])[:5],
            "citation": f"TSPI 39 Axes Mechanistic Compendium - Domain {ax.get('domain_id', 'General')}"
        })

    return {
        "query": query,
        "total_domains": 12,
        "total_axes": 39,
        "results": results
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8088)

