"""
คำขอย้าย LINE ไปเวชระเบียนเดิม: เกิดเมื่อเบอร์จากฟอร์มตรงกับคนไข้ที่มีอยู่
แยกจากคิวตรวจทานทางคลินิก เพราะการอนุมัติคิวนั้นจะเขียนข้อความลงเวชระเบียน ไม่ใช่เชื่อมบัญชี
"""

from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog
from accounts.views import get_client_ip
from patients.line_service import LineFlexMessageBuilder, LineMessagingService
from patients.models_line import ClinicalReviewItem, LinePatientBinding

LINK_REQUEST_PREFIX = 'staff_req_'


def is_link_request(item: ClinicalReviewItem) -> bool:
    return bool(item.source_message and item.source_message.line_message_id.startswith(LINK_REQUEST_PREFIX))


def clinical_review_items():
    """รายการในคิวตรวจทานทางคลินิก ไม่รวมคำขอย้าย LINE"""
    return ClinicalReviewItem.objects.exclude(source_message__line_message_id__startswith=LINK_REQUEST_PREFIX)


def pending_link_requests():
    return (
        ClinicalReviewItem.objects
        .filter(status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
                source_message__line_message_id__startswith=LINK_REQUEST_PREFIX)
        .select_related('patient', 'source_message', 'source_message__line_user')
        .order_by('created_at')
    )


def _finish(item: ClinicalReviewItem, status: str, reviewer, request, action: str, changes: dict) -> None:
    item.status = status
    item.reviewer = reviewer
    item.reviewer_role = getattr(reviewer, 'role', 'STAFF')
    item.reviewed_at = timezone.now()
    item.save(update_fields=['status', 'reviewer', 'reviewer_role', 'reviewed_at', 'updated_at'])
    AuditLog.objects.create(
        user=reviewer, action=action, model='ClinicalReviewItem', object_id=str(item.pk),
        changes={'hn': item.patient.hn, 'line_user_id': item.source_message.line_user.line_user_id, **changes},
        client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )


def approve_link_request(item: ClinicalReviewItem, reviewer, request) -> None:
    line_user = item.source_message.line_user
    existing = item.patient
    with transaction.atomic():
        temporary = line_user.active_patient
        changes = {'verified_method': 'STAFF_LINE_LINK'}
        if temporary and temporary.pk != existing.pk:
            # เวชระเบียนที่เปิดตอนลงทะเบียนยังเก็บไว้ ถ้ามีข้อมูลอาการอยู่ให้เจ้าหน้าที่รวมเองได้
            temporary.line_user_id = None
            temporary.extra_data = {**(temporary.extra_data or {}), 'linked_to_hn': existing.hn}
            temporary.save(update_fields=['line_user_id', 'extra_data', 'updated_at'])
            LinePatientBinding.objects.filter(line_user=line_user, patient=temporary).update(
                status=LinePatientBinding.StatusChoices.REVOKED)
            changes['temporary_hn'] = temporary.hn
        LinePatientBinding.objects.update_or_create(
            line_user=line_user, patient=existing,
            defaults={'role': LinePatientBinding.RoleChoices.SELF, 'status': LinePatientBinding.StatusChoices.ACTIVE,
                      'verified_method': 'STAFF_LINE_LINK', 'verified_at': timezone.now()},
        )
        line_user.active_patient = existing
        line_user.save(update_fields=['active_patient', 'last_seen_at'])
        if not existing.line_user_id:
            existing.line_user_id = line_user.line_user_id
            existing.save(update_fields=['line_user_id', 'updated_at'])
        _finish(item, ClinicalReviewItem.StatusChoices.APPROVED, reviewer, request, 'LINE_BINDING_SUCCESS', changes)

    if line_user.bot_enabled:
        LineMessagingService.push_message(line_user.line_user_id, [LineFlexMessageBuilder.build_bot_card(
            'เชื่อมประวัติเดิมเรียบร้อย',
            f'เจ้าหน้าที่เชื่อม LINE นี้กับประวัติของคุณ{existing.first_name}แล้ว ดูใบนัดและผลตรวจเดิมได้เลยครับ',
            buttons=[LineFlexMessageBuilder.button_postback('ดูใบนัด', 'action=check_appointment'),
                     LineFlexMessageBuilder.button_postback('ดูผลตรวจ', 'action=check_report')],
        )])


def reject_link_request(item: ClinicalReviewItem, reviewer, request) -> None:
    _finish(item, ClinicalReviewItem.StatusChoices.REJECTED, reviewer, request, 'LINE_LINK_REQUEST_REJECTED', {})
