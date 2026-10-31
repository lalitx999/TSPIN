"""
ผู้ช่วย AI สำหรับผู้ป่วย (หน้าเว็บแบบ ChatGPT)
- ตอบจากฐานความรู้ของ TSPI ผ่าน AI service (/api/ai/assistant/chat) นอกเรื่องปฏิเสธ
- มีหลายห้องแชท: สร้าง/เปลี่ยนชื่อ/ลบ; ห้องที่ส่งให้คลินิกแล้วลบจริงไม่ได้ (ซ่อนได้) เพราะเป็นเวชระเบียน
- "ส่งให้คลินิก" สร้างกล่องรอบซักประวัติ (Box) ให้บุคลากรเปิดในเมนูซักถาม
"""

import json
import logging

import httpx
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import AuditLog
from clinical import services_intake
from clinical.models import Box
from intelligence import ai_budget
from intelligence.models import AssistantMessage, AssistantThread
from portal_patient.views import get_current_patient

logger = logging.getLogger('tspi.portal.assistant')

DAILY_MESSAGE_LIMIT = 40
MAX_MESSAGE_LENGTH = 1500


def _thread_json(t: AssistantThread) -> dict:
    return {'id': t.pk, 'title': t.title, 'updated_at': t.updated_at.isoformat(), 'submitted': bool(t.submitted_box_id)}


def _message_json(m: AssistantMessage) -> dict:
    return {'id': m.pk, 'role': m.role, 'content': m.content, 'kind': m.kind, 'sources': m.sources,
            'created_at': m.created_at.isoformat()}


def _my_thread(request: HttpRequest, thread_id) -> AssistantThread:
    return get_object_or_404(AssistantThread, pk=thread_id, user=request.user, hidden_by_user=False)


def _body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return {}


@login_required
def assistant_page_view(request: HttpRequest):
    return render(request, 'portal_patient/assistant.html', {
        'has_patient_record': bool(get_current_patient(request.user)),
    })


@login_required
@require_GET
def assistant_threads_api(request: HttpRequest) -> JsonResponse:
    threads = AssistantThread.objects.filter(user=request.user, hidden_by_user=False)[:100]
    return JsonResponse({'threads': [_thread_json(t) for t in threads]})


@login_required
@require_POST
def assistant_new_thread_api(request: HttpRequest) -> JsonResponse:
    thread = AssistantThread.objects.create(user=request.user)
    return JsonResponse({'thread': _thread_json(thread)}, status=201)


@login_required
@require_GET
def assistant_thread_messages_api(request: HttpRequest, thread_id: int) -> JsonResponse:
    thread = _my_thread(request, thread_id)
    return JsonResponse({'thread': _thread_json(thread), 'messages': [_message_json(m) for m in thread.messages.all()]})


@login_required
@require_POST
def assistant_rename_api(request: HttpRequest, thread_id: int) -> JsonResponse:
    thread = _my_thread(request, thread_id)
    title = (_body(request).get('title') or '').strip()[:120]
    if not title:
        return JsonResponse({'error': 'กรุณาตั้งชื่อแชท'}, status=400)
    thread.title = title
    thread.save(update_fields=['title', 'updated_at'])
    return JsonResponse({'thread': _thread_json(thread)})


@login_required
@require_POST
def assistant_delete_api(request: HttpRequest, thread_id: int) -> JsonResponse:
    thread = _my_thread(request, thread_id)
    if thread.submitted_box_id:
        # ส่งให้คลินิกแล้วเป็นส่วนหนึ่งของเวชระเบียน: ซ่อนจากหน้าผู้ใช้เท่านั้น
        thread.hidden_by_user = True
        thread.save(update_fields=['hidden_by_user', 'updated_at'])
        return JsonResponse({'deleted': False, 'hidden': True})
    thread.delete()
    return JsonResponse({'deleted': True, 'hidden': False})


