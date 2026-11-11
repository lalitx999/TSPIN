"""
LINE Webhook & Account Binding Controllers for TSPI Clinic.
Enforces Strict HMAC-SHA256 Signature Verification, Fail-Closed Security,
and Complete Audit Trails (Pillars 8, 14).

แชทแบบธรรมดา: พิมพ์ "เปิดบอท" แล้วคุยกับ AI ได้เลย (ต้องลงทะเบียนก่อน) ทุกข้อความต่อเข้ารอบแชท (Box) ให้หมออ่านใน EMR
เงียบเกิน LINE_BOT_IDLE_MINUTES บอทปิดเองโดยไม่แจ้ง ข้อความถัดไปไปถึงทีมขายตามปกติ
"""

import json
import logging
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from patients.models import Patient, PatientLinkingToken, Appointment
from clinical.models import AnalysisRecord, Box
from patients import line_ai, line_alerts, line_dispatch
from patients.line_relay import relay_to_old_system
from patients.line_service import (
    BOT_OFF_WORD, BOT_ON_WORD, LineSecurity, LineFlexMessageBuilder, LineMessagingService, is_bot_off_word,
    is_bot_on_word, make_line_register_token, text_message,
)
from patients.views_line_internal import ingest_line_event, detect_clinical_intent
from patients.models_line import CommunicationRecord, LineUser
from clinical import media_store, services_intake

MEDIA_KINDS = {'image': 'image', 'audio': 'audio', 'video': 'video', 'file': 'file'}
APPOINTMENT_WORDS = ('นัดหมาย', 'ใบนัด', 'ตารางนัด', 'appointment')
REPORT_WORDS = ('ผลตรวจ', 'ผลแล็บ', 'รายงานผล', 'report')
MEDIA_REPLIES = {
    'image': 'ได้รับรูปแล้วครับ เก็บไว้ให้ทีมแพทย์ดูแล้ว ผู้ช่วยยังดูรูปไม่ได้ ช่วยพิมพ์เล่าสั้น ๆ ว่าเป็นรูปอะไรได้ไหมครับ',
    'audio': 'ได้รับข้อความเสียงแล้วครับ เก็บไว้ให้ทีมแพทย์ฟังแล้ว ผู้ช่วยยังฟังเสียงไม่ได้ รบกวนพิมพ์เล่าสั้น ๆ ได้ไหมครับ',
    'video': 'ได้รับวิดีโอแล้วครับ เก็บไว้ให้ทีมแพทย์ดูแล้ว ช่วยพิมพ์เล่าสั้น ๆ ว่าเป็นอะไรได้ไหมครับ',
    'file': 'ได้รับไฟล์แล้วครับ เก็บไว้ให้ทีมแพทย์ดูแล้ว ช่วยพิมพ์เล่าสั้น ๆ ว่าเป็นไฟล์อะไรได้ไหมครับ',
}


def _reply(reply_token: str, message: dict) -> None:
    if reply_token:
        LineMessagingService.reply_message(reply_token, [message])


def _resolve_patient(line_user_id: str):
    """ผู้ป่วยที่บัญชี LINE นี้กำลังดูแลอยู่ (Caregiver Hub) หรือที่ผูกแบบเดิม 1:1"""
    line_user = LineUser.objects.filter(line_user_id=line_user_id).select_related('active_patient').first()
    if line_user and line_user.active_patient:
        return line_user.active_patient
    return Patient.objects.filter(line_user_id=line_user_id).first()


def _binding_card(request: HttpRequest, line_user_id: str) -> dict:
    binding_url = request.build_absolute_uri(
        f"{reverse('root_line_register')}?t={make_line_register_token(line_user_id)}")
    return LineFlexMessageBuilder.build_bot_card(
        'ลงทะเบียนก่อนนะครับ', 'กรอกชื่อและเบอร์โทรครั้งเดียว แล้วคุยกับผู้ช่วย AI ของคลินิกได้เลย',
        buttons=[LineFlexMessageBuilder.button_uri('ลงทะเบียน', binding_url)])


