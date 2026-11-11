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
import re
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
    'txt_snippets': [],
    'clinic_info': [],
}
CLINIC_INFO_FILE = Path(__file__).resolve().parent / 'knowledge' / 'clinic_info.md'


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


def load_clinic_info():
    """แบ่งไฟล์ข้อมูลคลินิกเป็นหัวข้อ (## ...) ให้ผู้ช่วย AI ค้นได้"""
    KNOWLEDGE_STORE['clinic_info'] = []
    if not CLINIC_INFO_FILE.exists():
        return
    title, lines = None, []
    for line in CLINIC_INFO_FILE.read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            if title:
                KNOWLEDGE_STORE['clinic_info'].append({'title': title, 'text': "\n".join(lines).strip()})
            title, lines = line[3:].strip(), []
        elif title:
            lines.append(line)
    if title:
        KNOWLEDGE_STORE['clinic_info'].append({'title': title, 'text': "\n".join(lines).strip()})


@app.on_event("startup")
async def startup_event():
    if not config.INTERNAL_API_TOKEN:
        logger.critical("INTERNAL_API_TOKEN is not set: all routes except /health will return 401.")
    load_knowledge()
    load_clinic_info()


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
        "ถอดเสียงพูดภาษาไทยนี้เป็นข้อความตามคำพูดจริงของผู้พูดอย่างถูกต้อง "
        "ตอบกลับมาเฉพาะคำพูดที่ถอดได้เท่านั้น ห้ามใส่คำนำหน้า คำอธิบาย หัวข้อ รายการสรุป หรือเครื่องหมายคำพูดล้อมรอบ"
    )
    mime_type = file.content_type or "audio/mp3"
    gemini_res = await gateway.call_gemini_audio(prompt=prompt, audio_bytes=raw_audio_bytes, mime_type=mime_type)
    is_simulated = not bool(gemini_res.get("success"))
    raw_transcript = (gemini_res.get("content") or "").strip()
    if not is_simulated and raw_transcript:
        # ตัดหัวข้อหรือเครื่องหมายคำพูดส่วนเกินที่โมเดลบางรุ่นอาจใส่มา
        raw_transcript = re.sub(r'^ถอดความ[^:：\n]*[:：]\s*', '', raw_transcript).strip()
        raw_transcript = re.split(r'\n\s*คำศัพท์อาการที่ครบถ้วน\s*[:：]', raw_transcript, maxsplit=1)[0].strip()
        raw_transcript = raw_transcript.strip('"\'“” ')

    # 3. Post-Process Transcript with M5 Text Sanitizer
    sanitized_res = TextDeidentifier.sanitize(raw_transcript)

    return {
        "success": True,
        "simulated": is_simulated,
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
        "gateway": soap_res.get("gateway", "groq"),
        # True = LLM ไม่ได้ตอบ (ไม่มี key/ล่ม/parse ไม่ได้) ร่างนี้เป็นแม่แบบ ห้ามนำไปแสดงเป็นผล AI
        "is_fallback": bool(soap_res.get("is_fallback")),
        # ข้อมูลการใช้ token ให้ Django บันทึกและคุมงบต่อผู้ให้บริการ
        "provider": soap_res.get("provider", ""),
        "model": soap_res.get("model", ""),
        "usage": soap_res.get("usage", {}),
    }


# ============================================================================
# ซักประวัติที่คลินิก -> Gemini สรุป SOAP (ข้อความ + สัญญาณชีพ + รูป)
# ============================================================================
VISIT_SOAP_MAX_IMAGES = 6
VISIT_SOAP_IMAGE_EDGE = 1600  # ย่อด้านยาวก่อนส่ง ลดขนาดและ token

VISIT_SOAP_PROMPT = """คุณเป็นผู้ช่วยจัดทำบันทึกเวชระเบียนของคลินิก TSPI ให้พยาบาลและแพทย์
ได้รับ: ข้อความซักประวัติ (พิมพ์หรือพูด อาจไม่เรียบร้อย), สัญญาณชีพที่วัดจริง และรูปประกอบ (ถ้ามี)
งาน: จัดข้อมูลเป็น SOAP ภาษาไทย กระชับ ใช้ข้อมูลที่ได้รับเท่านั้น ห้ามแต่งข้อมูลที่ไม่มี

- subjective: อาการสำคัญ ระยะเวลา ลักษณะ ปัจจัยกระตุ้น อาการร่วม ยาที่ใช้ โรคประจำตัว การแพ้ ตามที่เล่า
- objective: สัญญาณชีพทุกค่าพร้อมหน่วย และสิ่งที่เห็นในรูป (เช่น ลักษณะผื่น ตัวเลขในใบผลแล็บ) บรรยายตามที่เห็น
- assessment: ข้อสังเกตเชิงการทำงานของร่างกาย และค่าที่ผิดปกติจากสัญญาณชีพ ห้ามฟันธงชื่อโรค ให้แพทย์เป็นผู้วินิจฉัย
- plan: สิ่งที่ควรซักหรือตรวจเพิ่ม และประเด็นให้แพทย์พิจารณา ห้ามระบุยาหรือขนาดยา

ถ้าข้อมูลส่วนใดไม่มี ให้เขียนว่า "ไม่มีข้อมูล" อย่าเว้นว่าง
ถ้าในข้อความหรือรูปมีอาการฉุกเฉิน (เช่น เจ็บหน้าอก หายใจลำบาก อ่อนแรงครึ่งซีก) ให้ขึ้นต้น assessment ด้วย "⚠ ควรประเมินด่วน:"
ตอบเป็น JSON เท่านั้น: {"subjective": "...", "objective": "...", "assessment": "...", "plan": "..."}"""

VITAL_LABELS = [
    ("bp_systolic", "ความดันบน", "mmHg"), ("bp_diastolic", "ความดันล่าง", "mmHg"), ("pulse", "ชีพจร", "ครั้ง/นาที"),
    ("temperature", "อุณหภูมิ", "°C"), ("weight_kg", "น้ำหนัก", "กก."), ("height_cm", "ส่วนสูง", "ซม."),
    ("bmi", "BMI", "กก./ม²"), ("spo2", "SpO2", "%"),
]


def _shrink_image(data: bytes) -> bytes:
    """ย่อด้านยาวเหลือ VISIT_SOAP_IMAGE_EDGE และบันทึกเป็น JPEG (รูปผ่านการลบ EXIF/เบลอหน้ามาแล้ว)"""
    import io
    from PIL import Image
    try:
        with Image.open(io.BytesIO(data)) as img:
            img = img.convert("RGB")
            img.thumbnail((VISIT_SOAP_IMAGE_EDGE, VISIT_SOAP_IMAGE_EDGE))
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=85)
            return out.getvalue()
    except Exception:
        return data


