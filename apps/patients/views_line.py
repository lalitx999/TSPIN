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
from patients.line_service import LineSecurity, LineFlexMessageBuilder, LineMessagingService
from patients.views_line_internal import ingest_line_event, detect_clinical_intent
from patients.models_line import LineUser
from clinical import media_store, services_intake

START_WORDS = ('เริ่ม', 'เริ่มต้น', 'start', 'ปรึกษา')
DONE_WORDS = ('เสร็จแล้ว', 'จบ', 'done', 'ครบแล้ว')
MEDIA_KINDS = {'image': 'image', 'audio': 'audio', 'video': 'video', 'file': 'file'}
EMERGENCY_TEXT = (
    "⚠️ อาการที่แจ้งมาอาจเป็นภาวะฉุกเฉิน\n"
    "หากมีอาการแน่นหน้าอก หายใจลำบาก หมดสติ หรือแขนขาอ่อนแรง กรุณาโทร 1669 หรือไปโรงพยาบาลที่ใกล้ที่สุดทันที\n"
    "ทีมแพทย์ได้รับแจ้งแล้วเช่นกัน"
)


def _done_quick_reply(text: str) -> dict:
    """ข้อความพร้อมปุ่ม "เสร็จแล้ว" ให้ผู้ป่วยกดปิดรอบซักประวัติ"""
    return {
        "type": "text",
        "text": text,
        "quickReply": {"items": [{"type": "action", "action": {"type": "message", "label": "เสร็จแล้ว", "text": "เสร็จแล้ว"}}]},
    }


def _resolve_patient(line_user_id: str):
    """ผู้ป่วยที่บัญชี LINE นี้กำลังดูแลอยู่ (Caregiver Hub) หรือที่ผูกแบบเดิม 1:1"""
    line_user = LineUser.objects.filter(line_user_id=line_user_id).select_related('active_patient').first()
    if line_user and line_user.active_patient:
        return line_user.active_patient
    return Patient.objects.filter(line_user_id=line_user_id).first()


def _binding_card(request: HttpRequest) -> dict:
    binding_url = request.build_absolute_uri(reverse('root_liff_binding_page'))
    return LineFlexMessageBuilder.build_welcome_card(binding_url=binding_url)

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

    # 5. กระจายจัดการ Events ตามประเภท
    for event in events:
        try:
            _dispatch_line_event(request, event)
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

    if event_type == 'follow':
        # ผู้ใช้กดเพิ่มเพื่อนหรือปลดบล็อก LINE OA
        AuditLog.objects.create(
            action='LINE_USER_FOLLOW',
            user=None,
            model='Patient',
            object_id=str(patient.pk) if patient else '',
            client_ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            changes={'details': f"LINE User {line_user_id} followed TSPI Clinic OA"}
        )
        msg = LineFlexMessageBuilder.build_welcome_card() if patient else _binding_card(request)

        if reply_token:
            LineMessagingService.reply_message(reply_token, [msg])

    elif event_type == 'message':
        # บันทึกทุกข้อความเข้า Unified Inbox / Clinical Review Queue (Caregiver Hub)
        ingest_line_event(event)

        message_obj = event.get('message', {})
        msg_type = message_obj.get('type')
        if msg_type == 'text':
            _handle_line_text_command(request, patient, line_user_id, (message_obj.get('text') or '').strip(), reply_token,
                                      message_id=message_obj.get('id', ''))
        elif msg_type in MEDIA_KINDS:
            _handle_line_media(request, patient, message_obj, reply_token)

    elif event_type == 'postback':
        postback_data = event.get('postback', {}).get('data', '')
        if 'action=check_appointment' in postback_data:
            _send_appointment_reply(patient, reply_token)
        elif 'action=check_report' in postback_data:
            _send_latest_report_reply(request, patient, reply_token)


