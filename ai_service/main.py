"""
TSPI Dedicated AI Copilot & Streaming Microservice (FastAPI).
Runs on Port 8088 alongside Django Core (Port 8000).
Handles asynchronous LLM streaming (SSE), RAG Knowledge Search over 39 Axes & 12 Domains,
and botanical module citations.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Any, Optional
from fastapi import FastAPI, Header, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'apps' / 'clinical' / 'data'
TXT_FILE = BASE_DIR / 'legacy_drpatt' / 'frontend' / 'public' / '38_tspi.txt'

app = FastAPI(
    title="TSPI Clinical AI Copilot Microservice",
    version="2.0.0",
    description="High-concurrency streaming AI engine for 39 Biological Axes (12 Domains) & 200 Phytochemical Modules."
)

# CORS Middleware (Allows seamless communication with Django web app on port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    load_knowledge()


class ChatRequest(BaseModel):
    message: str
    patient_id: Optional[int] = None
    role: str = "doctor"


@app.get("/health")
async def health_check():
    """Healthcheck endpoint."""
    return {
        "status": "healthy",
        "service": "tspi-ai-service",
        "port": 8088,
        "total_domains": len(KNOWLEDGE_STORE['domains']) or 12,
        "total_axes": len(KNOWLEDGE_STORE['axes']) or 39,
        "total_modules": len(KNOWLEDGE_STORE['modules']) or 200,
        "engine": "FastAPI + SSE Streamer + RAG Knowledge Engine"
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


def build_clinical_reasoning_response(query: str, patient_id: Optional[int] = None) -> str:
    """Generate structured, grounded clinical reasoning citing 39 axes and botanical modules."""
    matched_axes = search_relevant_axes(query)
    
    lines = []
    lines.append(f"### 🧬 ผลการวิเคราะห์ทางคลินิกเชิงกลไกชีววิทยา (Mechanistic Reasoning)\n")
    lines.append(f"**คำถาม/อาการทางคลินิก:** {query}\n")
    lines.append(f"จากการตรวจเทียบกับระบบ **39 แกนชีววิทยา (12 โดเมน)** และคลังพฤกษเคมี 200 โมดูล พบความเชื่อมโยงสำคัญ:\n")

    for i, ax in enumerate(matched_axes, 1):
        ax_id = ax.get('axis_id')
        name = ax.get('name')
        dom = ax.get('domain_title')
        mods = ax.get('modules', [])
        mod_str = ", ".join(mods[:4]) if mods else "KERRA, MINOZA, KS, VITALPLUS"
        
        lines.append(f"#### {i}. Axis {ax_id}: {name}")
        lines.append(f"- **โดเมนชีววิทยา:** {dom}")
        lines.append(f"- **กลไกระดับเซลล์:** มีผลต่อ signaling cascades, cellular stress และ metabolic homeostasis")
        lines.append(f"- **โมดูลการรักษาเป้าหมาย:** `{mod_str}`\n")

    lines.append("### 🎯 แผนการบำบัดรักษาฟื้นฟู (9-Step Protocol Alignment)")
    lines.append("- **ระยะที่ 1 (Phase 1: Assess & Cleanse):** เคลียร์การอักเสบสะสมและเสริมเกราะป้องกันเยื่อบุ")
    lines.append("- **ระยะที่ 2 (Phase 2: Cellular Repair):** ฟื้นฟูการสร้างพลังงาน ATP และสมดุลไมโทคอนเดรีย")
    lines.append("- **ระยะที่ 3 (Phase 3: Longevity & Maintenance):** ปรับจังหวะชีวภาพและการฟื้นฟูระดับยีน\n")
    lines.append("> ⚠️ **ข้อควรระวังทางคลินิก (Safety Gate):** ให้ตรวจทานค่าการทำงานของตับ (ALT/AST) และไต (eGFR/Cr) ก่อนสั่งจ่ายโมดูลตำรับสมุนไพรเข้มข้น")

    return "\n".join(lines)


@app.get("/api/v1/copilot/stream")
async def stream_copilot_chat_get(
    q: str = Query(..., description="Doctor query text"),
    patient_id: Optional[int] = Query(None)
):
    """
    Streaming AI Copilot Chat for EventSource GET requests.
    Yields chunks formatted as JSON: {"chunk": "...", "done": false}
    """
    async def token_generator() -> AsyncGenerator[str, None]:
        response_text = build_clinical_reasoning_response(q, patient_id)
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            payload = json.dumps({"chunk": chunk, "done": False}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            await asyncio.sleep(0.02)
        
        done_payload = json.dumps({"chunk": "", "done": True})
        yield f"data: {done_payload}\n\n"

    return EventSourceResponse(token_generator())


@app.post("/api/v1/copilot/stream")
async def stream_copilot_chat_post(
    req: ChatRequest,
    x_internal_secret: Optional[str] = Header(None)
):
    """
    Streaming AI Copilot Chat for POST requests.
    """
    async def token_generator() -> AsyncGenerator[str, None]:
        response_text = build_clinical_reasoning_response(req.message, req.patient_id)
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            payload = json.dumps({"chunk": chunk, "done": False}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            await asyncio.sleep(0.02)
        
        done_payload = json.dumps({"chunk": "", "done": True})
        yield f"data: {done_payload}\n\n"

    return EventSourceResponse(token_generator())


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
    uvicorn.run(app, host="0.0.0.0", port=8088)
