"""
TSPI Internal LINE Webhook Ingestion Controller.
Receives forwarded Webhook events from FastAPI Microservice (Port 8088).
Enforces:
1. Constant-Time Internal API Token Authentication (secrets.compare_digest)
2. Strict Event Deduplication with line_message_id / webhookEventId
3. Thai Negation-Aware Clinical & Urgent Keyword Detection
4. Human-in-the-Loop ClinicalReviewItem Queue Generation (Level 1 Nurse / Level 2 Doctor)
5. Zero Hallucination & Caregiver 1:N Patient Context Separation
"""

import json
import logging
import secrets
import re
from datetime import timedelta
from typing import Tuple, List, Optional

from django.conf import settings
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from patients.models import (
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
)
from accounts.models import AuditLog

logger = logging.getLogger('tspi.security')

# --------------------------------------------------------------------------
# Clinical & Urgent Keyword Dictionaries (Sorted by length descending)
# --------------------------------------------------------------------------
URGENT_KEYWORDS = [
    'หายใจไม่ออก',
    'แน่นหน้าอก',
    'หมดสติ',
    'ชักเกร็ง',
    'ปากเบี้ยว',
    'แพ้ยา',
    'ฉุกเฉิน',
    'ผลแล็บ',
]

CLINICAL_KEYWORDS = [
    'ความดัน',
    'ท้องเสีย',
    'น้ำตาล',
    'พยาบาล',
    'เลือด',
    'เจ็บ',
    'ปวด',
    'ไข้',
    'นัด',
    'หมอ',
    'ยา',
    'ไอ',
    'หายใจ',
    'แพ้',
    'ผื่น',
    'คัน',
]

NEGATION_PREFIXES = ['ไม่', 'ไม่มี', 'ไม่เคย', 'หาย', 'ไร้', 'มิได้', 'มิ']


def detect_clinical_intent(text: str) -> Tuple[bool, bool, List[str]]:
    """
    ตรวจจับเจตนาทางคลินิกและระดับความเร่งด่วน พร้อมตัด False Positive ด้วย Negation Prefix
    Returns:
        (is_clinical: bool, is_urgent: bool, matched_keywords: List[str])
    """
    if not text:
        return False, False, []

    cleaned_text = text.lower().strip()
    matched_urgent: List[str] = []
    matched_clinical: List[str] = []

    # 1. ตรวจสอบ URGENT_KEYWORDS ก่อน (กฎข้อ 2: URGENT ชนะเสมอ)
    for kw in URGENT_KEYWORDS:
        if kw in cleaned_text:
            if not _is_negated(cleaned_text, kw):
                matched_urgent.append(kw)

    # 2. ตรวจสอบ CLINICAL_KEYWORDS
    for kw in CLINICAL_KEYWORDS:
        if kw in cleaned_text:
            if not _is_negated(cleaned_text, kw):
                matched_clinical.append(kw)

    all_matched = list(dict.fromkeys(matched_urgent + matched_clinical))
    is_urgent = len(matched_urgent) > 0
    is_clinical = len(all_matched) > 0

    return is_clinical, is_urgent, all_matched


def _is_negated(text: str, keyword: str) -> bool:
    """
    ตรวจสอบว่าคำสำคัญถูกนำหน้าด้วยคำปฏิเสธ (Negation) ในระยะใกล้หรือไม่
    เช่น "ไม่แน่นหน้าอก", "ไม่มีไข้", "หายปวดแล้ว"
    """
    start_pos = 0
    while True:
        idx = text.find(keyword, start_pos)
        if idx == -1:
            break

        # ตรวจสอบบริบทข้างหน้า 1 - 6 ตัวอักษร
        prefix_window = text[max(0, idx - 6):idx].strip()
        for neg in NEGATION_PREFIXES:
            if prefix_window.endswith(neg):
                return True

        start_pos = idx + len(keyword)

    return False


