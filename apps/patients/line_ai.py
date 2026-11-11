"""
แชทกับ AI ใน LINE แบบข้อความธรรมดา: AI ซักประวัติทีละคำถามและให้คำแนะนำทั่วไป ไม่วินิจฉัย
คำตอบต่อเข้ารอบแชท (Box) เดียวกับข้อความของผู้ป่วย หมอจึงอ่านทั้งบทสนทนาใน EMR ได้
AI ใช้เวลาหลายวินาที จึงทำนอก request เพื่อให้ตอบ webhook ของ LINE ได้ทันที
"""

import base64
import logging
import threading
import uuid
from datetime import timedelta

import httpx
from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.utils import timezone

from clinical import services_intake
from clinical.models import Box
from intelligence import ai_budget
from patients.line_service import LineFlexMessageBuilder, LineMessagingService, text_message
from patients.models_line import CommunicationRecord, LineUser

logger = logging.getLogger(__name__)

DAILY_LIMIT_PER_USER = 30
HISTORY_MESSAGES = 20
HISTORY_WINDOW = timedelta(hours=24)
MAX_ANSWER_CHARS = 3500
UNAVAILABLE_TEXT = 'ขออภัยครับ ตอนนี้ผู้ช่วย AI ไม่พร้อมใช้งาน ลองใหม่อีกครั้ง หรือพิมพ์ "ปิดบอท" แล้วฝากข้อความถึงเจ้าหน้าที่ได้ครับ'
LIMIT_TEXT = 'วันนี้คุยกับผู้ช่วย AI ครบจำนวนแล้วครับ พรุ่งนี้คุยต่อได้ ทีมแพทย์ยังอ่านข้อความที่ส่งมาได้ตามปกติ'
EMERGENCY_TEXT = (
    "หากมีอาการแน่นหน้าอก หายใจลำบาก หมดสติ หรือแขนขาอ่อนแรง กรุณาโทร 1669 หรือไปโรงพยาบาลที่ใกล้ที่สุดทันที\n"
    "ทีมแพทย์ได้รับแจ้งแล้วเช่นกัน"
)


def emergency_card(closable: bool = True) -> dict:
    """การ์ดเดียวที่ยังใช้ในแชท นอกจากลิงก์ลงทะเบียน: ต้องเด่นและมีปุ่มโทรทันที"""
    return LineFlexMessageBuilder.build_bot_card('อาจเป็นภาวะฉุกเฉิน', EMERGENCY_TEXT, danger=True, closable=closable,
                                                 buttons=[LineFlexMessageBuilder.button_uri('โทร 1669', 'tel:1669', style='secondary')])


def answer_question(line_user_id: str, patient, text: str, reply_token: str, box_id=None) -> None:
    _run_in_background(_answer, line_user_id, patient, text, reply_token, box_id)


def answer_voice(line_user_id: str, patient, audio: bytes, content_type: str, reply_token: str, box_id,
                 message_id: str) -> None:
    """ข้อความเสียง: ถอดเป็นตัวอักษรก่อน แล้วตอบเหมือนข้อความที่พิมพ์มา"""
    _run_in_background(_answer_voice, line_user_id, patient, audio, content_type, reply_token, box_id, message_id)


def answer_image(line_user_id: str, patient, image_bytes: bytes, content_type: str, reply_token: str, box_id) -> None:
    """รูปภาพจาก LINE: ส่งให้ AI ช่วยสังเกตเบื้องต้นและซักประวัติเพิ่ม (ไม่วินิจฉัย) พร้อมตอบเป็น Flex Card"""
    _run_in_background(_answer_image, line_user_id, patient, image_bytes, content_type, reply_token, box_id)


def _run_in_background(func, *args) -> None:
    def run():
        try:
            func(*args)
        finally:
            connections.close_all()  # thread นี้มี connection ของตัวเอง ต้องปิดเอง
    threading.Thread(target=run, daemon=True).start()


def _send(line_user_id: str, reply_token: str, message: dict) -> None:
    if not LineMessagingService.reply_message(reply_token, [message]):
        LineMessagingService.push_message(line_user_id, [message])


def _answer(line_user_id: str, patient, text: str, reply_token: str, box_id=None) -> None:
    try:
        LineMessagingService.show_loading(line_user_id)
        line_user = LineUser.objects.get(line_user_id=line_user_id)
        message = text_message(LIMIT_TEXT) if _over_daily_limit(line_user_id) else _ask_ai(line_user, patient, text, box_id)
        _send(line_user_id, reply_token, message)
    except Exception as e:
        logger.error(f"[LINE AI] Failed to answer: {e}", exc_info=True)


def _answer_voice(line_user_id: str, patient, audio: bytes, content_type: str, reply_token: str, box_id,
                  message_id: str) -> None:
    try:
        LineMessagingService.show_loading(line_user_id)
        transcript = transcribe(audio, content_type)
        if not transcript:
            _send(line_user_id, reply_token, text_message(
                'ได้รับข้อความเสียงแล้วครับ เก็บไว้ให้ทีมแพทย์ฟังแล้ว แต่ผู้ช่วยฟังเสียงนี้ไม่ได้ รบกวนพิมพ์เล่าสั้น ๆ ได้ไหมครับ'))
            return
        box = Box.objects.filter(pk=box_id).first()
        if box:
            _set_transcript(box, message_id, transcript)
        CommunicationRecord.objects.filter(line_message_id=message_id).update(content=transcript)
        _answer(line_user_id, patient, transcript, reply_token, box_id)
    except Exception as e:
        logger.error(f"[LINE AI] Failed to answer voice: {e}", exc_info=True)