def welcome_text(patient) -> str:
    minutes = settings.LINE_BOT_IDLE_MINUTES
    idle = f'{minutes // 60} ชั่วโมง' if minutes % 60 == 0 else f'{minutes} นาที'
    return (f'สวัสดีครับคุณ{patient.first_name} ผมเป็นผู้ช่วย AI ของคลินิก เล่าอาการหรือถามเรื่องสุขภาพได้เลยครับ '
            f'ทีมแพทย์ของคลินิกอ่านบทสนทนานี้ได้\n\n'
            f'ถ้าเงียบไป {idle} ผมจะหยุดตอบเอง อยากคุยใหม่พิมพ์ "{BOT_ON_WORD}" '
            f'อยากคุยกับเจ้าหน้าที่พิมพ์ "{BOT_OFF_WORD}"')


def welcome_message(patient) -> dict:
    minutes = settings.LINE_BOT_IDLE_MINUTES
    idle = f'{minutes // 60} ชั่วโมง' if minutes % 60 == 0 else f'{minutes} นาที'
    return LineFlexMessageBuilder.build_bot_welcome_card(patient.first_name, idle, BOT_OFF_WORD)


def _set_bot_enabled(request: HttpRequest, line_user: LineUser, enabled: bool, patient, reason: str = '') -> None:
    line_user.bot_enabled = enabled
    fields = ['bot_enabled', 'last_seen_at']
    if enabled:
        line_user.bot_last_active_at = timezone.now()
        fields.append('bot_last_active_at')
    line_user.save(update_fields=fields)
    AuditLog.objects.create(
        action='LINE_BOT_ENABLED' if enabled else 'LINE_BOT_DISABLED',
        user=None,
        model='Patient',
        object_id=str(patient.pk) if patient else '',
        client_ip=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        changes={'line_user_id': line_user.line_user_id, **({'reason': reason} if reason else {})},
    )


def _touch_bot(line_user: LineUser) -> None:
    line_user.bot_last_active_at = timezone.now()
    line_user.save(update_fields=['bot_last_active_at', 'last_seen_at'])


def _turn_bot_on(request: HttpRequest, line_user: LineUser, patient, reply_token: str) -> None:
    _set_bot_enabled(request, line_user, True, patient)
    _reply(reply_token, welcome_message(patient) if patient else _binding_card(request, line_user.line_user_id))


def _turn_bot_off(request: HttpRequest, line_user: LineUser, patient, reply_token: str) -> None:
    """ปิดบอท: จบรอบแชทให้หมอเห็นเลย ไม่ให้ข้อมูลค้างในร่าง"""
    services_intake.end_line_session(patient, reason='bot_disabled')
    _set_bot_enabled(request, line_user, False, patient, reason='user')
    _reply(reply_token, text_message(f'ปิดบอทแล้วครับ พิมพ์ข้อความทิ้งไว้ได้ เจ้าหน้าที่จะตอบกลับทางแชทนี้\n'
                                     f'อยากคุยกับผู้ช่วย AI อีกครั้ง พิมพ์ "{BOT_ON_WORD}"'))


def _turn_bot_complete(request: HttpRequest, line_user: LineUser, patient, reply_token: str) -> None:
    """ผู้ป่วยกดยืนยันส่งสรุปให้ทีมแพทย์ -> ปิดรอบเข้าคิวตรวจและปิดบอทอย่างนุ่มนวล"""
    services_intake.end_line_session(patient, reason='patient_completed')
    _set_bot_enabled(request, line_user, False, patient, reason='completed')
    _reply(reply_token, text_message(
        'ส่งสรุปอาการให้ทีมแพทย์เรียบร้อยแล้วครับ ทีมแพทย์สามารถเปิดดูข้อมูลจากเวชระเบียนได้ทันที\n\n'
        f'หากต้องการสอบถามเพิ่มเติมหรือเล่าอาการใหม่ พิมพ์ "{BOT_ON_WORD}" ได้ทุกเมื่อครับ'
    ))


def _expire_idle_bot(request: HttpRequest, line_user: LineUser, patient) -> None:
    """เงียบเกินเวลา: ปิดบอทแบบเงียบ ๆ ตอนมีข้อความใหม่เข้ามา (ระบบเก่าได้ข้อความนี้ไปแล้วตามกฎเดียวกัน)"""
    services_intake.end_line_session(patient, reason='idle')
    _set_bot_enabled(request, line_user, False, patient, reason='idle')


logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def line_webhook_view(request: HttpRequest) -> HttpResponse:
    """
    รับและตรวจสอบ Event Webhook จาก LINE Official Account (Pillars 8, 14)
    กฎความปลอดภัย:
    1. หากไม่ตั้งค่า LINE_CHANNEL_SECRET ฝั่ง Server -> 503 Service Unavailable
    2. หากไม่มี X-Line-Signature หรือลายเซ็นไม่ตรง -> 401 Unauthorized (Fail-Closed)
    3. หาก Payload JSON เสียรูป -> 400 Bad Request
    4. ตรวจสอบ Empty Events Probe สำเร็จ -> 200 OK
    """
    secret = getattr(settings, 'LINE_CHANNEL_SECRET', '')
    if not secret:
        logger.warning("[LINE Webhook] Rejected: LINE_CHANNEL_SECRET is not configured on server.")
        return HttpResponse("LINE_CHANNEL_SECRET not configured", status=503)

    # 1. ตรวจสอบ Header X-Line-Signature
    signature = request.headers.get('X-Line-Signature', '')
    if not signature:
        logger.warning("[LINE Webhook] Rejected: Missing X-Line-Signature header.")
        return HttpResponse("Missing signature", status=401)

    # ป้องกัน non-ASCII injection ใน signature header
    try:
        signature.encode('ascii')
    except UnicodeEncodeError:
        logger.warning("[LINE Webhook] Rejected: Non-ASCII characters in X-Line-Signature.")
        return HttpResponse("Invalid signature encoding", status=401)

    # 2. ตรวจสอบความถูกต้องของ HMAC-SHA256 เทียบกับ Raw Body ไบนารีแท้จริง
    raw_body = request.body
    if not LineSecurity.verify_signature(raw_body, signature, secret=secret):
        logger.warning("[LINE Webhook] Rejected: Cryptographic signature mismatch.")
        return HttpResponse("Invalid cryptographic signature", status=401)

    # 3. ถอดรหัส JSON และตรวจสอบโครงสร้าง Payload
    try:
        data = json.loads(raw_body.decode('utf-8'))
    except Exception as e:
        logger.warning(f"[LINE Webhook] Malformed JSON: {e}")
        return HttpResponse("Malformed JSON payload", status=400)

    if not isinstance(data, dict) or 'events' not in data or not isinstance(data['events'], list):
        logger.warning("[LINE Webhook] Invalid events container shape.")
        return HttpResponse("Invalid events structure", status=400)

    events = data['events']

    # 4. หากเป็น Empty Events Probe จาก LINE Console ตรวจสอบสถานะ ให้ตอบกลับ 200 ทันที
    if len(events) == 0:
        return JsonResponse({"status": "ok", "message": "Probe signature verified successfully"})

    # 5. ส่งต่อให้ระบบเก่าก่อน เพราะต้องดูสถานะบอทก่อนที่ event ชุดนี้จะเปลี่ยนมัน
    try:
        relay_to_old_system(raw_body, signature, data)
    except Exception as e:
        logger.error(f"[LINE Relay] Failed before delivery: {e}", exc_info=True)

    # 6. กระจายจัดการ Events ตามประเภท
    for event in events:
        try:
            # บันทึกข้อความก่อนตอบ LINE เสมอ ส่วนงานช้า (ดาวน์โหลดไฟล์ ตอบกลับ) ทำต่อหลังตอบแล้ว
            if event.get('type') == 'message':
                result, _ = ingest_line_event(event)
                if result.get('action') == 'deduplicated':
                    continue  # LINE ส่งซ้ำ: เคยจัดการแล้ว ห้ามตอบหรือสั่งงานซ้ำ
            line_dispatch.submit((event.get('source') or {}).get('userId') or '', _dispatch_line_event, request, event)
        except Exception as e:
            logger.error(f"[LINE Webhook] Error processing event: {e}", exc_info=True)

    return JsonResponse({"status": "ok", "processed": len(events)})


