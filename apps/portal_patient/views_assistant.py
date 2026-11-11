"""
ผู้ช่วย AI สำหรับผู้ป่วย (หน้าเว็บแบบ ChatGPT / Gemini)
- ตอบจากฐานความรู้ของ TSPI ผ่าน AI service (/api/ai/assistant/chat) นอกเรื่องปฏิเสธ
- คนไข้ที่เข้าสู่ระบบแล้วคุยได้ต่อเนื่อง รองรับข้อความ รูปภาพ และคลิปเสียง (เข้ารหัสใน PRIVATE_MEDIA_ROOT)
- ยังไม่รองรับวิดีโอเพื่อประหยัดพื้นที่จัดเก็บ
- มีหลายห้องแชท: สร้าง/เปลี่ยนชื่อ/ลบ; ห้องที่ส่งให้คลินิกแล้วลบจริงไม่ได้ (ซ่อนได้) เพราะเป็นเวชระเบียน
- "ส่งให้คลินิก" สร้างกล่องรอบซักประวัติ (Box) ให้บุคลากรเปิดในเมนูซักถาม พร้อมรูปและเสียงแนบ
"""

import base64
import json
import logging

import httpx
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import AuditLog, User
from accounts.views import get_client_ip
from clinical import media_store, services_intake
from clinical.models import Box
from intelligence import ai_budget
from intelligence.models import AssistantMessage, AssistantThread
from portal_patient.views import get_current_patient

logger = logging.getLogger('tspi.portal.assistant')

MAX_MESSAGE_LENGTH = 1500
BURST_LIMIT_PER_MINUTE = 25
MAX_IMAGES_PER_MESSAGE = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_AUDIO_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_AUDIO_TYPES = {
    'audio/webm', 'audio/ogg', 'audio/mpeg', 'audio/mp3',
    'audio/mp4', 'audio/m4a', 'audio/x-m4a', 'audio/wav', 'audio/x-wav', 'audio/aac',
}


def _clean_mime(content_type: str) -> str:
    return (content_type or '').split(';')[0].strip().lower()


def _public_attachments(m: AssistantMessage) -> list:
    out = []
    for att in (m.attachments or []):
        if not isinstance(att, dict) or not att.get('media_id'):
            continue
        out.append({
            'kind': att.get('kind', 'image'),
            'media_id': att['media_id'],
            'content_type': att.get('content_type', ''),
            'size': att.get('size', 0),
            'transcript': att.get('transcript', ''),
            'url': reverse('portal_patient:assistant_media', args=[m.pk, att['media_id']]),
        })
    return out


def _thread_json(t: AssistantThread) -> dict:
    return {'id': t.pk, 'title': t.title, 'updated_at': t.updated_at.isoformat(), 'submitted': bool(t.submitted_box_id)}


def _message_json(m: AssistantMessage) -> dict:
    return {
        'id': m.pk,
        'role': m.role,
        'content': m.content,
        'kind': m.kind,
        'sources': m.sources,
        'attachments': _public_attachments(m),
        'created_at': m.created_at.isoformat(),
    }


def _my_thread(request: HttpRequest, thread_id) -> AssistantThread:
    return get_object_or_404(AssistantThread, pk=thread_id, user=request.user, hidden_by_user=False)


def _body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return {}