def transcribe(audio: bytes, content_type: str) -> str:
    try:
        response = httpx.post(
            f"{settings.AI_SERVICE_URL}/api/intake/voice",
            files={'file': ('voice', audio, content_type or 'audio/m4a')},
            data={'consent_granted': 'true'},
            headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
            timeout=60.0,
        )
        data = response.json() if response.status_code == 200 else {}
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(f"[LINE AI] Voice transcription failed: {e}")
        return ''
    return (data.get('sanitized_transcript') or '').strip()


def _set_transcript(box: Box, message_id: str, transcript: str) -> None:
    contents = dict(box.contents or {})
    contents['messages'] = [{**m, 'text': transcript} if m.get('external_id') == message_id else m
                            for m in contents.get('messages', [])]
    box.contents = contents
    box.save(update_fields=['contents', 'signature'])


def _over_daily_limit(line_user_id: str) -> bool:
    key = f"line_ai_{line_user_id}_{timezone.localdate():%Y%m%d}"
    count = cache.get(key, 0)
    if count >= DAILY_LIMIT_PER_USER:
        return True
    cache.set(key, count + 1, timeout=60 * 60 * 24)
    return False


def _history(line_user: LineUser, text: str) -> list:
    """บทสนทนาล่าสุดจากประวัติแชท (ข้อความนี้ถูกบันทึกแล้วตอนรับ webhook)"""
    recent = CommunicationRecord.objects.filter(
        line_user=line_user, message_type=CommunicationRecord.MessageTypeChoices.TEXT,
        created_at__gte=timezone.now() - HISTORY_WINDOW,
    ).exclude(content='').order_by('-created_at')[:HISTORY_MESSAGES]
    history = [
        {'role': 'user' if m.direction == CommunicationRecord.DirectionChoices.INCOMING else 'assistant',
         'content': m.content[:1500]}
        for m in reversed(recent)
    ]
    if not history or history[-1] != {'role': 'user', 'content': text[:1500]}:
        history.append({'role': 'user', 'content': text[:1500]})
    return history


def _answer_image(line_user_id: str, patient, image_bytes: bytes, content_type: str, reply_token: str, box_id) -> None:
    try:
        LineMessagingService.show_loading(line_user_id)
        line_user = LineUser.objects.get(line_user_id=line_user_id)
        if _over_daily_limit(line_user_id):
            _send(line_user_id, reply_token, text_message(LIMIT_TEXT))
            return
        images_b64 = [{
            'data': base64.b64encode(image_bytes).decode('ascii'),
            'mime_type': content_type or 'image/jpeg',
        }]
        prompt_text = 'ผู้ป่วยส่งรูปภาพนี้มาสอบถาม โปรดสังเกตเบื้องต้นและซักถามอาการประกอบโดยห้ามวินิจฉัยโรค'
        message = _ask_ai(line_user, patient, prompt_text, box_id, images_b64=images_b64)
        _send(line_user_id, reply_token, message)
    except Exception as e:
        logger.error(f"[LINE AI] Failed to answer image: {e}", exc_info=True)


def _ask_ai(line_user: LineUser, patient, text: str, box_id=None, images_b64=None) -> dict:
    provider = settings.AI_SOAP_PROVIDER
    allowed, budget_msg = ai_budget.check_budget(provider)
    if not allowed:
        return text_message(budget_msg)
    payload = {'messages': _history(line_user, text)}
    patient_ctx = services_intake.build_anonymous_patient_context(patient)
    if patient_ctx:
        payload['patient_context'] = patient_ctx
    if images_b64:
        payload['images_base64'] = images_b64
    try:
        response = httpx.post(
            f"{settings.AI_SERVICE_URL}/api/ai/line/chat",
            json=payload,
            headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
            timeout=60.0 if images_b64 else 45.0,
        )
        data = response.json() if response.status_code == 200 else {}
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(f"[LINE AI] AI service error: {e}")
        data = {}
    if any((data.get('usage') or {}).values()):
        ai_budget.record_usage(data.get('provider') or provider, data.get('model', ''), data['usage'], 'line_chat')

    answer = (data.get('answer') or '').strip()
    if not answer:
        return text_message(UNAVAILABLE_TEXT)
    if len(answer) > MAX_ANSWER_CHARS:
        answer = f"{answer[:MAX_ANSWER_CHARS]}…"
    # เก็บคำตอบไว้ให้เจ้าหน้าที่เห็นว่า AI บอกอะไรคนไข้ และใช้เป็นบริบทของข้อความถัดไป
    CommunicationRecord.objects.create(
        line_message_id=f"ai_{uuid.uuid4().hex[:24]}", line_user=line_user, patient=patient,
        direction=CommunicationRecord.DirectionChoices.OUTGOING,
        message_type=CommunicationRecord.MessageTypeChoices.TEXT, content=answer,
    )
    is_emergency = data.get('kind') == 'emergency'
    is_summary = bool(data.get('is_summary') or data.get('kind') == 'summary')
    box = Box.objects.filter(pk=box_id).first() if box_id else None
    if box:
        # AI เจอคำฉุกเฉินที่ตัวกรองฝั่งเราไม่จับ: ติดธงไว้ให้รอบนี้ขึ้นบนสุดในรายการของหมอ
        services_intake.append_message(
            box, 'text', text=answer, sender='bot',
            red_flag=is_emergency, has_symptoms=is_summary,
        )
    if is_emergency:
        return emergency_card()
    return LineFlexMessageBuilder.build_assistant_reply(
        answer,
        kind=data.get('kind', 'answer'),
        sources=data.get('sources', []),
        is_summary=is_summary,
    )
