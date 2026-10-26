"""
TSPI AI Copilot Streaming Views & Internal Proxy (Option 4).
Enforces Doctor-Only RBAC (HTTP 403), Rate Limiting (10 req/min per Doctor),
Grounded Context Injection via CopilotContextBuilder, and High-Performance SSE Streaming.
"""

import os
import json
import logging
from typing import Generator
import httpx
from django.http import StreamingHttpResponse, JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django_ratelimit.decorators import ratelimit

from accounts.decorators import doctor_only
from accounts.models import AuditLog
from accounts.views import get_client_ip
from clinical.services.copilot import CopilotContextBuilder

logger = logging.getLogger('tspi.clinical.copilot')

AI_SERVICE_URL = os.environ.get('AI_SERVICE_URL', 'http://127.0.0.1:8088')
INTERNAL_API_TOKEN = os.environ.get('INTERNAL_API_TOKEN', 'tspi-internal-secret-token-2026')


@doctor_only
@ratelimit(key='user', rate='10/m', block=False)
@require_http_methods(["POST"])
def copilot_stream_chat_view(request):
    """
    Streaming AI Copilot Chat for Doctors (SSE Endpoint).
    Proxy to FastAPI Microservice on port 8088 with Patient Grounding Context & Rate Limiting.
    """
    # 1. Check Rate Limit (10 req/min)
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        logger.warning(f"[Copilot] Doctor {request.user.username} exceeded rate limit (10/min)")
        return JsonResponse(
            {
                "error": "คุณส่งคำถามเกินกำหนด (จำกัด 10 ครั้ง/นาที) กรุณารอสักครู่ก่อนลองใหม่อีกครั้ง",
                "status": 429
            },
            status=429
        )

    # 2. Parse Request Data
    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = {}

    user_query = body.get('message', '').strip()
    if not user_query:
        user_query = request.POST.get('message', '').strip()

    if not user_query:
        return JsonResponse({"error": "กรุณาระบุข้อความคำถาม"}, status=400)

    patient_id = body.get('patient_id') or request.POST.get('patient_id')
    try:
        patient_id = int(patient_id) if patient_id else None
    except (ValueError, TypeError):
        patient_id = None

    # 3. Build Grounded Clinical Context (Single Source of Truth)
    ctx_data = CopilotContextBuilder.build_context(patient_id=patient_id)

    # 4. Audit Log
    AuditLog.objects.create(
        user=request.user,
        action="COPILOT_STREAM_QUERY",
        model="CopilotQuery",
        object_id=str(patient_id or "GENERAL"),
        changes={
            "query": user_query[:100],
            "patient_hn": ctx_data.get('patient_hn'),
            "scored_axes_count": ctx_data.get('scored_axes_count', 0),
        },
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    # 5. Generator yielding SSE Tokens from FastAPI
    def sse_proxy_generator() -> Generator[str, None, None]:
        fastapi_url = f"{AI_SERVICE_URL}/api/v1/copilot/stream"
        payload = {
            "message": user_query,
            "patient_id": patient_id,
            "patient_hn": ctx_data.get('patient_hn'),
            "context": ctx_data.get('context_text'),
            "role": "doctor"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Internal-Secret": INTERNAL_API_TOKEN,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                with client.stream("POST", fastapi_url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        err_chunk = json.dumps({
                            "chunk": f"⚠️ ไม่สามารถเชื่อมต่อ AI Service ได้ (HTTP {response.status_code}) กรุณาลองใหม่",
                            "done": True
                        }, ensure_ascii=False)
                        yield f"data: {err_chunk}\n\n"
                        return

                    for line in response.iter_lines():
                        if line:
                            yield f"{line}\n\n"

        except (httpx.ConnectError, httpx.TimeoutException, Exception) as exc:
            logger.error(f"[Copilot Proxy Error] Connection failed to FastAPI: {exc}")
            # Graceful Degradation (Checklist Phase 3)
            fallback_payload = json.dumps({
                "chunk": "⚠️ ระบบ AI Copilot ขัดข้องชั่วคราว ไม่สามารถเชื่อมต่อระบบประมวลผลได้ในขณะนี้ กรุณาตรวจสอบข้อมูลผลแล็บและ 39 แกนชีววิทยาจากหน้า Dashboard โดยตรง",
                "done": True
            }, ensure_ascii=False)
            yield f"data: {fallback_payload}\n\n"

    # 6. Return StreamingHttpResponse with no-buffering headers
    stream_response = StreamingHttpResponse(
        sse_proxy_generator(),
        content_type='text/event-stream'
    )
    stream_response['X-Accel-Buffering'] = 'no'
    stream_response['Cache-Control'] = 'no-cache'
    stream_response['Connection'] = 'keep-alive'
    return stream_response