@login_required
def assistant_page_view(request: HttpRequest):
    patient = get_current_patient(request.user)
    display_name = (
        patient.full_name if patient
        else (request.user.get_full_name() or request.user.first_name or request.user.username)
    )
    active_thread_id = request.GET.get('thread', '')
    return render(request, 'portal_patient/assistant.html', {
        'has_patient_record': bool(patient),
        'patient_display_name': display_name,
        'patient_hn': patient.hn if patient else '',
        'active_thread_id': active_thread_id if str(active_thread_id).isdigit() else '',
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

    # รองรับทั้ง JSON (ข้อความอย่างเดียว) และ multipart/form-data (ข้อความ + รูปภาพ + คลิปเสียง)
    is_multipart = (request.content_type or '').startswith('multipart/form-data')
    if is_multipart:
        text = (request.POST.get('text') or '').strip()
        image_files = request.FILES.getlist('images')
        audio_file = request.FILES.get('audio')
    else:
        text = (_body(request).get('text') or '').strip()
        image_files = []
        audio_file = None

    if len(text) > MAX_MESSAGE_LENGTH:
        return JsonResponse({'error': f'ข้อความยาวเกิน {MAX_MESSAGE_LENGTH} ตัวอักษร'}, status=400)

    # ป้องกันไฟล์วิดีโอ (ยังไม่รองรับตามนโยบายประหยัดพื้นที่)
    for f in list(image_files) + ([audio_file] if audio_file else []):
        if f and _clean_mime(getattr(f, 'content_type', '')).startswith('video/'):
            return JsonResponse({'error': 'ยังไม่รองรับการส่งไฟล์วิดีโอ กรุณาส่งเป็นข้อความ รูปภาพ หรือคลิปเสียง'}, status=400)

    if len(image_files) > MAX_IMAGES_PER_MESSAGE:
        return JsonResponse({'error': f'ส่งรูปได้สูงสุด {MAX_IMAGES_PER_MESSAGE} รูปต่อครั้ง'}, status=400)

    # ตรวจไฟล์รูปภาพและเสียงก่อนบันทึก
    validated_images = []
    for img in image_files:
        mime = _clean_mime(getattr(img, 'content_type', ''))
        if mime not in ALLOWED_IMAGE_TYPES:
            return JsonResponse({'error': 'รองรับเฉพาะรูปภาพ JPG, PNG หรือ WEBP'}, status=400)
        if img.size > MAX_IMAGE_BYTES:
            return JsonResponse({'error': 'รูปภาพแต่ละรูปต้องมีขนาดไม่เกิน 5 MB'}, status=400)
        raw = img.read()
        if raw:
            validated_images.append((raw, mime))

    validated_audio = None
    if audio_file:
        mime = _clean_mime(getattr(audio_file, 'content_type', ''))
        if mime not in ALLOWED_AUDIO_TYPES:
            return JsonResponse({'error': 'รูปแบบไฟล์เสียงไม่รองรับ กรุณาอัดเสียงใหม่หรือใช้ MP3 / M4A / WAV / OGG'}, status=400)
        if audio_file.size > MAX_AUDIO_BYTES:
            return JsonResponse({'error': 'ไฟล์เสียงต้องมีขนาดไม่เกิน 10 MB'}, status=400)
        raw_audio = audio_file.read()
        if raw_audio:
            validated_audio = (raw_audio, 'audio/mpeg' if mime == 'audio/mp3' else mime)

    if not text and not validated_images and not validated_audio:
        return JsonResponse({'error': 'กรุณาพิมพ์ข้อความ แนบรูปภาพ หรืออัดเสียง'}, status=400)

    # กันการส่งถี่ผิดปกติ (Burst guard) แต่ไม่จำกัดจำนวนครั้งต่อวันสำหรับคนไข้
    burst_key = f"assistant_burst_{request.user.pk}"
    burst = int(cache.get(burst_key, 0) or 0)
    if burst >= BURST_LIMIT_PER_MINUTE:
        return JsonResponse({'error': 'ส่งข้อความถี่เกินไป กรุณารอสักครู่แล้วลองใหม่'}, status=429)
    cache.set(burst_key, burst + 1, timeout=60)

    # เข้ารหัสเก็บไฟล์แนบลง PRIVATE_MEDIA_ROOT
    attachments = []
    images_b64 = []
    for raw_img, mime in validated_images:
        meta = media_store.save_encrypted(raw_img, mime, 'assistant')
        meta['kind'] = 'image'
        attachments.append(meta)
        images_b64.append({'data': base64.b64encode(raw_img).decode('ascii'), 'mime_type': mime})

    audio_transcript = ''
    if validated_audio:
        raw_aud, mime = validated_audio
        meta = media_store.save_encrypted(raw_aud, mime, 'assistant')
        meta['kind'] = 'audio'
        try:
            vresp = httpx.post(
                f"{settings.AI_SERVICE_URL}/api/intake/voice",
                files={'file': ('voice' + media_store.EXTENSIONS.get(mime, '.webm'), raw_aud, mime)},
                data={'consent_granted': 'true'},
                headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
                timeout=45.0,
            )
            if vresp.status_code == 200:
                vdata = vresp.json()
                if vdata.get('success') and not vdata.get('simulated'):
                    audio_transcript = (vdata.get('sanitized_transcript') or '').strip()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(f"[Assistant] Voice transcribe error for thread {thread.pk}: {exc}")
        if audio_transcript:
            meta['transcript'] = audio_transcript
        attachments.append(meta)

    display_text = text
    if audio_transcript:
        display_text = f"{text}\n\n[ถอดความจากเสียง] {audio_transcript}".strip() if text else audio_transcript
    elif validated_audio and not text:
        display_text = "[ส่งคลิปเสียง]"
    elif validated_images and not display_text:
        display_text = f"[ส่งรูปภาพ {len(validated_images)} รูป]"

    user_msg = AssistantMessage.objects.create(
        thread=thread,
        role='user',
        content=display_text,
        attachments=attachments,
    )
    if thread.title == 'แชทใหม่':
        title_src = display_text.replace('[ส่งคลิปเสียง]', 'สอบถามด้วยเสียง').replace('[ส่งรูปภาพ', 'สอบถามจากรูปภาพ')
        thread.title = title_src[:40] + ('…' if len(title_src) > 40 else '')

    provider = settings.AI_SOAP_PROVIDER
    allowed, budget_msg = ai_budget.check_budget(provider)
    data = {}
    if allowed:
        history = [{'role': m.role, 'content': m.content} for m in thread.messages.all()][-8:]
        patient_ctx = services_intake.build_anonymous_patient_context(get_current_patient(request.user))
        payload = {'messages': history}
        if patient_ctx:
            payload['patient_context'] = patient_ctx
        if images_b64:
            payload['images_base64'] = images_b64
        try:
            resp = httpx.post(
                f"{settings.AI_SERVICE_URL}/api/ai/assistant/chat",
                json=payload,
                headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
                timeout=60.0 if images_b64 else 45.0,
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
@require_GET
def assistant_media_view(request: HttpRequest, message_id: int, media_id: str) -> HttpResponse:
    """เปิดดูภาพหรือฟังคลิปเสียงแนบในแชท (เฉพาะเจ้าของห้องแชท หรือบุคลากรคลินิกเมื่อส่งเข้า Box แล้ว)"""
    msg = get_object_or_404(AssistantMessage.objects.select_related('thread'), pk=message_id)
    is_owner = msg.thread.user_id == request.user.pk and not msg.thread.hidden_by_user
    is_clinical = (
        getattr(request.user, 'role', None) in (User.Role.DOCTOR, User.Role.NURSE, User.Role.STAFF, User.Role.ADMIN)
        or request.user.is_staff
    ) and bool(msg.thread.submitted_box_id)
    if not (is_owner or is_clinical):
        raise Http404

    meta = next((a for a in (msg.attachments or []) if isinstance(a, dict) and a.get('media_id') == media_id), None)
    data = media_store.read_decrypted(meta) if meta else None
    if data is None:
        raise Http404

    content_type = meta.get('content_type', 'application/octet-stream')
    AuditLog.objects.create(
        user=request.user,
        action='ASSISTANT_MEDIA_VIEWED',
        model='AssistantMessage',
        object_id=str(msg.pk),
        changes={'media_id': media_id, 'content_type': content_type},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    response = HttpResponse(data, content_type=content_type)
    response['Cache-Control'] = 'no-store'
    response['Content-Disposition'] = 'inline'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


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
        sender = 'patient' if m.role == 'user' else 'bot'
        if m.content:
            services_intake.append_message(box, 'text', text=m.content, sender=sender)
        for att in (m.attachments or []):
            if isinstance(att, dict) and att.get('media_id'):
                services_intake.append_message(
                    box,
                    att.get('kind', 'image'),
                    text=att.get('transcript', ''),
                    media=att,
                    sender=sender,
                )
    services_intake.close_session(box, reason='patient_submitted')

    thread.submitted_box = box
    thread.save(update_fields=['submitted_box', 'updated_at'])
    AuditLog.objects.create(user=request.user, action='ASSISTANT_THREAD_SUBMITTED', model='Box', object_id=str(box.id),
                            changes={'thread_id': thread.pk, 'patient_hn': patient.hn, 'messages': len(messages)})
    return JsonResponse({'thread': _thread_json(thread)})
