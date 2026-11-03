"""
LINE Webhook & Account Binding Controllers for TSPI Clinic.
Enforces Strict HMAC-SHA256 Signature Verification, Fail-Closed Security,
and Complete Audit Trails (Pillars 8, 14).
"""

import json
import logging
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse

from accounts.models import AuditLog
from patients.models import Patient, PatientLinkingToken, Appointment
from clinical.models import AnalysisRecord, Box
from patients import line_ai, line_alerts, line_dispatch
from patients.line_relay import relay_to_old_system
from patients.line_service import (
    BOT_OFF_WORDS, BOT_ON_WORD, LineSecurity, LineFlexMessageBuilder, LineMessagingService, is_bot_on_word,
    make_line_register_token,
)
from patients.views_line_internal import ingest_line_event, detect_clinical_intent
from patients.models_line import CommunicationRecord, LineUser
from clinical import media_store, services_intake

START_WORDS = ('เริ่ม', 'เริ่มต้น', 'start', 'ปรึกษา')
DONE_WORDS = ('เสร็จแล้ว', 'จบ', 'done', 'ครบแล้ว')
MEDIA_KINDS = {'image': 'image', 'audio': 'audio', 'video': 'video', 'file': 'file'}
EMERGENCY_TEXT = (
    "หากมีอาการแน่นหน้าอก หายใจลำบาก หมดสติ หรือแขนขาอ่อนแรง กรุณาโทร 1669 หรือไปโรงพยาบาลที่ใกล้ที่สุดทันที\n"
    "ทีมแพทย์ได้รับแจ้งแล้วเช่นกัน"
)


def _card(title: str, body: str, buttons=None, **kwargs) -> dict:
    return LineFlexMessageBuilder.build_bot_card(title, body, buttons=buttons, **kwargs)


def _intake_card(title: str, body: str) -> dict:
    """การ์ดระหว่างเล่าอาการ พร้อมปุ่ม "เสร็จแล้ว" ให้ผู้ป่วยกดปิดรอบซักประวัติ"""
    return _card(title, body, buttons=[LineFlexMessageBuilder.button_message('เสร็จแล้ว', 'เสร็จแล้ว')])


def _emergency_card() -> dict:
    return _card('อาจเป็นภาวะฉุกเฉิน', EMERGENCY_TEXT, danger=True, buttons=[
        LineFlexMessageBuilder.button_uri('โทร 1669', 'tel:1669', style='secondary'),
        LineFlexMessageBuilder.button_message('เสร็จแล้ว', 'เสร็จแล้ว', style='secondary'),
    ])


def _reply(reply_token: str, card: dict) -> None:
    if reply_token:
        LineMessagingService.reply_message(reply_token, [card])


def _resolve_patient(line_user_id: str):
    """ผู้ป่วยที่บัญชี LINE นี้กำลังดูแลอยู่ (Caregiver Hub) หรือที่ผูกแบบเดิม 1:1"""
    line_user = LineUser.objects.filter(line_user_id=line_user_id).select_related('active_patient').first()
    if line_user and line_user.active_patient:
        return line_user.active_patient
    return Patient.objects.filter(line_user_id=line_user_id).first()


def _binding_card(request: HttpRequest, line_user_id: str) -> dict:
    binding_url = request.build_absolute_uri(
        f"{reverse('root_line_register')}?t={make_line_register_token(line_user_id)}")
    return _card('เชื่อมบัญชีคลินิกก่อนนะครับ', 'เชื่อมบัญชี LINE กับเวชระเบียนของคลินิก เพื่อเล่าอาการ ดูใบนัด และดูผลตรวจผ่านบอทได้',
                 buttons=[LineFlexMessageBuilder.button_uri('เชื่อมบัญชีคลินิก', binding_url)])


def _menu_buttons() -> list:
    return [
        LineFlexMessageBuilder.button_message('เล่าอาการให้คลินิก', 'เริ่ม'),
        LineFlexMessageBuilder.button_postback('ดูใบนัด', 'action=check_appointment'),
        LineFlexMessageBuilder.button_postback('ดูผลตรวจ', 'action=check_report'),
    ]


def _sent_to_doctor_card(title: str) -> dict:
    return _card(title, 'ทีมแพทย์จะตรวจและติดต่อกลับครับ\n\nระหว่างนี้พิมพ์ถาม AI ได้เลย หรือเลือกเมนูด้านล่าง', buttons=_menu_buttons())


def _bot_menu_card(request: HttpRequest, patient, line_user_id: str) -> dict:
    if not patient:
        return _binding_card(request, line_user_id)
    return _card('เปิดใช้งานบอทแล้ว', f'สวัสดีครับคุณ{patient.first_name}\nพิมพ์คำถามเรื่องโรคหรือการรักษา ถาม AI ได้เลย หรือเลือกเมนูด้านล่าง',
                 buttons=_menu_buttons())