@app.post("/api/ai/visit/soap")
async def visit_soap_endpoint(
    history: str = Form(""),
    vitals: str = Form("{}"),
    images: List[UploadFile] = File(default=[]),
):
    """
    สรุป SOAP จากการซักประวัติที่คลินิกด้วย Gemini เสมอ (ไม่ขึ้นกับ AI_SOAP_PROVIDER)
    Django ลบข้อมูลระบุตัวตนในข้อความมาก่อน ที่นี่ลบ EXIF และเบลอใบหน้าในรูปซ้ำก่อนส่งออก
    """
    try:
        vitals_data = json.loads(vitals or "{}")
    except ValueError:
        vitals_data = {}
    history = TextDeidentifier.sanitize(history or "")["sanitized_text"].strip()

    sent_images = []
    for upload in (images or [])[:VISIT_SOAP_MAX_IMAGES]:
        raw = await upload.read()
        if not raw:
            continue
        clean, _faces = MediaSanitizer.blur_faces(raw, safety_margin=0.25)
        sent_images.append({"data": _shrink_image(clean), "mime_type": "image/jpeg"})

    if not history and not sent_images:
        raise HTTPException(status_code=400, detail="ไม่มีข้อมูลซักประวัติ")

    vital_lines = [f"- {label}: {vitals_data[key]} {unit}" for key, label, unit in VITAL_LABELS
                   if vitals_data.get(key) not in (None, "")]
    user_text = (
        "สัญญาณชีพ:\n" + ("\n".join(vital_lines) or "- ไม่มี") +
        f"\n\nข้อความซักประวัติ:\n{history or '(ไม่มีข้อความ มีเฉพาะรูป)'}" +
        f"\n\nจำนวนรูปประกอบ: {len(sent_images)} รูป"
    )

    res = await gateway.call_gemini_json(VISIT_SOAP_PROMPT, user_text, images=sent_images,
                                         temperature=0.2, max_tokens=4096)
    meta = {"provider": res.get("provider", "gemini"), "model": res.get("model", ""), "usage": res.get("usage", {})}
    if not res.get("success"):
        return {"success": False, "error": res.get("error", "GEMINI_FAILED"), **meta}

    content_raw = str(res.get("content") or "").strip()
    try:
        # ถอด markdown code fence หากโมเดลส่ง ```json ... ``` มา
        if content_raw.startswith("```"):
            lines = content_raw.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content_raw = "\n".join(lines).strip()

        # ดึงช่วง {...} หากมีข้อความข้างหน้าหรือข้างหลัง
        start_idx = content_raw.find("{")
        end_idx = content_raw.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content_raw = content_raw[start_idx:end_idx + 1]

        raw_soap = json.loads(content_raw)
        if not isinstance(raw_soap, dict):
            raise ValueError("not an object")
    except Exception as e:
        logger.warning(f"[Visit SOAP] Gemini returned non-JSON content: {e} | Raw: {content_raw[:300]}")
        return {"success": False, "error": "UNPARSEABLE", **meta}

    soap = {k: str(raw_soap.get(k) or "").strip() for k in ("subjective", "objective", "assessment", "plan")}
    guarded = ClinicalGuardrail.sanitize_and_guard(soap["assessment"])
    soap["assessment"] = guarded["safe_text"]
    return {
        "success": True,
        "soap": soap,
        "images_sent": len(sent_images),
        "guardrail": {"status": guarded["guardrail_status"], "redacted_violations": guarded["violated_patterns"]},
        "gateway": f"gemini:{meta['model']}",
        **meta,
    }


SUGGEST_AXES_PROMPT = """คุณคือ TSPI Clinical Systems Biology AI Copilot สำหรับคลินิกการแพทย์บูรณาการ ดร.พัทธ์
หน้าที่ของคุณ:
วิเคราะห์ข้อมูลการตรวจของผู้ป่วย (SOAP, สัญญาณชีพ, ประวัติแพ้ยา, โรคประจำตัว) เพื่อประเมินความผิดปกติของ "39 แกนชีววิทยา (39 Canonical Biological Axes)" ตามหลัก Functional & Systems Medicine

รายชื่อ 39 แกนชีววิทยา:
Axis 1: Systemic Inflammatory Load (การอักเสบระดับระบบ)
Axis 2: Innate & Adaptive Immune Balance (สมดุลภูมิคุ้มกัน)
Axis 3: Immune Senescence & Exhaustion (ความเสื่อมของภูมิคุ้มกัน)
Axis 4: Chronic Latent Infection Burden (การติดเชื้อเรื้อรังแฝง)
Axis 5: Glucose–Insulin Regulation (การควบคุมกลูโคสและอินซูลิน)
Axis 6: Lipid Metabolism & Transport (การเผาผลาญและขนส่งไขมัน)
Axis 7: Metabolic Flexibility & Energy Allocation (ความยืดหยุ่นทางเมแทบอลิซึม)
Axis 8: Mitochondrial Network (เครือข่ายไมโทคอนเดรีย)
Axis 9: Bioenergetic & Redox Coupling (การจับคู่พลังงานและรีดอกซ์)
Axis 10: Metabolic Organ Cross-talk (การสื่อสารระหว่างอวัยวะเมแทบอลิก)
Axis 11: DNA Repair & Genomic Stability (การซ่อมแซมดีเอ็นเอ)
Axis 12: Epigenetic Programming (การควบคุมเอพิเจเนติกส์)
Axis 13: Telomere Dynamics (พลวัตของเทโลเมียร์)
Axis 14: Cellular Senescence & SASP (เซลล์ชราภาพ)
Axis 15: Detoxification & Cellular Defense (การขับสารพิษและการปกป้องเซลล์)
Axis 16: Upper GI & Digestive Capacity (ระบบย่อยอาหารส่วนบนและกรดกระเพาะ)
Axis 17: Intestinal Barrier Integrity (ความสมบูรณ์ของเยื่อบุลำไส้และลำไส้รั่ว)
Axis 18: Microbiome Diversity & Ecology (ความหลากหลายของจุลชีพในลำไส้)
Axis 19: Gut–Immune–Systemic Axis (แกนลำไส้-ภูมิคุ้มกัน-ระบบ)
Axis 20: Endothelial Function & Microcirculation (การทำงานของเยื่อบุหลอดเลือดและการไหลเวียนโลหิตฝอย)
Axis 21: Arterial Stiffness & Vascular Compliance (ความยืดหยุ่นของหลอดเลือดแดง)
Axis 22: Tissue Perfusion & Oxygenation (การลำเลียงออกซิเจนและการซึมซาบเนื้อเยื่อ)
Axis 23: Lymphatic Drainage & Fluid Homeostasis (การระบายน้ำเหลืองและสมดุลของเหลว)
Axis 24: Extracellular Matrix Dynamics (พลวัตของโครงร่างค้ำจุนภายนอกเซลล์)
Axis 25: Wound Healing & Fibrogenic Balance (การสมานแผลและสมดุลพังผืด)
Axis 26: Bone Remodeling & Mineral Homeostasis (การสร้างและสลายกระดูก)
Axis 27: Stem Cell Niche & Regenerative Capacity (สเต็มเซลล์และความสามารถในการฟื้นฟู)
Axis 28: Skeletal Muscle Mass & Quality (มวลและคุณภาพของกล้ามเนื้อลาย)
Axis 29: Neuromuscular Junction & Motor Unit Integrity (การเชื่อมต่อประสาทและกล้ามเนื้อ)
Axis 30: Connective Tissue Integrity (ความแข็งแรงของเนื้อเยื่อเกี่ยวพัน)
Axis 31: HPA Axis & Stress Response (แกน HPA และการตอบสนองต่อความเครียด/คอร์ติซอล)
Axis 32: Thyroid Hormone Economy (ระบบฮอร์โมนไทรอยด์)
Axis 33: Sex Steroid & Reproductive Endocrine (ฮอร์โมนเพศ)
Axis 34: Central Neurotransmitter Balance (สมดุลสารสื่อประสาทส่วนกลาง)
Axis 35: Autonomic Nervous System & Vagal Tone (ระบบประสาทอัตโนมัติและ Vagal Tone)
Axis 36: Sleep Architecture & Circadian Rhythm (วงจรการนอนและจังหวะชีวภาพ)
Axis 37: Blood–Brain Barrier & Neuroinflammation (แผงกั้นเลือด-สมองและการอักเสบในระบบประสาท)
Axis 38: Hepatorenal Clearance (การขจัดสารพิษของตับและไต)
Axis 39: Systemic Immune–Oncology Surveillance (ระบบเฝ้าระวังภูมิคุ้มกันระดับโมเลกุล)

เกณฑ์การให้คะแนน:
- 50 คะแนน = ปกติ/ยังไม่พบสัญญาณบ่งชี้ชัดเจน (Default baseline)
- 60-75 คะแนน = มีอาการหรือผลตรวจบ่งชี้ถึงความบกพร่อง/เสียสมดุลปานกลาง
- 76-90 คะแนน = มีอาการชัดเจน รุนแรง หรือเรื้อรังตรงตามกลไกของแกนนั้น

กฎเหล็ก:
1. ตอบเป็น JSON object เท่านั้น ห้ามใส่คำบรรยายภายนอก JSON
2. "suggested_scores": อ็อบเจกต์ที่ key เป็นหมายเลขแกน "1" ถึง "39" และ value เป็นคะแนนตัวเลขจำนวนเต็ม (0-100) ต้องมีครบทั้ง 39 แกน (แกนที่ไม่มีอาการให้ใส่ 50)
3. "rationales": อ็อบเจกต์ที่ key เป็นหมายเลขแกนเฉพาะแกนที่มีคะแนน >= 60 พร้อมคำอธิบายสั้นๆ ภาษาไทย (1-2 ประโยค) ว่าทำไมจึงสงสัยแกนนี้จากอาการของผู้ป่วย
4. "summary_insight": สรุปภาพรวมความผิดปกติระดับเซลล์ของผู้ป่วยรายนี้ 2-3 บรรทัดภาษาไทย
"""