@csrf_exempt
@require_POST
def line_internal_ingest_view(request: HttpRequest) -> JsonResponse:
    """
    Internal API Endpoint สำหรับรับ Webhook Event จาก FastAPI Microservice
    Header:
        X-Internal-Token: <SECRET_TOKEN>
    """
    # 1. Constant-Time Token Authentication (Pillars 8, 14)
    received_token = request.headers.get('X-Internal-Token', '').strip()
    expected_token = getattr(settings, 'INTERNAL_API_TOKEN', '').strip()

    if not expected_token or not secrets.compare_digest(received_token, expected_token):
        logger.warning(f"[LINE Internal API] Unauthorized access attempt from IP: {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({'status': 'error', 'message': 'Unauthorized internal call'}, status=401)

    # 2. แกะ Payload JSON
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Malformed JSON: {str(e)}'}, status=400)

    event = body.get('event') or body
    if not isinstance(event, dict):
        return JsonResponse({'status': 'error', 'message': 'Event payload must be a JSON object'}, status=400)

    event_type = event.get('type', 'message')
    source = event.get('source', {})
    line_user_id = source.get('userId', '').strip()
    if not line_user_id:
        return JsonResponse({'status': 'error', 'message': 'Missing source.userId in event'}, status=400)

    # 3. กำหนด Deduplication Key (กฎข้อ 2 & ข้อผิดพลาดที่คนมักพลาด #1)
    # - หากเป็น message ให้ใช้ message.id
    # - หากเป็น event อื่น ให้ใช้ webhookEventId หรือ composite hash
    message_obj = event.get('message', {})
    msg_id = message_obj.get('id')
    if not msg_id:
        webhook_event_id = event.get('webhookEventId')
        if webhook_event_id:
            msg_id = f"event_{webhook_event_id}"
        else:
            ts = event.get('timestamp', int(timezone.now().timestamp()))
            msg_id = f"event_{event_type}_{line_user_id}_{ts}"

    # กฎข้อ 3: Dedupe ด้วย line_message_id ก่อนบันทึกเสมอ (Idempotent 200 OK)
    if CommunicationRecord.objects.filter(line_message_id=msg_id).exists():
        logger.info(f"[LINE Internal API] Deduplicated message: {msg_id}")
        return JsonResponse({
            'status': 'ok',
            'action': 'deduplicated',
            'line_message_id': msg_id,
            'message': 'Event already processed'
        }, status=200)

    # 4. Resolve LineUser & Active Patient Context
    line_user, _ = LineUser.objects.get_or_create(
        line_user_id=line_user_id,
        defaults={'display_name': 'LINE User'}
    )
    patient = line_user.active_patient

    # 5. วิเคราะห์ประเภทข้อความและเนื้อหา
    msg_type = message_obj.get('type', 'text')
    text_content = message_obj.get('text', '').strip() if msg_type == 'text' else ''

    # กรณีเป็น image หรือ file
    if msg_type in ['image', 'file', 'video', 'audio']:
        text_content = f"[{msg_type.upper()}] ผู้ใช้ส่งไฟล์สื่อ"

    is_clinical, is_urgent, matched_kws = detect_clinical_intent(text_content)

    # 6. บันทึก CommunicationRecord ลง Unified Inbox
    record = CommunicationRecord.objects.create(
        line_message_id=msg_id,
        line_user=line_user,
        patient=patient,
        direction=CommunicationRecord.DirectionChoices.INCOMING,
        message_type=CommunicationRecord.MessageTypeChoices.TEXT if msg_type == 'text' else CommunicationRecord.MessageTypeChoices.IMAGE,
        content=text_content,
        is_clinical_candidate=is_clinical,
        raw_payload=event
    )

    review_item_id = None
    binding_required = False

    # 7. สร้าง Human-in-the-Loop ClinicalReviewItem หากเป็นข้อมูลอาการทางการแพทย์
    if is_clinical:
        if patient:
            review_type = (
                ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC
                if is_urgent
                else ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE
            )

            # ตรวจสอบ 5-minute time window grouping (คำถามที่ 5)
            five_mins_ago = timezone.now() - timedelta(minutes=5)
            recent_item = ClinicalReviewItem.objects.filter(
                patient=patient,
                status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
                created_at__gte=five_mins_ago
            ).order_by('-created_at').first()

            if recent_item:
                # Group รวมเข้ากับเคสก่อนหน้าเพื่อไม่ให้พยาบาล/แพทย์เจอน้ำท่วมคิว
                recent_item.review_notes += f"\n[+ข้อความต่อเนื่อง]: {text_content} (คำสำคัญ: {', '.join(matched_kws)})"
                # หากข้อความใหม่เป็น URGENT ให้ยกระดับเป็น LEVEL_2_DIAGNOSTIC ทันที
                if is_urgent and recent_item.review_type != ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC:
                    recent_item.review_type = ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC
                recent_item.save(update_fields=['review_notes', 'review_type', 'updated_at'])
                review_item_id = recent_item.pk
            else:
                review_item = ClinicalReviewItem.objects.create(
                    patient=patient,
                    source_message=record,
                    review_type=review_type,
                    status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
                    review_notes=f"ตรวจพบคีย์เวิร์ด: {', '.join(matched_kws)}\nข้อความ: {text_content}"
                )
                review_item_id = review_item.pk
        else:
            # ผู้ใช้ยังไม่ได้ผูกบัญชีคนไข้ แต่พิมพ์อาการมา
            binding_required = True

    return JsonResponse({
        'status': 'ok',
        'action': 'processed',
        'record_id': record.pk,
        'line_message_id': msg_id,
        'is_clinical_candidate': is_clinical,
        'is_urgent': is_urgent,
        'matched_keywords': matched_kws,
        'review_item_id': review_item_id,
        'binding_required': binding_required
    }, status=200)
