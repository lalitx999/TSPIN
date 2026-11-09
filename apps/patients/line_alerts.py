"""
แจ้งเตือนจากงาน LINE: ทีมแพทย์เมื่อมีเคสฉุกเฉิน และคนไข้เมื่อทีมแพทย์ตรวจข้อมูลแล้ว
อีเมลไม่ใส่ชื่อหรืออาการ เพราะเป็นช่องทางนอกระบบ ให้กดลิงก์เข้ามาดูในระบบที่มีการตรวจสิทธิ์
"""

import logging
from urllib.parse import urlencode

from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Q
from django.urls import reverse

from accounts.models import User
from patients import line_ai
from patients.line_service import LineMessagingService, text_message
from patients.models_line import LinePatientBinding, LineUser, bot_idle_cutoff

logger = logging.getLogger(__name__)

EMERGENCY_ALERT_ROLES = (User.Role.DOCTOR, User.Role.NURSE, User.Role.NURSING_ASSISTANT, User.Role.ADMIN)


def notify_emergency(request, box) -> None:
    recipients = _emergency_recipients()
    if not recipients:
        logger.warning("[LINE Alert] No staff email to notify about an emergency case")
        return
    url = request.build_absolute_uri(reverse('clinical:intake_detail', kwargs={'box_id': box.id}))
    line_ai._run_in_background(_send_emergency_email, recipients, url)


def notify_unbound_emergency(request, line_user) -> None:
    """คนที่ยังไม่ลงทะเบียนไม่มีกล่องให้ติดธง จึงกันอีเมลซ้ำด้วยเวลา 1 ชั่วโมงต่อคนแทน"""
    if not cache.add(f"line_emergency_{line_user.line_user_id}", 1, timeout=60 * 60):
        return
    recipients = _emergency_recipients()
    if not recipients:
        logger.warning("[LINE Alert] No staff email to notify about an emergency case")
        return
    url = request.build_absolute_uri(f"{reverse('patients:staff_inbox')}?{urlencode({'user_id': line_user.line_user_id})}")
    line_ai._run_in_background(_send_emergency_email, recipients, url)


def _emergency_recipients() -> list:
    return list(
        User.objects.filter(is_active=True, role__in=EMERGENCY_ALERT_ROLES).exclude(email='')
        .values_list('email', flat=True)
    )


def _send_emergency_email(recipients: list, url: str) -> None:
    try:
        send_mail(
            subject='[TSPI] มีเคสฉุกเฉินใหม่จาก LINE',
            message=f"มีคนไข้ส่งข้อความที่อาจเป็นภาวะฉุกเฉินทาง LINE กรุณาตรวจทันที\n{url}",
            from_email=None,
            recipient_list=recipients,
        )
    except Exception as e:
        logger.error(f"[LINE Alert] Emergency email failed: {type(e).__name__}")


def notify_patient_reviewed(box) -> None:
    """บอกคนไข้ว่าทีมแพทย์ตรวจแล้ว ไม่ใส่ผลการตรวจในแชท และไม่รบกวนคนที่บอทปิดไปแล้ว (แชทเป็นของทีมขาย)"""
    patient = box.patient
    bound_line_users = LineUser.objects.filter(
        Q(active_patient=patient)
        | Q(line_user_id=patient.line_user_id or '')
        | Q(patient_bindings__patient=patient, patient_bindings__status=LinePatientBinding.StatusChoices.ACTIVE),
        bot_enabled=True, bot_last_active_at__gte=bot_idle_cutoff(),
    ).distinct()
    card = text_message('ทีมแพทย์ได้อ่านข้อมูลที่คุณเล่าไว้เรียบร้อยแล้วครับ หากต้องทำอะไรเพิ่มเติม เจ้าหน้าที่จะติดต่อกลับ')
    for line_user in bound_line_users:
        LineMessagingService.push_message(line_user.line_user_id, [card])
