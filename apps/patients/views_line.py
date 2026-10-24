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
from clinical.models import AnalysisRecord
from patients.line_service import LineSecurity, LineFlexMessageBuilder, LineMessagingService

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
    patient = Patient.objects.filter(line_user_id=line_user_id).first()

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
        if patient:
            msg = LineFlexMessageBuilder.build_welcome_card()
        else:
            # สร้างการ์ดพร้อมปุ่มเชื่อมต่อ HN
            binding_url = request.build_absolute_uri(reverse('portal_patient:portal_login'))
            msg = LineFlexMessageBuilder.build_welcome_card(binding_url=binding_url)

        if reply_token:
            LineMessagingService.reply_message(reply_token, [msg])

    elif event_type == 'message':
        message_obj = event.get('message', {})
        if message_obj.get('type') == 'text':
            text = (message_obj.get('text') or '').strip().lower()
            _handle_line_text_command(request, patient, line_user_id, text, reply_token)

    elif event_type == 'postback':
        postback_data = event.get('postback', {}).get('data', '')
        if 'action=check_appointment' in postback_data:
            _send_appointment_reply(patient, reply_token)
        elif 'action=check_report' in postback_data:
            _send_latest_report_reply(request, patient, reply_token)


def _handle_line_text_command(request: HttpRequest, patient: Patient, line_user_id: str, text: str, reply_token: str):
    """จัดการคำสั่งข้อความจากผู้ป่วยบน LINE OA"""
    if not reply_token:
        return

    if any(k in text for k in ['นัดหมาย', 'ใบนัด', 'ตารางนัด', 'appointment']):
        _send_appointment_reply(patient, reply_token)
    elif any(k in text for k in ['ผลตรวจ', 'รายงาน', 'ผลแล็บ', 'report']):
        _send_latest_report_reply(request, patient, reply_token)
    elif any(k in text for k in ['ติดต่อ', 'เบอร์โทร', 'คลินิก']):
        msg = {
            "type": "text",
            "text": "TSPI Precision Medicine Clinic\nโทร: 02-123-4567\nเวลาทำการ: จันทร์ - ศุกร์ 09:00 - 18:00 น."
        }
        LineMessagingService.reply_message(reply_token, [msg])
    else:
        # Default Welcome / Menu Card
        if patient:
            msg = LineFlexMessageBuilder.build_welcome_card()
        else:
            binding_url = request.build_absolute_uri(reverse('portal_patient:portal_login'))
            msg = LineFlexMessageBuilder.build_welcome_card(binding_url=binding_url)
        LineMessagingService.reply_message(reply_token, [msg])


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