def _dispatch_line_event(request: HttpRequest, event: dict):
    """ประมวลผลแต่ละ Event จาก LINE อย่างปลอดภัย"""
    event_type = event.get('type')
    source = event.get('source', {})
    line_user_id = source.get('userId')
    reply_token = event.get('replyToken')

    if not line_user_id:
        return

    # ค้นหาผู้ป่วยที่ผูกกับ LINE ID นี้ไว้แล้วในระบบ
    patient = _resolve_patient(line_user_id)

    line_user, _ = LineUser.objects.get_or_create(line_user_id=line_user_id, defaults={'display_name': 'LINE User'})

    if event_type == 'follow':
        # ผู้ใช้กดเพิ่มเพื่อนหรือปลดบล็อก LINE OA (บันทึกอย่างเดียว บอทไม่ทักเอง)
        AuditLog.objects.create(
            action='LINE_USER_FOLLOW',
            user=None,
            model='Patient',
            object_id=str(patient.pk) if patient else '',
            client_ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            changes={'details': f"LINE User {line_user_id} followed TSPI Clinic OA"}
        )
        return

    if event_type not in ('message', 'postback'):
        return

    message_obj = event.get('message', {}) if event_type == 'message' else {}
    msg_type = message_obj.get('type')
    raw_text = (message_obj.get('text') or '').strip() if msg_type == 'text' else ''

    if is_bot_on_word(raw_text):
        _turn_bot_on(request, line_user, patient, reply_token)
        return
    if line_user.bot_enabled and not line_user.is_bot_on():
        _expire_idle_bot(request, line_user, patient)

    if not line_user.bot_enabled:
        # บอทปิดอยู่: ไม่ตอบ (ปุ่มจากการ์ดเก่าก็ไม่ปลุกบอท) แต่เก็บไฟล์ไว้ให้เจ้าหน้าที่ เพราะ LINE ลบทิ้งภายหลัง
        if msg_type in MEDIA_KINDS:
            _store_inbox_media(line_user, message_obj)
        elif detect_clinical_intent(raw_text)[1]:
            _handle_emergency_while_bot_off(request, line_user, patient, raw_text, message_obj.get('id', ''), reply_token)
        return

    _touch_bot(line_user)
    if event_type == 'postback':
        postback_data = event.get('postback', {}).get('data', '')
        if postback_data == LineFlexMessageBuilder.BOT_OFF_POSTBACK:
            _turn_bot_off(request, line_user, patient, reply_token)
        elif postback_data == LineFlexMessageBuilder.BOT_COMPLETE_POSTBACK:
            _turn_bot_complete(request, line_user, patient, reply_token)
        elif 'action=check_appointment' in postback_data:
            _send_appointment_reply(request, patient, line_user_id, reply_token)
        elif 'action=check_report' in postback_data:
            _send_latest_report_reply(request, patient, line_user_id, reply_token)
        return

    if is_bot_off_word(raw_text):
        _turn_bot_off(request, line_user, patient, reply_token)
    elif not patient:
        if msg_type in MEDIA_KINDS:
            _store_inbox_media(line_user, message_obj)
        _reply(reply_token, _binding_card(request, line_user_id))
    elif msg_type == 'text':
        _handle_line_text(request, patient, line_user_id, raw_text, reply_token, message_id=message_obj.get('id', ''))
    elif msg_type in MEDIA_KINDS:
        _handle_line_media(request, patient, line_user_id, message_obj, reply_token)


def _handle_line_text(request: HttpRequest, patient: Patient, line_user_id: str, raw_text: str, reply_token: str,
                      message_id: str = ''):
    """
    ข้อความของผู้ป่วยที่ลงทะเบียนแล้ว: ถามใบนัด/ผลตรวจตอบจากระบบทันที นอกนั้น AI คุยต่อ
    ทุกข้อความ (และคำตอบของ AI) ต่อเข้ารอบแชทเดียวกันให้หมออ่าน
    """
    text = raw_text.lower()
    if any(k in text for k in APPOINTMENT_WORDS):
        _send_appointment_reply(request, patient, line_user_id, reply_token)
        return
    if any(k in text for k in REPORT_WORDS):
        _send_latest_report_reply(request, patient, line_user_id, reply_token)
        return

    is_clinical, is_urgent, _ = detect_clinical_intent(raw_text)
    box = services_intake.open_session(patient, Box.Source.LINE)
    already_flagged = (box.contents or {}).get('red_flag')
    services_intake.append_message(box, 'text', text=raw_text, external_id=message_id, red_flag=is_urgent,
                                   has_symptoms=is_clinical)
    if is_urgent:
        if not already_flagged:
            line_alerts.notify_emergency(request, box)
        _reply(reply_token, line_ai.emergency_card())
        return
    line_ai.answer_question(line_user_id, patient, raw_text, reply_token, box_id=box.id)