def _handle_line_text_command(request: HttpRequest, patient: Patient, line_user_id: str, raw_text: str, reply_token: str,
                              message_id: str = ''):
    """
    จัดการข้อความจากผู้ป่วยบน LINE OA
    คำสั่ง (นัดหมาย/ผลตรวจ/ติดต่อ) ตอบทันที ข้อความอื่นของผู้ป่วยที่ผูกบัญชีแล้วต่อเข้ารอบซักประวัติ (Box เดียวต่อรอบ)
    """
    text = raw_text.lower()

    if any(k in text for k in ['นัดหมาย', 'ใบนัด', 'ตารางนัด', 'appointment']):
        _send_appointment_reply(patient, reply_token)
        return
    if any(k in text for k in ['ผลตรวจ', 'รายงาน', 'ผลแล็บ', 'report']):
        _send_latest_report_reply(request, patient, reply_token)
        return
    if any(k in text for k in ['ติดต่อ', 'เบอร์โทร']):
        LineMessagingService.reply_message(reply_token, [{
            "type": "text",
            "text": "TSPI Precision Medicine Clinic\nโทร: 02-123-4567\nเวลาทำการ: จันทร์ - ศุกร์ 09:00 - 18:00 น."
        }])
        return

    if not patient:
        if reply_token:
            LineMessagingService.reply_message(reply_token, [_binding_card(request)])
        return

    if text in DONE_WORDS:
        open_box = Box.objects.filter(patient=patient, source=Box.Source.LINE, status=Box.Status.DRAFT).first()
        if open_box and (open_box.contents or {}).get('messages'):
            services_intake.close_session(open_box)
            reply = "ขอบคุณครับ คลินิกได้รับข้อมูลของคุณครบแล้ว ทีมแพทย์จะตรวจและติดต่อกลับครับ"
        else:
            reply = "ยังไม่มีข้อมูลอาการในรอบนี้ครับ พิมพ์เล่าอาการ หรือส่งรูป/ข้อความเสียงได้เลย"
        if reply_token:
            LineMessagingService.reply_message(reply_token, [{"type": "text", "text": reply}])
        return

    if text in START_WORDS:
        services_intake.open_session(patient, Box.Source.LINE)
        if reply_token:
            LineMessagingService.reply_message(reply_token, [_done_quick_reply(
                f"สวัสดีครับคุณ{patient.first_name} เล่าอาการได้เลยครับ ส่งข้อความ รูป หรือข้อความเสียงได้\n"
                "เมื่อเล่าครบแล้วกดปุ่ม \"เสร็จแล้ว\" ด้านล่าง"
            )])
        return

    box = services_intake.open_session(patient, Box.Source.LINE)
    is_first = not (box.contents or {}).get('messages')
    _, is_urgent, _ = detect_clinical_intent(raw_text)
    services_intake.append_message(box, 'text', text=raw_text, external_id=message_id, red_flag=is_urgent)
    if not reply_token:
        return
    if is_urgent:
        LineMessagingService.reply_message(reply_token, [_done_quick_reply(EMERGENCY_TEXT)])
        return
    question = services_intake.ai_followup_question(box)
    if question:
        LineMessagingService.reply_message(reply_token, [_done_quick_reply(question)])
    elif is_first:
        LineMessagingService.reply_message(reply_token, [_done_quick_reply(
            "รับทราบครับ เล่าเพิ่มเติมได้เรื่อย ๆ ส่งรูปหรือข้อความเสียงได้ เมื่อครบแล้วกด \"เสร็จแล้ว\""
        )])


def _handle_line_media(request: HttpRequest, patient: Patient, message_obj: dict, reply_token: str):
    """ดึงรูป/เสียง/วิดีโอจาก LINE ทันที (LINE เก็บไว้ไม่นาน) เข้ารหัสเก็บ แล้วต่อเข้ารอบซักประวัติ"""
    if not patient:
        if reply_token:
            LineMessagingService.reply_message(reply_token, [_binding_card(request)])
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

    if reply_token and (is_first or media is None):
        text = "ได้รับไฟล์แล้วครับ" if media else "ขออภัย ระบบดึงไฟล์นี้ไม่สำเร็จ รบกวนส่งใหม่อีกครั้งครับ"
        LineMessagingService.reply_message(reply_token, [_done_quick_reply(text)])


def _send_appointment_reply(patient: Patient, reply_token: str):
    """ตอบกลับด้วยใบนัดหมายแพทย์ล่าสุด"""
    if not patient:
        msg = {
            "type": "text",
            "text": "กรุณาเชื่อมต่อบัญชีผู้ป่วย (HN) กับระบบก่อนเพื่อดูใบนัดหมาย"
        }
        LineMessagingService.reply_message(reply_token, [msg])
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
        LineMessagingService.reply_message(reply_token, [card])
    else:
        msg = {
            "type": "text",
            "text": f"เรียนคุณ {patient.full_name}\nท่านยังไม่มีนัดหมายแพทย์ที่เปิดอยู่ในขณะนี้"
        }
        LineMessagingService.reply_message(reply_token, [msg])


def _send_latest_report_reply(request: HttpRequest, patient: Patient, reply_token: str):
    """ตอบกลับด้วยรายงานการแพทย์แม่นยำที่ได้รับการอนุมัติล่าสุด (Approved Report Only)"""
    if not patient:
        msg = {
            "type": "text",
            "text": "กรุณาเข้าสู่ระบบ Patient Portal เพื่อเชื่อมโยงบัญชีก่อนตรวจสอบรายงาน"
        }
        LineMessagingService.reply_message(reply_token, [msg])
        return

    # ดึงเฉพาะรายงานที่ได้รับการอนุมัติแล้วเท่านั้น (Pillar 15)
    report = AnalysisRecord.objects.filter(
        patient=patient,
        status__in=['approved', 'released']
    ).order_by('-created_at').first()

    if report:
        portal_url = request.build_absolute_uri(reverse('portal_patient:portal_report_detail', kwargs={'pk': report.pk}))
        card = LineFlexMessageBuilder.build_report_released_card(
            patient_name=patient.full_name,
            report_title=f"รายงานการแพทย์แม่นยำ 39 แกน #{report.pk}",
            portal_url=portal_url
        )
        LineMessagingService.reply_message(reply_token, [card])
    else:
        msg = {
            "type": "text",
            "text": f"เรียนคุณ {patient.full_name}\nขณะนี้ยังไม่มีรายงานที่แพทย์ลงนามอนุมัติเผยแพร่\nกรุณาติดต่อแพทย์ผู้ดูแลหากต้องการข้อมูลเพิ่มเติม"
        }
        LineMessagingService.reply_message(reply_token, [msg])


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