def welcome_card(patient) -> dict:
    return _card(f'สวัสดีครับคุณ{patient.first_name}', 'ลงทะเบียนเรียบร้อยแล้ว ใช้งานบอทได้เลยครับ\nพิมพ์คำถามเรื่องโรคหรือการรักษา ถาม AI ได้เลย หรือเลือกเมนูด้านล่าง',
                 buttons=_menu_buttons())


def _set_bot_enabled(request: HttpRequest, line_user: LineUser, enabled: bool, patient) -> None:
    line_user.bot_enabled = enabled
    line_user.save(update_fields=['bot_enabled', 'last_seen_at'])
    AuditLog.objects.create(
        action='LINE_BOT_ENABLED' if enabled else 'LINE_BOT_DISABLED',
        user=None,
        model='Patient',
        object_id=str(patient.pk) if patient else '',
        client_ip=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        changes={'line_user_id': line_user.line_user_id},
    )


def _turn_bot_off(request: HttpRequest, line_user: LineUser, patient, reply_token: str) -> None:
    """ปิดบอท: ถ้ากำลังเล่าอาการค้างอยู่ ส่งรอบนั้นให้ทีมแพทย์เลย ไม่ให้ข้อมูลค้างในร่าง"""
    if patient:
        open_box = Box.objects.filter(patient=patient, source=Box.Source.LINE, status=Box.Status.DRAFT).first()
        if open_box and (open_box.contents or {}).get('messages'):
            services_intake.close_session(open_box, reason='bot_disabled')
    _set_bot_enabled(request, line_user, False, patient)
    _reply(reply_token, _card('ปิดบอทแล้ว', f'บอทจะไม่ตอบอัตโนมัติอีก พิมพ์ข้อความทิ้งไว้ได้ เจ้าหน้าที่จะตอบกลับทางแชทนี้\n\nอยากใช้บอทอีกครั้ง พิมพ์ว่า "{BOT_ON_WORD}"',
                               closable=False))


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

    elif event_type == 'message':
        message_obj = event.get('message', {})
        msg_type = message_obj.get('type')
        raw_text = (message_obj.get('text') or '').strip() if msg_type == 'text' else ''

        if is_bot_on_word(raw_text):
            _set_bot_enabled(request, line_user, True, patient)
            _reply(reply_token, _bot_menu_card(request, patient, line_user_id))
            return
        if not line_user.bot_enabled:
            # บอทปิดอยู่: ไม่ตอบ และไม่เปิดรอบซักประวัติ แต่เก็บไฟล์ไว้ให้เจ้าหน้าที่ เพราะ LINE ลบทิ้งภายหลัง
            if msg_type in MEDIA_KINDS:
                _store_inbox_media(line_user, message_obj)
            return
        if raw_text in BOT_OFF_WORDS:
            _turn_bot_off(request, line_user, patient, reply_token)
        elif msg_type == 'text':
            _handle_line_text_command(request, patient, line_user_id, raw_text, reply_token,
                                      message_id=message_obj.get('id', ''))
        elif msg_type in MEDIA_KINDS:
            _handle_line_media(request, patient, line_user_id, message_obj, reply_token)

    elif event_type == 'postback':
        if not line_user.bot_enabled:
            return  # ปุ่มจากการ์ดเก่าหรือ Rich Menu ไม่ปลุกบอท ต้องพิมพ์เปิดเองเท่านั้น
        postback_data = event.get('postback', {}).get('data', '')
        if postback_data == LineFlexMessageBuilder.BOT_OFF_POSTBACK:
            _turn_bot_off(request, line_user, patient, reply_token)
        elif postback_data.startswith(line_ai.SEND_TO_DOCTOR_POSTBACK):
            _send_message_to_doctor(request, patient, line_user, postback_data, reply_token)
        elif 'action=check_appointment' in postback_data:
            _send_appointment_reply(request, patient, line_user_id, reply_token)
        elif 'action=check_report' in postback_data:
            _send_latest_report_reply(request, patient, line_user_id, reply_token)