@login_required
@require_POST
def assistant_send_api(request: HttpRequest, thread_id: int) -> JsonResponse:
    thread = _my_thread(request, thread_id)
    text = (_body(request).get('text') or '').strip()
    if not text:
        return JsonResponse({'error': 'กรุณาพิมพ์ข้อความ'}, status=400)
    if len(text) > MAX_MESSAGE_LENGTH:
        return JsonResponse({'error': f'ข้อความยาวเกิน {MAX_MESSAGE_LENGTH} ตัวอักษร'}, status=400)

    quota_key = f"assistant_msgs_{request.user.pk}_{timezone.localdate():%Y%m%d}"
    used = cache.get(quota_key, 0)
    if used >= DAILY_MESSAGE_LIMIT:
        return JsonResponse({'error': 'วันนี้ส่งข้อความครบจำนวนแล้ว กรุณาลองใหม่พรุ่งนี้ หรือทักเจ้าหน้าที่ทาง LINE'}, status=429)
    cache.set(quota_key, used + 1, timeout=60 * 60 * 24)

    user_msg = AssistantMessage.objects.create(thread=thread, role='user', content=text)
    if thread.title == 'แชทใหม่':
        thread.title = text[:40] + ('…' if len(text) > 40 else '')

    provider = settings.AI_SOAP_PROVIDER
    allowed, budget_msg = ai_budget.check_budget(provider)
    data = {}
    if allowed:
        history = [{'role': m.role, 'content': m.content} for m in thread.messages.all()][-8:]
        try:
            resp = httpx.post(
                f"{settings.AI_SERVICE_URL}/api/ai/assistant/chat",
                json={'messages': history},
                headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
                timeout=45.0,
            )
            data = resp.json() if resp.status_code == 200 else {}
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(f"[Assistant] AI service error for thread {thread.pk}: {exc}")
        if any((data.get('usage') or {}).values()):
            ai_budget.record_usage(data.get('provider') or provider, data.get('model', ''), data['usage'],
                                   'patient_assistant', request.user)

    answer = data.get('answer') or (
        budget_msg if not allowed else 'ขออภัยค่ะ ระบบผู้ช่วยไม่พร้อมใช้งานชั่วคราว กรุณาลองใหม่ภายหลัง'
    )
    bot_msg = AssistantMessage.objects.create(
        thread=thread, role='assistant', content=answer,
        kind=data.get('kind', 'unavailable'), sources=data.get('sources', []),
    )
    thread.save(update_fields=['title', 'updated_at'])
    return JsonResponse({'thread': _thread_json(thread), 'messages': [_message_json(user_msg), _message_json(bot_msg)]})


@login_required
@require_POST
def assistant_submit_api(request: HttpRequest, thread_id: int) -> JsonResponse:
    """ส่งบทสนทนาให้คลินิก: สร้างกล่องรอบซักประวัติ (ช่องทางเว็บ) ให้บุคลากรเปิดดู สรุป SOAP และบันทึกเข้าเวชระเบียน"""
    thread = _my_thread(request, thread_id)
    if thread.submitted_box_id:
        return JsonResponse({'error': 'แชทนี้ส่งให้คลินิกแล้ว'}, status=409)
    patient = get_current_patient(request.user)
    if not patient:
        return JsonResponse({'error': 'บัญชีนี้ยังไม่ได้เชื่อมกับเวชระเบียนของคลินิก กรุณาติดต่อเจ้าหน้าที่'}, status=400)
    messages = list(thread.messages.all())
    if not any(m.role == 'user' for m in messages):
        return JsonResponse({'error': 'ยังไม่มีข้อความในแชทนี้'}, status=400)

    box = Box.objects.create(
        patient=patient, source=Box.Source.WEB, status=Box.Status.DRAFT,
        contents={'messages': [], 'soap': {}, 'soap_source': 'none', 'origin': 'patient_assistant',
                  'assistant_thread_id': thread.pk},
        last_activity_at=timezone.now(),
    )
    for m in messages:
        services_intake.append_message(box, 'text', text=m.content, sender='patient' if m.role == 'user' else 'bot')
    services_intake.close_session(box, reason='patient_submitted')

    thread.submitted_box = box
    thread.save(update_fields=['submitted_box', 'updated_at'])
    AuditLog.objects.create(user=request.user, action='ASSISTANT_THREAD_SUBMITTED', model='Box', object_id=str(box.id),
                            changes={'thread_id': thread.pk, 'patient_hn': patient.hn, 'messages': len(messages)})
    return JsonResponse({'thread': _thread_json(thread)})