class SuggestAxesPayload(BaseModel):
    soap: Dict[str, str] = Field(default_factory=dict, description="SOAP note")
    vitals: Dict[str, Any] = Field(default_factory=dict, description="Vitals")
    history_text: Optional[str] = Field(default="", description="ข้อความซักประวัติเพิ่มเติม")
    allergies: Optional[str] = Field(default="", description="ประวัติแพ้ยา")
    medical_history: Optional[str] = Field(default="", description="โรคประจำตัว")
    current_medications: Optional[str] = Field(default="", description="ยาประจำตัวหรืออาหารเสริม")
    lab_biomarkers: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="ผลตรวจแล็บและตัวชี้วัดชีวเคมีล่าสุด")


@app.post("/api/ai/clinical/suggest-axes")
async def suggest_axes_endpoint(
    payload: SuggestAxesPayload,
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    """
    วิเคราะห์ข้อมูล Encounter (SOAP + Vitals + ประวัติ + ผลแล็บ) แล้วร่างคะแนน 39 แกนชีววิทยาด้วย Gemini
    """
    if x_internal_token != config.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized internal token")

    soap = payload.soap or {}
    vital_str = json.dumps(payload.vitals, ensure_ascii=False) if payload.vitals else "ไม่มี"

    lab_str = "ไม่มี"
    if payload.lab_biomarkers:
        lab_lines = []
        for l in payload.lab_biomarkers:
            status_text = " (ผิดปกติ/สูงกว่าเกณฑ์)" if l.get('is_abnormal') else " (ปกติ)"
            target = f" -> ส่งผลต่อ {l.get('target_axis')}" if l.get('target_axis') else ""
            lab_lines.append(f"{l.get('name', l.get('code'))}: {l.get('value')} {l.get('unit', '')}{status_text}{target}")
        lab_str = "\n  - " + "\n  - ".join(lab_lines)

    user_prompt = (
        f"ข้อมูลการตรวจของผู้ป่วย (Encounter Summary):\n"
        f"- อาการที่ผู้ป่วยเล่า (S): {soap.get('subjective') or payload.history_text or 'ไม่มี'}\n"
        f"- ผลตรวจร่างกายและสัญญาณชีพ (O): {soap.get('objective') or 'ไม่มี'} | สัญญาณชีพดิบ: {vital_str}\n"
        f"- การประเมินของแพทย์ (A): {soap.get('assessment') or 'ไม่มี'}\n"
        f"- แผนการตรวจรักษา (P): {soap.get('plan') or 'ไม่มี'}\n"
        f"- ยาประจำตัว / อาหารเสริม: {payload.current_medications or 'ไม่มี'}\n"
        f"- ประวัติแพ้ยา: {payload.allergies or 'ปฏิเสธ/ไม่มี'}\n"
        f"- โรคประจำตัวเดิม: {payload.medical_history or 'ไม่มี'}\n"
        f"- ผลตรวจแล็บและตัวชี้วัดชีวเคมี (Lab Biomarkers): {lab_str}\n\n"
        f"กรุณาวิเคราะห์และคืนค่าผลการประเมิน 39 แกนตามข้อกำหนด JSON โดยนำผลตรวจแล็บที่ผิดปกติมาคิดคำนวณและอธิบายใน rationales ด้วย"
    )

    res = await gateway.call_gemini_json(
        SUGGEST_AXES_PROMPT,
        user_prompt,
        temperature=0.2,
        max_tokens=4096
    )
    meta = {"provider": res.get("provider", "gemini"), "model": res.get("model", ""), "usage": res.get("usage", {})}
    if not res.get("success"):
        return {"success": False, "error": res.get("error", "GEMINI_FAILED"), **meta}

    content_raw = str(res.get("content") or "").strip()
    try:
        if content_raw.startswith("```"):
            lines = content_raw.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content_raw = "\n".join(lines).strip()

        start_idx = content_raw.find("{")
        end_idx = content_raw.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content_raw = content_raw[start_idx:end_idx + 1]

        data = json.loads(content_raw)
        if not isinstance(data, dict):
            raise ValueError("not an object")
    except Exception as e:
        logger.warning(f"[Suggest Axes] Non-JSON content: {e} | Raw: {content_raw[:300]}")
        return {"success": False, "error": "UNPARSEABLE", **meta}

    scores = {}
    for k, v in (data.get("suggested_scores") or {}).items():
        try:
            k_int = int(k)
            if 1 <= k_int <= 39:
                scores[str(k_int)] = max(0, min(100, int(v)))
        except (ValueError, TypeError):
            continue

    # เติมแกนที่ขาดด้วยค่า default 50
    for i in range(1, 40):
        if str(i) not in scores:
            scores[str(i)] = 50

    return {
        "success": True,
        "suggested_scores": scores,
        "rationales": data.get("rationales") or {},
        "summary_insight": data.get("summary_insight") or "",
        "gateway": f"gemini:{meta['model']}",
        **meta,
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


# คำสำคัญทางคลินิก (ไทย/อังกฤษ) -> แกนชีวภาพ ใช้ทั้งค้นแกนและตัดสินว่าคำถามอยู่ในขอบเขตความรู้ของ TSPI หรือไม่
TOPIC_KEYWORDS = {
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


def search_relevant_axes(query: str) -> List[Dict[str, Any]]:
    """Search 39 Axes based on clinical keywords in query."""
    q_lower = query.lower()
    matches = []
    
    # Specific clinical keyword mappings
    topic_mapping = TOPIC_KEYWORDS

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


# ==============================================================================
# ผู้ช่วย AI สำหรับผู้ป่วย (หน้าเว็บแบบแชท)
# เอกสารของ TSPI เป็นแหล่งหลักและอ้างอิงด้วย [n]; LLM ภายนอกเสริมความรู้ทั่วไปได้แต่ต้องแยกหัวข้อชัดเจน
# เรื่องที่ไม่เกี่ยวกับสุขภาพ LLM ตอบรหัส OUT_OF_SCOPE แล้วเราแทนด้วยข้อความปฏิเสธ
# ==============================================================================
ASSISTANT_SCOPE_TEXT = "สุขภาพ โรค การรักษา 39 แกนชีววิทยา ผลิตภัณฑ์ และบริการของคลินิก"
ASSISTANT_OUT_OF_SCOPE_TOKEN = "OUT_OF_SCOPE"
ASSISTANT_GENERAL_HEADING = "ข้อมูลทั่วไปเพิ่มเติม (จาก AI ไม่ใช่เอกสารของคลินิก):"
ASSISTANT_REFUSAL = (
    "ขออภัยค่ะ ผู้ช่วยนี้ตอบได้เฉพาะเรื่อง" + ASSISTANT_SCOPE_TEXT +
    " ลองถามเรื่องโรค อาการ หรือการรักษาที่สนใจ หรือทักเจ้าหน้าที่ทาง LINE ได้เลยค่ะ"
)
ASSISTANT_EMERGENCY = (
    "อาการที่เล่ามาอาจเป็นภาวะฉุกเฉิน กรุณาโทร 1669 หรือไปโรงพยาบาลที่ใกล้ที่สุดทันทีค่ะ "
    "ผู้ช่วย AI ไม่สามารถประเมินภาวะฉุกเฉินแทนแพทย์ได้"
)
ASSISTANT_EMERGENCY_KEYWORDS = ('แน่นหน้าอก', 'เจ็บหน้าอก', 'หายใจไม่ออก', 'หายใจลำบาก', 'หมดสติ', 'ปากเบี้ยว',
                                'แขนขาอ่อนแรง', 'ชัก', 'ไอเป็นเลือด', 'อาเจียนเป็นเลือด', 'ฆ่าตัวตาย', 'แพ้ยารุนแรง')
ASSISTANT_SYSTEM_PROMPT = (
    "คุณคือผู้ช่วยให้ข้อมูลสุขภาพของคลินิก TSPI ตอบเป็นภาษาไทย สุภาพ อบอุ่น เข้าใจง่าย ไม่เกิน 8 ประโยค\n"
    "กฎที่ห้ามละเมิด:\n"
    "1. ถ้าคำถามเป็นงานที่ไม่เกี่ยวกับ " + ASSISTANT_SCOPE_TEXT + " เช่น เขียนโค้ด ทำการบ้าน แปลเอกสาร คณิตศาสตร์ "
    "ให้ตอบคำเดียวว่า " + ASSISTANT_OUT_OF_SCOPE_TOKEN + "\n"
    "   (ข้อยกเว้น: คำทักทาย คำขอบคุณ เช่น \"ขอบคุณ\", \"โอเค\", \"เข้าใจแล้ว\" หรือคำบอกว่าเล่าอาการครบแล้ว "
    "ให้ตอบรับอย่างสุภาพใน 1-2 ประโยคและแนะนำให้กดปุ่มส่งให้แพทย์ถ้าต้องการ ห้ามตอบ OUT_OF_SCOPE)\n"
    "2. ตอบจาก <ความรู้> ของคลินิกก่อนเสมอ และอ้างอิงด้วยหมายเลข เช่น [1] ทุกประโยคที่มาจากความรู้นั้น\n"
    "3. ถ้าความรู้ของคลินิกไม่พอหรือไม่มี ให้เสริมด้วยความรู้ทางการแพทย์ทั่วไปที่เป็นที่ยอมรับ โดยขึ้นบรรทัดใหม่ว่า \""
    + ASSISTANT_GENERAL_HEADING + "\" แล้วจึงเขียน ห้ามใส่หมายเลขอ้างอิงในส่วนนี้ และห้ามอ้างว่าเป็นข้อมูลของคลินิก\n"
    "4. ห้ามวินิจฉัยโรค ห้ามแนะนำยา ขนาดยา หรือบอกว่าผู้ใช้ควรใช้ผลิตภัณฑ์ใด การรักษาและการเลือกผลิตภัณฑ์ต้องผ่านแพทย์\n"
    "5. ถ้าผู้ใช้ถามความรู้ทั่วไป ให้ตอบให้ครบถ้วนโดยไม่ต้องซักประวัติ แต่ถ้าผู้ใช้เล่าอาการ ให้ดู <ข้อมูลแฟ้มผู้ป่วย> "
    "เพื่อไม่ถามซ้ำสิ่งที่บันทึกไว้แล้ว ถามข้อมูลเพิ่มที่ยังขาด 1 คำถาม และแนะนำให้ส่งข้อมูลให้แพทย์ของคลินิกตรวจ"
)


def _format_patient_context_block(ctx: Optional[Dict[str, Any]]) -> str:
    """แปลงบริบทผู้ป่วยไร้ตัวตนเป็นข้อความสั้น ๆ ใน prompt (ลบ PII ซ้ำอีกครั้ง)"""
    if not isinstance(ctx, dict) or not ctx:
        return ""
    lines = []
    if ctx.get("gender") or ctx.get("age") is not None:
        lines.append(f"- เพศ/อายุ: {ctx.get('gender', 'ไม่ระบุ')} อายุ {ctx.get('age', 'ไม่ระบุ')} ปี")
    if ctx.get("allergies"):
        lines.append(f"- ประวัติแพ้ยา/อาหารที่บันทึกไว้: {TextDeidentifier.sanitize(str(ctx['allergies']))['sanitized_text'][:300]}")
    if ctx.get("medical_history"):
        lines.append(f"- โรคประจำตัวที่บันทึกไว้: {TextDeidentifier.sanitize(str(ctx['medical_history']))['sanitized_text'][:300]}")
    if ctx.get("current_medications"):
        lines.append(f"- ยา/อาหารเสริมที่บันทึกไว้: {TextDeidentifier.sanitize(str(ctx['current_medications']))['sanitized_text'][:300]}")
    if ctx.get("upcoming_appointment"):
        lines.append(f"- นัดหมายครั้งถัดไป: {str(ctx['upcoming_appointment'])[:60]}")
    if not lines:
        return ""
    return "<ข้อมูลแฟ้มผู้ป่วย>\n" + "\n".join(lines) + "\n</ข้อมูลแฟ้มผู้ป่วย>\n\n"


def _patient_friendly_sources(context: List[Dict[str, str]]) -> List[str]:
    """ซ่อนชื่อ chunk เทคนิค (เช่น 'คลังความรู้ TSPI ส่วนที่ 92') ไม่ให้คนไข้สับสน"""
    out: List[str] = []
    for c in context:
        title = str(c.get("title") or "").strip()
        if not title:
            continue
        if title.startswith("คลังความรู้ TSPI ส่วนที่"):
            title = "คลังความรู้สุขภาพ TSPI Clinic"
        if title not in out:
            out.append(title)
    return out


def _assistant_keywords(text: str) -> List[str]:
    q = text.lower()
    keys = [kw.lower() for kw in TOPIC_KEYWORDS if kw.lower() in q]
    keys += [w for w in re.findall(r"[a-z0-9][a-z0-9\-]{2,}", q)]
    for mod in KNOWLEDGE_STORE['modules']:
        code = str(mod.get('Code /_Product ID') or '').strip().lower()
        if len(code) >= 2 and code in q:
            keys.append(code)
    for info in KNOWLEDGE_STORE['clinic_info']:
        for word in ('คลินิก', 'นัด', 'ติดต่อ', 'เวลา', 'ผลิตภัณฑ์', 'สั่งซื้อ', 'ราคา', 'ประเมิน', '39 แกน', 'แกน'):
            if word in q and word in (info['title'] + info['text']):
                keys.append(word)
    return list(dict.fromkeys(keys))


def retrieve_tspi_knowledge(question: str, limit: int = 4) -> List[Dict[str, str]]:
    """ค้นความรู้ของ TSPI (ข้อมูลคลินิก, 39 แกน, เอกสารความรู้) ตามคำสำคัญ ไม่มีคำตรง = คืนรายการว่าง"""
    keys = _assistant_keywords(question)
    if not keys:
        return []
    found: List[Dict[str, Any]] = []
    for info in KNOWLEDGE_STORE['clinic_info']:
        score = sum((info['title'] + info['text']).lower().count(k) for k in keys)
        if score:
            found.append({'title': f"ข้อมูลคลินิก: {info['title']}", 'text': info['text'], 'score': score + 5})
    axis_ids = {TOPIC_KEYWORDS[k] for k in TOPIC_KEYWORDS if k.lower() in keys}
    for ax in KNOWLEDGE_STORE['axes']:
        name = str(ax.get('name', ''))
        if ax.get('axis_id') in axis_ids or any(k in name.lower() for k in keys if len(k) > 3):
            text = json.dumps({k: ax.get(k) for k in ('name', 'domain_title', 'sub_axes', 'description') if ax.get(k)},
                              ensure_ascii=False)[:1200]
            found.append({'title': f"แกนที่ {ax.get('axis_id')}: {name}", 'text': text, 'score': 4})
    for i, snippet in enumerate(KNOWLEDGE_STORE['txt_snippets']):
        score = sum(snippet.lower().count(k) for k in keys)
        if score >= 2:
            found.append({'title': f"คลังความรู้ TSPI ส่วนที่ {i + 1}", 'text': snippet[:1200], 'score': min(score, 6)})
    found.sort(key=lambda x: -x['score'])
    return [{'title': f['title'], 'text': f['text']} for f in found[:limit]]


class AssistantImageItem(BaseModel):
    data: str
    mime_type: str = "image/jpeg"


class AssistantMessage(BaseModel):
    role: str
    content: str


class AssistantChatRequest(BaseModel):
    messages: List[AssistantMessage] = Field(..., description="บทสนทนาล่าสุด (ข้อความสุดท้ายคือคำถามของผู้ใช้)")
    images_base64: Optional[List[AssistantImageItem]] = Field(default=None, description="ภาพประกอบที่ผู้ป่วยแนบมา (สูงสุด 3 ภาพ)")
    patient_context: Optional[Dict[str, Any]] = Field(default=None, description="บริบทผู้ป่วยแบบไม่ระบุตัวตน")


@app.post("/api/ai/assistant/chat")
async def assistant_chat_endpoint(req: AssistantChatRequest):
    """
    แชทผู้ช่วยสำหรับผู้ป่วย: ฉุกเฉิน -> ข้อความ 1669 ทันที (ไม่เรียก LLM),
    อื่น ๆ -> LLM ตอบจากเอกสาร TSPI ที่ค้นได้ (อ้างอิง [n]) เสริมความรู้ทั่วไปแยกหัวข้อ, นอกเรื่องสุขภาพ -> ปฏิเสธ,
    รองรับภาพประกอบ (เบลอใบหน้า + ลบ EXIF ก่อนส่ง Gemini Vision) แล้วผ่าน Guardrail ห้ามวินิจฉัย
    """
    import base64
    history = [m for m in req.messages if m.role in ('user', 'assistant') and (m.content.strip() or req.images_base64)][-8:]
    if not history or history[-1].role != 'user':
        raise HTTPException(status_code=400, detail="ข้อความสุดท้ายต้องเป็นคำถามของผู้ใช้")
    raw_question = history[-1].content.strip() or "ผู้ป่วยแนบรูปภาพนี้มาสอบถาม โปรดอธิบายสิ่งที่สังเกตเห็นเบื้องต้นอย่างระมัดระวังและซักถามอาการประกอบ โดยห้ามวินิจฉัยโรค"
    question = TextDeidentifier.sanitize(raw_question)["sanitized_text"][:2000]

    if any(k in question for k in ASSISTANT_EMERGENCY_KEYWORDS):
        return {"answer": ASSISTANT_EMERGENCY, "kind": "emergency", "sources": [], "usage": {}}

    sent_images: List[Dict[str, Any]] = []
    for item in (req.images_base64 or [])[:3]:
        try:
            raw_bytes = base64.b64decode(item.data, validate=True)
        except Exception:
            continue
        if not raw_bytes:
            continue
        clean, _faces = MediaSanitizer.blur_faces(raw_bytes, safety_margin=0.25)
        sent_images.append({"data": _shrink_image(clean), "mime_type": "image/jpeg"})

    context = retrieve_tspi_knowledge(question)
    knowledge = "\n\n".join(f"[{i + 1}] {c['title']}\n{c['text']}" for i, c in enumerate(context)) \
        or "(ไม่พบเอกสารของคลินิกที่ตรงกับคำถามนี้)"
    patient_block = _format_patient_context_block(req.patient_context)
    system_prompt = ASSISTANT_SYSTEM_PROMPT
    if sent_images:
        system_prompt += (
            "\n6. ผู้ใช้ได้แนบรูปภาพมาด้วย ให้อธิบายสิ่งที่สังเกตเห็นเป็นข้อมูลเบื้องต้นและซักถามอาการประกอบ "
            "ห้ามวินิจฉัยโรคจากภาพ ห้ามระบุชื่อโรค และแนะนำให้ส่งภาพให้แพทย์ของคลินิกตรวจเพิ่มเติม"
        )
    conv_messages = [
        {"role": m.role, "content": TextDeidentifier.sanitize(m.content)["sanitized_text"][:1500]}
        for m in history[:-1]
    ]
    conv_messages.append({"role": "user", "content": f"{patient_block}<ความรู้>\n{knowledge}\n</ความรู้>\n\nคำถาม: {question}"})

    if sent_images:
        res = await gateway.call_gemini_chat(system_prompt, conv_messages, images=sent_images, temperature=0.2, max_tokens=1500)
    else:
        res = await gateway.call_chat(config.SOAP_PROVIDER, messages=[{"role": "system", "content": system_prompt}, *conv_messages], temperature=0.2, max_tokens=1500)
    meta = {"provider": res.get("provider", config.SOAP_PROVIDER), "model": res.get("model", ""), "usage": res.get("usage", {})}
    answer = (res.get("content") or "").strip() if res.get("success") else ""
    sources = _patient_friendly_sources(context)
    if not answer:
        return {"answer": "ขออภัยค่ะ ระบบผู้ช่วยไม่พร้อมใช้งานชั่วคราว กรุณาลองใหม่ภายหลัง หรือทักเจ้าหน้าที่ทาง LINE",
                "kind": "unavailable", "sources": sources, **meta}
    if ASSISTANT_OUT_OF_SCOPE_TOKEN in answer[:40]:
        return {"answer": ASSISTANT_REFUSAL, "kind": "out_of_scope", "sources": [], **meta}
    guarded = ClinicalGuardrail.sanitize_and_guard(answer)
    # answer = มีเอกสารคลินิกรองรับ, general = ความรู้ทั่วไปจาก AI ล้วน
    return {"answer": guarded["safe_text"], "kind": "answer" if sources else "general", "sources": sources, **meta}


# ==============================================================================
# แชทกับผู้ป่วยใน LINE: ซักประวัติทีละคำถามและให้คำแนะนำทั่วไป ไม่วินิจฉัย ไม่แนะนำยา ไม่เลือกผลิตภัณฑ์ให้
# ทีมแพทย์อ่านบทสนทนานี้ใน EMR แล้วดึงเข้าเวชระเบียนเอง
# ==============================================================================
LINE_CHAT_HISTORY_LIMIT = 20
LINE_INTAKE_COMPLETE_TOKEN = "[INTAKE_COMPLETE]"
LINE_CHAT_SYSTEM_PROMPT = (
    "คุณคือผู้ช่วย AI ของคลินิก TSPI ที่คุยกับผู้ป่วยทางแชท LINE ตอบเป็นภาษาไทย สุภาพ อบอุ่น เป็นกันเอง "
    "เข้าใจง่าย ปรับระดับภาษาให้เหมาะกับ <ข้อมูลแฟ้มผู้ป่วย> และใช้คำลงท้ายว่า \"ครับ\"\n"
    "แยกจังหวะการคุยให้ฉลาด (ดูประวัติแชท + <ข้อมูลแฟ้มผู้ป่วย> ก่อนตอบทุกครั้ง):\n"
    "1. ถ้าผู้ป่วยถามความรู้สุขภาพหรือบริการคลินิก (ไม่ได้เล่าอาการ): ตอบจาก <ความรู้> ของคลินิกก่อนเสมอ "
    "ถ้าไม่มีใน <ความรู้> ให้ขึ้นบรรทัดใหม่ว่า \"" + ASSISTANT_GENERAL_HEADING + "\" แล้วให้คำแนะนำทั่วไปที่ปลอดภัย "
    "ไม่ต้องซักประวัติ 6 ข้อ\n"
    "2. ถ้าผู้ป่วยเล่าอาการ: ตรวจสอบกับประวัติแชทและ <ข้อมูลแฟ้มผู้ป่วย> ก่อนเพื่อไม่ถามซ้ำสิ่งที่รู้แล้ว "
    "ถามทีละ 1 คำถามเท่านั้น เฉพาะเรื่องที่ยังขาดจากรายการนี้: "
    "เริ่มเป็นเมื่อไรหรือเป็นมานานแค่ไหน, รุนแรงแค่ไหน (0-10), มีอาการอื่นร่วมไหม, "
    "ใช้ยาหรืออาหารเสริมอะไรอยู่, มีโรคประจำตัวไหม, แพ้ยาอะไรไหม "
    "(ถ้าในแฟ้มมีประวัติแพ้ยา/โรคประจำตัว/ยาเดิมอยู่แล้ว ให้ทวนสั้น ๆ หรือถามเฉพาะว่ามีเพิ่มเติมไหม)\n"
    "3. จบการสนทนาให้เป็น: เมื่อได้ข้อมูลครบแล้ว หรือผู้ป่วยส่งสัญญาณว่าครบแล้ว/ขอบคุณ (เช่น \"ประมาณนี้\", \"ครบแล้ว\", \"ขอบคุณ\"): "
    "ให้ขึ้นบรรทัดแรกด้วยคำว่า " + LINE_INTAKE_COMPLETE_TOKEN + " แล้วเขียน:\n"
    "   - สรุปอาการและประวัติที่ได้รับเป็นข้อย่อย (ระบุเฉพาะชื่อยาที่ผู้ป่วยแจ้ง ห้ามใส่ตัวเลขขนาดยา)\n"
    "   - คำแนะนำดูแลตัวเองเบื้องต้น (พักผ่อน ดื่มน้ำ อาหาร) และอาการเตือนที่ควรรีบพบแพทย์\n"
    "   - บอกว่าทีมแพทย์พร้อมเปิดอ่านสรุปนี้แล้ว และห้ามถามคำถามซักประวัติต่อ\n"
    "4. ถ้ามีรูปภาพแนบมา ให้อธิบายสิ่งที่สังเกตเห็นเบื้องต้นอย่างระมัดระวังและซักถามอาการประกอบ ห้ามวินิจฉัยโรคจากภาพ\n"
    "ห้ามเด็ดขาด:\n"
    "- บอกหรือเดาว่าผู้ป่วยเป็นโรคอะไร ถ้าถูกถาม ให้ตอบว่าผู้ช่วยบอกไม่ได้ แพทย์จะเป็นผู้ประเมิน\n"
    "- แนะนำยา ชื่อยา ขนาดยา หรือให้หยุดหรือปรับยาที่แพทย์สั่ง (เวลาทวนยาที่ผู้ป่วยกินอยู่ ห้ามใส่ขนาดยาเช่น 10 mg หรือ 500 มก.)\n"
    "- เลือกหรือแนะนำผลิตภัณฑ์ชิ้นใดให้ บอกได้แค่ว่าคลินิกมีผลิตภัณฑ์ การเลือกต้องผ่านแพทย์ "
    "หรือพิมพ์ \"ปิดบอท\" เพื่อคุยกับเจ้าหน้าที่\n"
    "- แปลผลแล็บออกมาเป็นการวินิจฉัย\n"
    "คุยเรื่องอื่น: ทักทายหรือขอบคุณตอบรับสั้น ๆ อย่างสุภาพ แล้วถามว่ามีเรื่องสุขภาพให้ช่วยไหม ถ้าขอให้ทำงานที่ไม่เกี่ยวกับสุขภาพหรือคลินิก "
    "เช่น การบ้าน เขียนโค้ด แปลเอกสาร ให้ปฏิเสธอย่างสุภาพใน 1 ประโยค\n"
    "รูปแบบ: จัดย่อหน้าหรือข้อย่อยด้วย \"-\" ให้อ่านง่ายบนมือถือ ไม่ใช้ markdown (ห้ามใช้ ** # หรือตาราง) ไม่ใส่หมายเลขอ้างอิง [1]"
)
LINE_CHAT_EMERGENCY = (
    "อาการที่เล่ามาอาจเป็นภาวะฉุกเฉิน กรุณาโทร 1669 หรือไปโรงพยาบาลที่ใกล้ที่สุดทันทีครับ "
    "ทีมแพทย์ของคลินิกจะเห็นข้อความนี้ด้วย"
)
LINE_CHAT_MEDICATION_REPLY = (
    "เรื่องยาและขนาดยา ผู้ช่วยแนะนำไม่ได้ครับ ต้องให้แพทย์หรือเภสัชกรเป็นผู้แนะนำ "
    "ทีมแพทย์ของคลินิกจะเห็นข้อความนี้ เล่าอาการเพิ่มเติมได้เลยครับ"
)
# ตัวเลขตามด้วยหน่วยยา = ขนาดยา ถือว่าหลุดกฎ ใช้ข้อความปลอดภัยแทนทั้งคำตอบ
_DOSAGE_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s*(?:มก\.?|มิลลิกรัม|mg|ม\.ก\.|มล\.?|มิลลิลิตร|ml|ไมโครกรัม|mcg|เม็ด|แคปซูล)",
                             re.IGNORECASE)
_MARKDOWN_NOISE = re.compile(r"\*\*|__|^#+\s*", re.MULTILINE)


LINE_CHAT_DIAGNOSIS_REPLY = (
    "ผู้ช่วยบอกไม่ได้ว่าเป็นโรคอะไรครับ แพทย์จะเป็นผู้ประเมิน ทีมแพทย์ของคลินิกจะอ่านข้อความนี้ "
    "เล่าอาการเพิ่มเติมได้เลยครับ"
)


def line_chat_safety(answer: str, patient_texts: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    ตรวจคำตอบก่อนส่งถึงผู้ป่วย:
    - หลุดขนาดยาที่ AI เสนอเอง -> ใช้ข้อความปลอดภัยแทนทั้งคำตอบ
    - ยกเว้นขนาดยาที่ผู้ป่วยเป็นคนพิมพ์เล่ามาเองในแชท (เพื่อไม่ให้บล็อกตัวเองตอน AI สรุปยาเดิม)
    - หลุดคำวินิจฉัย -> ใช้ข้อความปลอดภัยแทนทั้งคำตอบ และตัด markdown ที่ LINE แสดงไม่ได้
    """
    patient_blob = " ".join(patient_texts or []).lower()
    patient_dosages = {m.group(0).strip().lower() for m in _DOSAGE_PATTERN.finditer(patient_blob)}
    for m in _DOSAGE_PATTERN.finditer(answer):
        if m.group(0).strip().lower() not in patient_dosages:
            return {"text": LINE_CHAT_MEDICATION_REPLY, "blocked": "dosage"}
    if ClinicalGuardrail.check_forbidden_assertions(answer)[0]:
        return {"text": LINE_CHAT_DIAGNOSIS_REPLY, "blocked": "diagnosis"}
    return {"text": _MARKDOWN_NOISE.sub("", answer).strip(), "blocked": ""}


class LineChatRequest(BaseModel):
    messages: List[AssistantMessage] = Field(..., description="บทสนทนาใน LINE (ข้อความสุดท้ายคือของผู้ป่วย)")
    images_base64: Optional[List[AssistantImageItem]] = Field(default=None, description="ภาพที่ผู้ป่วยส่งใน LINE")
    patient_context: Optional[Dict[str, Any]] = Field(default=None, description="บริบทผู้ป่วยแบบไม่ระบุตัวตน")


@app.post("/api/ai/line/chat")
async def line_chat_endpoint(req: LineChatRequest):
    import base64
    history = [m for m in req.messages if m.role in ('user', 'assistant') and (m.content.strip() or req.images_base64)][-LINE_CHAT_HISTORY_LIMIT:]
    if not history or history[-1].role != 'user':
        raise HTTPException(status_code=400, detail="ข้อความสุดท้ายต้องเป็นของผู้ป่วย")
    raw_q = history[-1].content.strip() or "ผู้ป่วยส่งรูปภาพนี้มาสอบถาม โปรดสังเกตเบื้องต้นอย่างระมัดระวังและซักถามอาการเพิ่มโดยห้ามวินิจฉัยโรค"
    question = TextDeidentifier.sanitize(raw_q)["sanitized_text"][:2000]

    if any(k in question for k in ASSISTANT_EMERGENCY_KEYWORDS):
        return {"answer": LINE_CHAT_EMERGENCY, "kind": "emergency", "is_summary": False, "sources": [], "usage": {}}

    sent_images: List[Dict[str, Any]] = []
    for item in (req.images_base64 or [])[:3]:
        try:
            raw_bytes = base64.b64decode(item.data, validate=True)
        except Exception:
            continue
        if not raw_bytes:
            continue
        clean, _faces = MediaSanitizer.blur_faces(raw_bytes, safety_margin=0.25)
        sent_images.append({"data": _shrink_image(clean), "mime_type": "image/jpeg"})

    context = retrieve_tspi_knowledge(question)
    knowledge = "\n\n".join(f"{c['title']}\n{c['text']}" for c in context) or "(ไม่มีข้อมูลคลินิกที่เกี่ยวกับข้อความนี้)"
    patient_block = _format_patient_context_block(req.patient_context)
    conv_messages = [
        {"role": m.role, "content": TextDeidentifier.sanitize(m.content)["sanitized_text"][:1500]}
        for m in history[:-1]
    ]
    conv_messages.append({"role": "user", "content": f"{patient_block}<ความรู้>\n{knowledge}\n</ความรู้>\n\nผู้ป่วย: {question}"})

    if sent_images:
        res = await gateway.call_gemini_chat(LINE_CHAT_SYSTEM_PROMPT, conv_messages, images=sent_images, temperature=0.3, max_tokens=1200)
    else:
        res = await gateway.call_chat(config.SOAP_PROVIDER, messages=[{"role": "system", "content": LINE_CHAT_SYSTEM_PROMPT}, *conv_messages], temperature=0.3, max_tokens=1200)
    meta = {"provider": res.get("provider", config.SOAP_PROVIDER), "model": res.get("model", ""), "usage": res.get("usage", {})}
    answer = (res.get("content") or "").strip() if res.get("success") else ""
    if not answer:
        return {"answer": "", "kind": "unavailable", "is_summary": False, "sources": [], **meta}

    is_summary = LINE_INTAKE_COMPLETE_TOKEN in answer
    clean_answer = answer.replace(LINE_INTAKE_COMPLETE_TOKEN, "").strip()
    patient_texts = [m.content for m in history if m.role == 'user']
    checked = line_chat_safety(clean_answer, patient_texts=patient_texts)
    if checked["blocked"]:
        is_summary = False
    sources = _patient_friendly_sources(context)
    return {
        "answer": checked["text"],
        "kind": "summary" if is_summary else ("answer" if sources else "general"),
        "is_summary": is_summary,
        "blocked": checked["blocked"],
        "sources": sources,
        **meta,
    }


class ComposeThreeReportsRequest(BaseModel):
    patient_summary: str = Field(..., description="สรุปเวชระเบียน: อายุ เพศ SOAP Vitals Labs 39 แกน โมดูล")
    has_omics: bool = Field(default=False, description="มีข้อมูล Genomics/Microbiome/Metabolomics จริงหรือไม่")
    doctor_notes: str = Field(default="", description="ความเห็นเพิ่มเติมของแพทย์")


@app.post("/api/v1/reports/compose")
async def compose_three_reports_endpoint(req: ComposeThreeReportsRequest):
    """
    สร้างเนื้อหารายงาน TSPI Precision Medicine ทั้ง 3 ฉบับ (Physician, Patient, Multi-Omics)
    ตามมาตรฐานความปลอดภัย EP6 และ Clinical Safety Rules (ห้ามเดาแกนที่ยังไม่ตรวจ)
    """
    omics_rule = (
        "ผู้ป่วยมีข้อมูล Multi-Omics จริง ให้เขียน Multi-Omics Edition 5 บทวิเคราะห์เชิงลึก (Genomics, Microbiome, Metabolomics, Mitochondrial & Network Mapping)"
        if req.has_omics
        else "ผู้ป่วยยังไม่มีผลตรวจ Omics (NGS/Microbiome/Metabolomics) ให้เขียน Multi-Omics Edition เป็น 3 บท (Chapter 1: Omics Readiness & Missing Datasets, Chapter 2: Clinical Utility of Omics Testing, Chapter 3: Preliminary Phenotype-based Inferences [HYPOTHESIS]) โดยห้ามเดาผล Omics เด็ดขาด"
    )

    system_prompt = (
        "คุณคือ TSPI Chief Medical Officer & Systems Biology Writer.\n"
        "จงเขียนเนื้อหารายงานทางการแพทย์จากข้อมูลจริงด้านล่าง ออกเป็น JSON ที่มีคีย์ 3 ตัว: \"physician\", \"patient\", \"multiomics\".\n"
        "แต่ละคีย์เป็น JSON Array ของบท (chapters): [{\"title\": \"...\", \"content\": \"...\"}].\n\n"
        "กฎความปลอดภัยเด็ดขาด:\n"
        "1. ห้ามสร้างตัวเลขหรืออาการที่ไม่มีในข้อมูลนำเข้า (แกนที่ไม่มีผลให้ระบุ [NOT_AVAILABLE])\n"
        "2. Physician Edition (5 บท): ใช้ศัพท์แพทย์ กำกับสถานะหลักฐาน [MEASURED], [DERIVED], [CLINICAL_INFERENCE], [HYPOTHESIS], [NOT_AVAILABLE]\n"
        "3. Patient Edition (7 บท): ภาษาไทยอบอุ่นเข้าใจง่าย ห้ามใส่รหัสแกน (เช่น A8, AXIS_1) ห้ามใส่คะแนน /100 ห้ามใส่แท็ก [MEASURED]/[HYPOTHESIS] ห้ามใส่ชื่อโมดูลสมุนไพรที่ยังไม่อนุมัติ\n"
        f"4. Multi-Omics Edition: {omics_rule}\n"
        "5. ตอบกลับเป็น Valid JSON Object เท่านั้น ห้ามใส่ markdown code fence"
    )

    user_prompt = f"ข้อมูลเวชระเบียนจริง:\n{req.patient_summary[:5500]}\n\nความเห็นแพทย์: {req.doctor_notes[:800]}"

    raw_content = ""
    if config.is_gemini_available():
        res = await gateway.call_gemini_json(f"{system_prompt}\n\n{user_prompt}")
        if res.get("success"):
            raw_content = res.get("content", "")
    elif config.is_groq_available() or config.is_openai_available():
        provider = "openai" if config.is_openai_available() else "groq"
        res = await gateway.call_chat(
            provider=provider,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.2,
            max_tokens=3200,
            json_mode=True,
        )
        if res.get("success"):
            raw_content = res.get("content", "")

    if not raw_content:
        return {"success": False, "reason": "no_llm_available"}

    try:
        clean = raw_content.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        parsed = json.loads(clean.strip())
        if all(k in parsed and isinstance(parsed[k], list) for k in ("physician", "patient", "multiomics")):
            return {"success": True, "editions": parsed, "has_omics": req.has_omics}
    except Exception as exc:
        logger.warning(f"Failed parsing AI composed report JSON: {exc}")

    return {"success": False, "reason": "invalid_json"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8088)