def _send_message_to_doctor(request: HttpRequest, patient: Patient, line_user: LineUser, postback_data: str, reply_token: str):
    """ปุ่มใต้คำตอบ AI: ส่งข้อความที่เคยถาม AI เข้ากล่องให้ทีมแพทย์ โดยไม่ต้องพิมพ์ใหม่"""
    if not patient:
        _reply(reply_token, _binding_card(request, line_user.line_user_id))
        return

    message_id = postback_data[len(line_ai.SEND_TO_DOCTOR_POSTBACK):]
    # หาจากข้อความของ LINE คนนี้เท่านั้น กันการปลอม postback มาดึงข้อความของคนอื่น
    record = CommunicationRecord.objects.filter(
        line_message_id=message_id, line_user=line_user,
        direction=CommunicationRecord.DirectionChoices.INCOMING,
    ).first()
    if not record:
        _reply(reply_token, _intake_card('ไม่พบข้อความนี้', 'รบกวนกด "เล่าอาการให้คลินิก" แล้วพิมพ์อาการอีกครั้งครับ'))
        return
    if Box.objects.filter(patient=patient, source=Box.Source.LINE,
                          contents__messages__contains=[{'external_id': message_id}]).exists():
        _reply(reply_token, _sent_to_doctor_card('ส่งให้ทีมแพทย์แล้ว'))
        return

    box = services_intake.open_session(patient, Box.Source.LINE)
    still_telling = bool((box.contents or {}).get('messages'))
    services_intake.append_message(box, 'text', text=record.content, external_id=message_id)
    if still_telling:
        _reply(reply_token, _intake_card('เพิ่มเข้ารอบเล่าอาการแล้ว', 'เล่าเพิ่มได้เลยครับ เมื่อครบแล้วกด "เสร็จแล้ว"'))
    else:
        services_intake.close_session(box, reason='sent_from_ai_chat')
        _reply(reply_token, _sent_to_doctor_card('ส่งให้ทีมแพทย์แล้ว'))


def _handle_line_text_command(request: HttpRequest, patient: Patient, line_user_id: str, raw_text: str, reply_token: str,
                              message_id: str = ''):
    """
    จัดการข้อความจากผู้ป่วยบน LINE OA
    คำสั่ง (นัดหมาย/ผลตรวจ/ติดต่อ) ตอบทันที ระหว่างเล่าอาการข้อความเข้ารอบซักประวัติ (Box เดียวต่อรอบ) นอกนั้น AI ตอบ
    """
    text = raw_text.lower()

    if any(k in text for k in ['นัดหมาย', 'ใบนัด', 'ตารางนัด', 'appointment']):
        _send_appointment_reply(request, patient, line_user_id, reply_token)
        return
    if any(k in text for k in ['ผลตรวจ', 'รายงาน', 'ผลแล็บ', 'report']):
        _send_latest_report_reply(request, patient, line_user_id, reply_token)
        return
    if any(k in text for k in ['ติดต่อ', 'เบอร์โทร']):
        _reply(reply_token, _card('ติดต่อเจ้าหน้าที่', 'กดปิดบอท แล้วพิมพ์ข้อความทิ้งไว้ได้เลย เจ้าหน้าที่จะตอบกลับทางแชทนี้ในเวลาทำการ'))
        return

    if not patient:
        _reply(reply_token, _binding_card(request, line_user_id))
        return

    if text in DONE_WORDS:
        open_box = Box.objects.filter(patient=patient, source=Box.Source.LINE, status=Box.Status.DRAFT).first()
        if open_box and (open_box.contents or {}).get('messages'):
            services_intake.close_session(open_box)
            _reply(reply_token, _sent_to_doctor_card('ได้รับข้อมูลครบแล้ว'))
        else:
            _reply(reply_token, _intake_card('ยังไม่มีข้อมูลอาการ', 'พิมพ์เล่าอาการ หรือส่งรูป/ข้อความเสียงได้เลยครับ'))
        return

    if text in START_WORDS:
        services_intake.open_session(patient, Box.Source.LINE)
        _reply(reply_token, _intake_card('เล่าอาการได้เลยครับ',
                                         f'สวัสดีครับคุณ{patient.first_name} ส่งข้อความ รูป หรือข้อความเสียงได้\nเมื่อเล่าครบแล้วกดปุ่ม "เสร็จแล้ว"'))
        return

    is_clinical, is_urgent, _ = detect_clinical_intent(raw_text)
    in_session = Box.objects.filter(patient=patient, source=Box.Source.LINE, status=Box.Status.DRAFT).exists()
    if not in_session and not is_urgent:
        # ไม่ได้กำลังเล่าอาการ: เป็นคำถามทั่วไป ให้ AI ตอบ อาการฉุกเฉินยังเข้ากล่องเพื่อให้ทีมแพทย์เห็น
        line_ai.answer_question(line_user_id, patient, raw_text, reply_token,
                                symptom_message_id=message_id if is_clinical else '')
        return

    box = services_intake.open_session(patient, Box.Source.LINE)
    is_first = not (box.contents or {}).get('messages')
    already_flagged = (box.contents or {}).get('red_flag')
    services_intake.append_message(box, 'text', text=raw_text, external_id=message_id, red_flag=is_urgent)
    if is_urgent and not already_flagged:
        line_alerts.notify_emergency(request, box)
    if not reply_token:
        return
    if is_urgent:
        _reply(reply_token, _emergency_card())
        return
    question = services_intake.ai_followup_question(box)
    if question:
        _reply(reply_token, _intake_card('ขอถามเพิ่มอีกนิดครับ', question))
    elif is_first:
        _reply(reply_token, _intake_card('รับทราบครับ', 'เล่าเพิ่มเติมได้เรื่อย ๆ ส่งรูปหรือข้อความเสียงได้ เมื่อครบแล้วกด "เสร็จแล้ว"'))