def _handle_emergency_while_bot_off(request: HttpRequest, line_user: LineUser, patient, raw_text: str, message_id: str,
                                    reply_token: str) -> None:
    """ข้อยกเว้นข้อเดียวของบอทปิด: อาจเป็นเรื่องชีวิต จึงเตือนโทร 1669 และแจ้งทีมแพทย์"""
    if patient:
        box = services_intake.open_session(patient, Box.Source.LINE)
        already_flagged = (box.contents or {}).get('red_flag')
        services_intake.append_message(box, 'text', text=raw_text, external_id=message_id, red_flag=True)
        if not already_flagged:
            line_alerts.notify_emergency(request, box)
    else:
        record = CommunicationRecord.objects.filter(line_message_id=message_id, line_user=line_user).first()
        if record:
            record.raw_payload = {**(record.raw_payload or {}), 'emergency_alert': True}
            record.save(update_fields=['raw_payload'])
        line_alerts.notify_unbound_emergency(request, line_user)
    _reply(reply_token, line_ai.emergency_card(closable=False))


def _store_inbox_media(line_user: LineUser, message_obj: dict) -> None:
    """เข้ารหัสเก็บไฟล์ไว้กับข้อความใน Inbox สำหรับไฟล์ที่ไม่ได้เข้ารอบแชท"""
    message_id = message_obj.get('id', '')
    record = CommunicationRecord.objects.filter(line_message_id=message_id, line_user=line_user).first()
    if not record:
        return
    content = LineMessagingService.get_message_content(message_id)
    if not content:
        logger.warning("[LINE Webhook] Could not download media for inbox")
        return
    data, content_type = content
    meta = media_store.save_encrypted(data, content_type, kind=f"line_inbox/{MEDIA_KINDS[message_obj['type']]}")
    record.raw_payload = {**(record.raw_payload or {}), 'stored_media': meta}
    record.save(update_fields=['raw_payload'])


def _handle_line_media(request: HttpRequest, patient: Patient, line_user_id: str, message_obj: dict, reply_token: str):
    """ดึงรูป/เสียง/วิดีโอจาก LINE ทันที (LINE เก็บไว้ไม่นาน) เข้ารหัสเก็บเข้ารอบแชท แล้วตอบสั้น ๆ"""
    kind = MEDIA_KINDS[message_obj.get('type')]
    message_id = message_obj.get('id', '')
    box = services_intake.open_session(patient, Box.Source.LINE)
    last_patient_msg = next(
        (m for m in reversed((box.contents or {}).get('messages') or []) if m.get('sender') == 'patient'),
        {},
    )

    content = LineMessagingService.get_message_content(message_id) if message_id else None
    media = media_store.save_encrypted(content[0], content[1], kind=f"line/{kind}") if content else None
    services_intake.append_message(box, kind, media=media, external_id=message_id)

    if media is None:
        _reply(reply_token, text_message('ขออภัยครับ ดึงไฟล์นี้ไม่สำเร็จ รบกวนส่งใหม่อีกครั้ง'))
    elif kind == 'audio' and settings.LINE_VOICE_TRANSCRIBE_ENABLED:
        line_ai.answer_voice(line_user_id, patient, content[0], content[1], reply_token, box.id, message_id)
    elif kind == 'image' and last_patient_msg.get('kind') != kind:
        # ส่งรูปหลายรูปติดกันตอบครั้งเดียว และให้ AI ช่วยสังเกตเบื้องต้น + ซักประวัติเพิ่มเหมือนหน้าเว็บ
        line_ai.answer_image(line_user_id, patient, content[0], content[1], reply_token, box.id)
    elif last_patient_msg.get('kind') != kind:
        # เสียง (กรณีปิดถอดเสียง) / วิดีโอ / ไฟล์: เก็บเข้ารหัสแล้วขอให้พิมพ์เล่าสั้น ๆ
        _reply(reply_token, text_message(MEDIA_REPLIES[kind]))


def _send_appointment_reply(request: HttpRequest, patient: Patient, line_user_id: str, reply_token: str):
    """ตอบกลับด้วยนัดครั้งถัดไป"""
    if not patient:
        _reply(reply_token, _binding_card(request, line_user_id))
        return

    appt = patient.appointments.filter(status__in=['scheduled', 'confirmed']).order_by('appointment_date', 'appointment_time').first()
    if appt:
        doc_name = appt.doctor.get_full_name() if appt.doctor else "แพทย์ของคลินิก"
        _reply(reply_token, text_message(
            f'นัดครั้งถัดไปของคุณ{patient.first_name}\n'
            f'วันที่ {appt.appointment_date:%d/%m/%Y} เวลา {appt.appointment_time:%H:%M} น.\n'
            f'แพทย์: {doc_name}'))
    else:
        _reply(reply_token, text_message(f'ตอนนี้คุณ{patient.first_name}ยังไม่มีนัดหมายที่เปิดอยู่ครับ '
                                         f'อยากนัดพบแพทย์ พิมพ์ "{BOT_OFF_WORD}" แล้วฝากข้อความถึงเจ้าหน้าที่ได้เลย'))


