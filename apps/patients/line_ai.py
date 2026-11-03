"""
ตอบคำถามสุขภาพใน LINE ด้วยผู้ช่วย AI ตัวเดียวกับหน้าเว็บ (เอกสารคลินิกก่อน แล้วค่อยใช้ DeepSeek/Gemini/Groq ตามที่ตั้งไว้)
AI ใช้เวลาหลายวินาที จึงทำนอก request เพื่อให้ตอบ webhook ของ LINE ได้ทันที
"""

import logging
import threading
import uuid
from datetime import timedelta

import httpx
from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.utils import timezone

from intelligence import ai_budget
from patients.line_service import LineFlexMessageBuilder, LineMessagingService
from patients.models_line import CommunicationRecord, LineUser

logger = logging.getLogger(__name__)

DAILY_LIMIT_PER_USER = 30
HISTORY_MESSAGES = 8
HISTORY_WINDOW = timedelta(minutes=30)
MAX_ANSWER_CHARS = 3500
UNAVAILABLE_TEXT = 'ขออภัยครับ ตอนนี้ผู้ช่วย AI ไม่พร้อมใช้งาน ลองใหม่อีกครั้ง หรือกดปิดบอทแล้วฝากข้อความถึงเจ้าหน้าที่ได้ครับ'


def answer_question(line_user_id: str, patient, text: str, reply_token: str) -> None:
    _run_in_background(_answer, line_user_id, patient, text, reply_token)


def _run_in_background(func, *args) -> None:
    def run():
        try:
            func(*args)
        finally:
            connections.close_all()  # thread นี้มี connection ของตัวเอง ต้องปิดเอง
    threading.Thread(target=run, daemon=True).start()


def _answer(line_user_id: str, patient, text: str, reply_token: str) -> None:
    try:
        LineMessagingService.show_loading(line_user_id)
        line_user = LineUser.objects.get(line_user_id=line_user_id)
        card = _limit_card() if _over_daily_limit(line_user_id) else _ask_ai(line_user, patient, text)
        if not LineMessagingService.reply_message(reply_token, [card]):
            LineMessagingService.push_message(line_user_id, [card])
    except Exception as e:
        logger.error(f"[LINE AI] Failed to answer: {e}", exc_info=True)


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


def _ask_ai(line_user: LineUser, patient, text: str) -> dict:
    provider = settings.AI_SOAP_PROVIDER
    allowed, budget_msg = ai_budget.check_budget(provider)
    if not allowed:
        return _answer_card(budget_msg)
    try:
        response = httpx.post(
            f"{settings.AI_SERVICE_URL}/api/ai/assistant/chat",
            json={'messages': _history(line_user, text)},
            headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
            timeout=45.0,
        )
        data = response.json() if response.status_code == 200 else {}
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(f"[LINE AI] AI service error: {e}")
        data = {}
    if any((data.get('usage') or {}).values()):
        ai_budget.record_usage(data.get('provider') or provider, data.get('model', ''), data['usage'], 'line_assistant')

    answer = data.get('answer')
    if not answer:
        return _answer_card(UNAVAILABLE_TEXT)
    # เก็บคำตอบไว้ให้เจ้าหน้าที่เห็นว่า AI บอกอะไรคนไข้ และใช้เป็นบริบทของคำถามถัดไป
    CommunicationRecord.objects.create(
        line_message_id=f"ai_{uuid.uuid4().hex[:24]}", line_user=line_user, patient=patient,
        direction=CommunicationRecord.DirectionChoices.OUTGOING,
        message_type=CommunicationRecord.MessageTypeChoices.TEXT, content=answer,
    )
    return _answer_card(answer, sources=data.get('sources') or [], emergency=data.get('kind') == 'emergency')


def _answer_card(answer: str, sources=(), emergency: bool = False) -> dict:
    body = answer if len(answer) <= MAX_ANSWER_CHARS else f"{answer[:MAX_ANSWER_CHARS]}…"
    if sources:
        body += '\n\nอ้างอิงเอกสารคลินิก:\n' + '\n'.join(f"[{i}] {title}" for i, title in enumerate(sources, 1))
    if emergency:
        return LineFlexMessageBuilder.build_bot_card('อาจเป็นภาวะฉุกเฉิน', body, danger=True, buttons=[
            LineFlexMessageBuilder.button_uri('โทร 1669', 'tel:1669', style='secondary')])
    return LineFlexMessageBuilder.build_bot_card('ผู้ช่วย AI ของคลินิก', body, buttons=[
        LineFlexMessageBuilder.button_message('เล่าอาการให้คลินิก', 'เริ่ม', style='secondary')])


def _limit_card() -> dict:
    return LineFlexMessageBuilder.build_bot_card(
        'วันนี้ถามครบจำนวนแล้ว', 'พรุ่งนี้ถาม AI ได้อีกครั้งครับ ระหว่างนี้กดเล่าอาการให้คลินิกได้',
        buttons=[LineFlexMessageBuilder.button_message('เล่าอาการให้คลินิก', 'เริ่ม', style='secondary')])