def _store_inbox_media(line_user: LineUser, message_obj: dict) -> None:
    """เข้ารหัสเก็บไฟล์ไว้กับข้อความใน Inbox สำหรับไฟล์ที่ไม่ได้เข้ารอบซักประวัติ"""
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
    """ดึงรูป/เสียง/วิดีโอจาก LINE ทันที (LINE เก็บไว้ไม่นาน) เข้ารหัสเก็บ แล้วต่อเข้ารอบซักประวัติ"""
    if not patient:
        _store_inbox_media(LineUser.objects.get(line_user_id=line_user_id), message_obj)
        _reply(reply_token, _binding_card(request, line_user_id))
        return

    kind = MEDIA_KINDS[message_obj.get('type')]
    message_id = message_obj.get('id', '')
    box = services_intake.open_session(patient, Box.Source.LINE)
    is_first = not (box.contents or {}).get('messages')

    media = None
    content = LineMessagingService.get_message_content(message_id) if message_id else None
    if content:
        data, content_type = content
        media = media_store.save_encrypted(data, content_type, kind=f"line/{kind}")
    services_intake.append_message(box, kind, media=media, external_id=message_id)

    if is_first or media is None:
        if media:
            _reply(reply_token, _intake_card('ได้รับไฟล์แล้วครับ', 'ส่งเพิ่มหรือเล่าอาการต่อได้เลย เมื่อครบแล้วกด "เสร็จแล้ว"'))
        else:
            _reply(reply_token, _intake_card('ดึงไฟล์ไม่สำเร็จ', 'ขออภัยครับ รบกวนส่งไฟล์นี้ใหม่อีกครั้ง'))


def _send_appointment_reply(request: HttpRequest, patient: Patient, line_user_id: str, reply_token: str):
    """ตอบกลับด้วยใบนัดหมายแพทย์ล่าสุด"""
    if not patient:
        _reply(reply_token, _binding_card(request, line_user_id))
        return

    appt = patient.appointments.filter(status__in=['scheduled', 'confirmed']).order_by('appointment_date', 'appointment_time').first()
    if appt:
        doc_name = appt.doctor.get_full_name() if appt.doctor else "แพทย์ผู้เชี่ยวชาญ TSPI"
        card = LineFlexMessageBuilder.build_appointment_card(
            patient_name=patient.full_name,
            appt_date=str(appt.appointment_date),
            appt_time=str(appt.appointment_time),
            doctor_name=doc_name
        )
        _reply(reply_token, LineFlexMessageBuilder.with_close_button(card))
    else:
        _reply(reply_token, _card('ยังไม่มีนัดหมาย', f'เรียนคุณ {patient.full_name}\nขณะนี้ท่านยังไม่มีนัดหมายแพทย์ที่เปิดอยู่\n\nพิมพ์ถาม AI ได้เลย หรือเลือกเมนูด้านล่าง', buttons=_menu_buttons()))


def _send_latest_report_reply(request: HttpRequest, patient: Patient, line_user_id: str, reply_token: str):
    """ตอบกลับด้วยรายงานการแพทย์แม่นยำที่ได้รับการอนุมัติล่าสุด (Approved Report Only)"""
    if not patient:
        _reply(reply_token, _binding_card(request, line_user_id))
        return

    # ดึงเฉพาะรายงานที่ได้รับการอนุมัติแล้วเท่านั้น (Pillar 15)
    report = AnalysisRecord.objects.filter(
        patient=patient,
        status__in=['approved', 'released']
    ).order_by('-analysis_date').first()

    if report:
        portal_url = request.build_absolute_uri(reverse('portal_patient:portal_report_detail', kwargs={'pk': report.pk}))
        card = LineFlexMessageBuilder.build_report_released_card(
            patient_name=patient.full_name,
            report_title=f"รายงานการแพทย์แม่นยำ 39 แกน #{report.pk}",
            portal_url=portal_url
        )
        _reply(reply_token, LineFlexMessageBuilder.with_close_button(card))
    else:
        _reply(reply_token, _card('ยังไม่มีผลตรวจที่พร้อมดู', f'เรียนคุณ {patient.full_name}\nขณะนี้ยังไม่มีรายงานที่แพทย์ลงนามอนุมัติ กรุณาสอบถามแพทย์ผู้ดูแลหากต้องการข้อมูลเพิ่มเติม\n\nพิมพ์ถาม AI ได้เลย หรือเลือกเมนูด้านล่าง', buttons=_menu_buttons()))


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