def _send_latest_report_reply(request: HttpRequest, patient: Patient, line_user_id: str, reply_token: str):
    """ตอบกลับด้วยลิงก์รายงานที่แพทย์อนุมัติแล้วเท่านั้น (Pillar 15)"""
    if not patient:
        _reply(reply_token, _binding_card(request, line_user_id))
        return

    report = AnalysisRecord.objects.filter(
        patient=patient,
        status__in=['approved', 'released']
    ).order_by('-analysis_date').first()

    if report:
        portal_url = request.build_absolute_uri(reverse('portal_patient:portal_report_detail', kwargs={'pk': report.pk}))
        _reply(reply_token, text_message(f'รายงานผลตรวจล่าสุดของคุณ{patient.first_name} แพทย์อนุมัติแล้วครับ '
                                         f'เปิดดูได้ที่\n{portal_url}'))
    else:
        _reply(reply_token, text_message(f'ตอนนี้ยังไม่มีผลตรวจที่แพทย์อนุมัติให้ดูครับ '
                                         f'ถ้าสงสัยเรื่องผลตรวจ สอบถามแพทย์ผู้ดูแลได้'))


def line_account_binding_callback_view(request: HttpRequest) -> HttpResponse:
    """
    หน้ายืนยันการเชื่อมต่อบัญชี LINE OA กับเวชระเบียนคลินิก TSPI
    ตรวจสอบ One-Time Nonce Token (Pillars 1, 14)
    """
    token_str = request.GET.get('token', '')
    if not token_str:
        return render(request, 'portal/binding_result.html', {
            'success': False,
            'message': 'ไม่พบโทเค็นสำหรับเชื่อมต่อบัญชี'
        })

    token_obj = PatientLinkingToken.objects.filter(token=token_str, action_type='line_binding').first()
    if not token_obj or not token_obj.is_valid:
        return render(request, 'portal/binding_result.html', {
            'success': False,
            'message': 'โทเค็นเชื่อมต่อไม่ถูกต้องหรือหมดอายุแล้ว กรุณาสร้างคำขอใหม่'
        })

    if request.method == 'POST':
        line_user_id = request.POST.get('line_user_id', '').strip()
        if not line_user_id:
            return render(request, 'portal/binding_result.html', {
                'success': False,
                'message': 'กรุณาระบุ LINE User ID เพื่อยืนยัน'
            })

        patient = token_obj.patient

        # ป้องกัน duplicate LINE identity ผูกกับคนไข้รายอื่น
        existing = Patient.objects.filter(line_user_id=line_user_id).exclude(pk=patient.pk).first()
        if existing:
            return render(request, 'portal/binding_result.html', {
                'success': False,
                'message': f'บัญชี LINE นี้ถูกเชื่อมต่อกับผู้ป่วยรายอื่น ({existing.hn}) เรียบร้อยแล้ว'
            })

        # บันทึกการเชื่อมโยงและตัดการใช้งานโทเค็น
        patient.line_user_id = line_user_id
        patient.save(update_fields=['line_user_id', 'updated_at'])

        token_obj.is_used = True
        token_obj.save(update_fields=['is_used'])

        AuditLog.objects.create(
            action='LINE_ACCOUNT_BOUND',
            user=patient.user,
            model='Patient',
            object_id=str(patient.pk),
            client_ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            changes={'details': f"Patient {patient.hn} ({patient.full_name}) bound to LINE ID {line_user_id}"}
        )

        return render(request, 'portal/binding_result.html', {
            'success': True,
            'patient': patient,
            'message': f'เชื่อมต่อบัญชีคุณ {patient.full_name} (HN: {patient.hn}) กับ LINE OA สำเร็จเรียบร้อย'
        })

    return render(request, 'portal/binding_confirm.html', {
        'patient': token_obj.patient,
        'token': token_str
    })
