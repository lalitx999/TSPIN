"""
ส่งต่อ Webhook ให้ระบบเก่า: OA หนึ่งตัวตั้ง webhook ได้ URL เดียว เมื่อชี้มาที่ TSPI ระบบเก่าต้องได้ข้อความผ่านทางนี้
ไม่ส่งข้อความของคนที่เปิดบอทเรา เพราะ reply token ใช้ได้ครั้งเดียว และลูกค้าจะได้คำตอบจากสองบอทซ้อนกัน
"""

import base64
import hashlib
import hmac
import json
import logging
import threading

import httpx
from django.conf import settings

from patients.line_service import LineFlexMessageBuilder, is_bot_off_word, is_bot_on_word
from patients.models_line import LineUser, bot_idle_cutoff
from patients.views_line_internal import detect_clinical_intent

logger = logging.getLogger(__name__)

RELAY_TIMEOUT_SECONDS = 5
RELAY_ATTEMPTS = 2


def events_for_old_system(events: list) -> list:
    """เลือก event ที่ระบบเก่าควรได้ ไล่ตามลำดับ เพราะคนเดียวอาจเปิดหรือปิดบอทกลาง batch"""
    user_ids = {(e.get('source') or {}).get('userId') for e in events}
    # กฎเดียวกับ LineUser.is_bot_on: เงียบเกินเวลาแล้วนับว่าปิด ข้อความนี้จึงไปถึงระบบเก่า
    enabled = set(LineUser.objects.filter(line_user_id__in=user_ids, bot_enabled=True,
                                          bot_last_active_at__gte=bot_idle_cutoff())
                  .values_list('line_user_id', flat=True))

    forwarded = []
    for event in events:
        if event.get('type') not in ('message', 'postback'):
            forwarded.append(event)  # follow, unfollow ฯลฯ บอทเราไม่ตอบ ไม่ชนกับระบบเก่า
            continue

        user_id = (event.get('source') or {}).get('userId')
        message = event.get('message') or {}
        text = (message.get('text') or '').strip() if message.get('type') == 'text' else ''
        if is_bot_on_word(text):
            enabled.add(user_id)
        elif user_id not in enabled:
            # บอทเราตอบเตือนฉุกเฉินแม้บอทปิด reply token ใช้ได้ครั้งเดียว จึงไม่ส่งข้อความนี้ต่อ
            if not detect_clinical_intent(text)[1]:
                forwarded.append(event)
        elif (is_bot_off_word(text)
              or (event.get('postback') or {}).get('data') == LineFlexMessageBuilder.BOT_OFF_POSTBACK):
            enabled.discard(user_id)
    return forwarded


def relay_to_old_system(raw_body: bytes, signature: str, data: dict) -> None:
    """คำนวณสิ่งที่จะส่งก่อนบอทเปลี่ยนสถานะ แล้วส่งแบบไม่รอ เพื่อให้ตอบ LINE ทันเวลา"""
    url = settings.LINE_RELAY_URL
    if not url:
        return
    events = events_for_old_system(data['events'])
    if not events:
        return
    if len(events) != len(data['events']):
        # เนื้อหาเปลี่ยน ต้องเซ็นใหม่ด้วย secret เดียวกัน ระบบเก่าจึงตรวจลายเซ็นผ่าน
        raw_body = json.dumps({**data, 'events': events}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        digest = hmac.new(settings.LINE_CHANNEL_SECRET.encode('utf-8'), raw_body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode('utf-8')
    _deliver_in_background(url, raw_body, signature)


def _deliver_in_background(url: str, body: bytes, signature: str) -> None:
    threading.Thread(target=_deliver, args=(url, body, signature), daemon=True).start()


def _deliver(url: str, body: bytes, signature: str) -> bool:
    headers = {'Content-Type': 'application/json', 'X-Line-Signature': signature, 'User-Agent': 'LineBotWebhook/2.0'}
    failure = ''
    for _ in range(RELAY_ATTEMPTS):
        try:
            response = httpx.post(url, content=body, headers=headers, timeout=RELAY_TIMEOUT_SECONDS)
        except httpx.HTTPError as e:
            failure = type(e).__name__
            continue
        if response.status_code < 500:
            if response.status_code >= 400:
                logger.error(f"[LINE Relay] Old system rejected events: HTTP {response.status_code}")
            return response.status_code < 400
        failure = f"HTTP {response.status_code}"
    logger.error(f"[LINE Relay] Could not deliver events to old system: {failure}")
    return False
