"""
TSPI Staff Portal Controllers (Option C).
Unified Inbox, Clinical Review Queue, and Staff Dashboard for Doctors & Nurses.
Enforces:
1. Strict Role-Based Access Control (@clinical_staff_required / @doctor_only)
2. Database-Level Race Condition Prevention (select_for_update)
3. Live Polling & Optimistic UI Support
4. Tamper-Proof Audit Logging (PDPA & HIPAA Compliance)
"""

import logging
from datetime import timedelta
from typing import Dict, Any

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Max

from accounts.decorators import clinical_staff_required, doctor_only
from accounts.models import AuditLog, User
from patients.models import (
    Patient,
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
    PatientHistory,
)

logger = logging.getLogger('tspi.clinical')


# ==============================================================================
# 1. STAFF DASHBOARD (/staff/ or /staff/dashboard/)
# ==============================================================================

@clinical_staff_required
def staff_dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    หน้าหลักสรุปสถานะการทำงานของทีมแพทย์และพยาบาล
    แสดงจำนวนเคสที่รอตรวจทาน เคสด่วนวิกฤต และสถิติการอนุมัติประจำวัน
    """
    today = timezone.now().date()

    # สถิติคิวตรวจทาน
    pending_level1 = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE
    ).count()

    pending_level2 = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC
    ).count()

    approved_today = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.APPROVED,
        reviewed_at__date=today
    ).count()

    rejected_today = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.REJECTED,
        reviewed_at__date=today
    ).count()

    # รายการเคสด่วนวิกฤต (Urgent Items) ที่ยังรอการอนุมัติ (Sort ขึ้นบนสุด)
    urgent_items = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC
    ).select_related('patient', 'source_message').order_by('-created_at')[:5]

    # คำนวณระยะเวลารอของแต่ละเคสด่วน
    now = timezone.now()
    urgent_list = []
    for item in urgent_items:
        wait_minutes = int((now - item.created_at).total_seconds() / 60)
        urgent_list.append({
            'item': item,
            'wait_minutes': wait_minutes,
            'is_long_wait': wait_minutes > 15
        })

    # ข้อความล่าสุดจาก LINE Unified Inbox
    recent_messages = CommunicationRecord.objects.select_related(
        'line_user', 'patient'
    ).order_by('-created_at')[:8]

    return render(request, 'patients/staff_dashboard.html', {
        'pending_level1': pending_level1,
        'pending_level2': pending_level2,
        'total_pending': pending_level1 + pending_level2,
        'approved_today': approved_today,
        'rejected_today': rejected_today,
        'urgent_items': urgent_list,
        'recent_messages': recent_messages,
        'is_doctor': request.user.role == User.Role.DOCTOR or request.user.is_superuser,
    })


# ==============================================================================
# 2. UNIFIED INBOX (/staff/inbox/)
# ==============================================================================

@clinical_staff_required
def staff_inbox_view(request: HttpRequest) -> HttpResponse:
    """
    หน้าจอรวมแชท LINE Unified Inbox สไตล์ Two-Pane
    - ฝั่งซ้าย: รายชื่อผู้ติดต่อ LINE พร้อมตัวแสดงบริบทคนไข้ที่ดูแล
    - ฝั่งขวา: ข้อความสนทนาใน Thread ของผู้ติดต่อที่เลือก
    """
    filter_type = request.GET.get('filter', 'all')  # 'all' หรือ 'clinical'
    selected_user_id = request.GET.get('user_id', '').strip()

    # ดึงรายชื่อ LineUser ที่มีข้อความเข้ามา พร้อมนับจำนวนข้อความและเวลาล่าสุด
    users_qs = LineUser.objects.annotate(
        last_message_at=Max('messages__created_at'),
        clinical_count=Count('messages', filter=Q(messages__is_clinical_candidate=True)),
        total_messages=Count('messages')
    ).filter(total_messages__gt=0).select_related('active_patient').order_by('-last_message_at')

    if filter_type == 'clinical':
        users_qs = users_qs.filter(clinical_count__gt=0)

    user_list = list(users_qs[:30])

    # กำหนดผู้ติดต่อเป้าหมายที่กำลังเปิดดู
    current_line_user = None
    if selected_user_id:
        current_line_user = LineUser.objects.filter(line_user_id=selected_user_id).select_related('active_patient').first()

    if not current_line_user and user_list:
        current_line_user = user_list[0]

    # ดึงข้อความใน Thread ของผู้ติดต่อปัจจุบัน
    messages_thread = []
    bindings = []
    if current_line_user:
        messages_thread = current_line_user.messages.select_related('patient').order_by('created_at')[:100]
        bindings = current_line_user.patient_bindings.filter(
            status=LinePatientBinding.StatusChoices.ACTIVE
        ).select_related('patient')

    return render(request, 'patients/staff_inbox.html', {
        'user_list': user_list,
        'current_line_user': current_line_user,
        'messages_thread': messages_thread,
        'bindings': bindings,
        'filter_type': filter_type,
        'is_doctor': request.user.role == User.Role.DOCTOR or request.user.is_superuser,
    })


@clinical_staff_required
@require_POST
def staff_create_review_from_message_api(request: HttpRequest) -> JsonResponse:
    """
    สร้าง ClinicalReviewItem จากข้อความใน Inbox ด้วยคลิกเดียว
    """
    msg_id = request.POST.get('message_id', '').strip()
    review_type = request.POST.get('review_type', ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE)
    
    comm_record = get_object_or_404(CommunicationRecord, pk=msg_id)
    if not comm_record.patient:
        return JsonResponse({
            'status': 'error',
            'message': 'ไม่สามารถส่งเข้าคิวได้เนื่องจากผู้ใช้นี้ยังไม่ได้ผูกบัญชีคนไข้'
        }, status=400)

    # ตรวจสอบว่าเคยสร้างไปแล้วหรือไม่
    existing = ClinicalReviewItem.objects.filter(source_message=comm_record).first()
    if existing:
        return JsonResponse({
            'status': 'error',
            'message': f'ข้อความนี้ถูกส่งเข้าคิวตรวจทานแล้ว (#{existing.pk})'
        }, status=400)

    review_item = ClinicalReviewItem.objects.create(
        patient=comm_record.patient,
        source_message=comm_record,
        review_type=review_type,
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_notes=f"สร้างโดยเจ้าหน้าที่ ({request.user.username}):\n{comm_record.content}"
    )

    # อัปเดต flag ของข้อความ
    comm_record.is_clinical_candidate = True
    comm_record.save(update_fields=['is_clinical_candidate'])

    # AuditLog
    AuditLog.objects.create(
        action='CLINICAL_REVIEW_CREATED_MANUAL',
        user=request.user,
        model='ClinicalReviewItem',
        object_id=str(review_item.pk),
        client_ip=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        changes={
            'review_item_id': review_item.pk,
            'hn': comm_record.patient.hn,
            'review_type': review_type
        }
    )

    return JsonResponse({
        'status': 'ok',
        'message': f'ส่งข้อความเข้าคิวตรวจทานสำเร็จ (รหัส #{review_item.pk})',
        'review_item_id': review_item.pk
    })


# ==============================================================================
# 3. CLINICAL REVIEW QUEUE (/staff/review-queue/)
# ==============================================================================

@clinical_staff_required
def staff_review_queue_view(request: HttpRequest) -> HttpResponse:
    """
    หน้าจอจัดการคิวตรวจทานทางคลินิก (Human-in-the-Loop Clinical Review Queue)
    - Tab 1: Level 1 Intake (พยาบาล + แพทย์)
    - Tab 2: Level 2 Diagnostic (แพทย์เท่านั้น, พยาบาลดูได้อย่างเดียว)
    """
    status_filter = request.GET.get('status', ClinicalReviewItem.StatusChoices.PENDING_REVIEW)
    active_tab = request.GET.get('tab', 'level1')

    base_qs = ClinicalReviewItem.objects.select_related(
        'patient', 'source_message', 'source_message__line_user', 'reviewer'
    ).order_by('-created_at')

    if status_filter != 'all':
        base_qs = base_qs.filter(status=status_filter)

    level1_items = base_qs.filter(review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE)
    level2_items = base_qs.filter(review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC)

    # นับจำนวนสำหรับ Badges
    p_level1_count = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE
    ).count()

    p_level2_count = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC
    ).count()

    is_doctor = request.user.role == User.Role.DOCTOR or request.user.is_superuser

    return render(request, 'patients/staff_review_queue.html', {
        'level1_items': level1_items[:50],
        'level2_items': level2_items[:50],
        'p_level1_count': p_level1_count,
        'p_level2_count': p_level2_count,
        'status_filter': status_filter,
        'active_tab': active_tab,
        'is_doctor': is_doctor,
    })


@clinical_staff_required
@require_GET
def staff_review_queue_poll_api(request: HttpRequest) -> JsonResponse:
    """
    Real-time Polling API (5 วินาที) สำหรับตรวจสอบจำนวนเคสรอตรวจทานแบบ Real-time
    """
    p_level1_count = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE
    ).count()

    p_level2_count = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_2_DIAGNOSTIC
    ).count()

    # ตรวจสอบว่ามีรายการใหม่เข้ามาในช่วง 10 วินาทีล่าสุดหรือไม่
    recent_threshold = timezone.now() - timedelta(seconds=10)
    has_new_items = ClinicalReviewItem.objects.filter(
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        created_at__gte=recent_threshold
    ).exists()

    return JsonResponse({
        'status': 'ok',
        'pending_level1': p_level1_count,
        'pending_level2': p_level2_count,
        'total_pending': p_level1_count + p_level2_count,
        'has_new_items': has_new_items,
        'timestamp': timezone.now().isoformat()
    })


# ==============================================================================
# 4. APPROVE & REJECT ACTIONS (ป้องกัน Race Condition ด้วย select_for_update)
# ==============================================================================

@clinical_staff_required
@require_POST
def staff_approve_review_item_api(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    อนุมัติรายการในคิวตรวจทาน และแปลงข้อมูลเข้าสู่เวชระเบียนผู้ป่วย (EMR PatientHistory)
    กฎความปลอดภัย:
    1. ป้องกัน Race Condition ด้วย select_for_update() ใน Database Transaction
    2. บังคับใช้ Model-level RBAC: หากเป็น LEVEL_2_DIAGNOSTIC แต่ผู้ใช้ไม่ใช่แพทย์ จะติด PermissionDenied
    """
    clinical_summary = request.POST.get('clinical_summary', '').strip()
    category = request.POST.get('category', 'soap').strip()

    try:
        with transaction.atomic():
            # 1. ล็อกแถวข้อมูลในฐานข้อมูล ป้องกันคนกดพร้อมกัน (Race Condition Guard)
            item = ClinicalReviewItem.objects.select_for_update().filter(pk=item_id).first()
            if not item:
                return JsonResponse({'status': 'error', 'message': 'ไม่พบรายการที่ระบุ'}, status=404)

            if item.status != ClinicalReviewItem.StatusChoices.PENDING_REVIEW:
                return JsonResponse({
                    'status': 'error',
                    'message': f'รายการนี้ได้รับการประมวลผลแล้วโดยผู้อื่น (สถานะปัจจุบัน: {item.get_status_display()})'
                }, status=409)

            # 2. บันทึกการอนุมัติผ่านโมเดล method ที่มี Guard RBAC
            try:
                history = item.approve(
                    reviewer_user=request.user,
                    clinical_summary=clinical_summary,
                    category=category
                )
            except PermissionDenied as pe:
                return JsonResponse({
                    'status': 'error',
                    'message': str(pe)
                }, status=403)

            # 3. บันทึก PDPA AuditLog
            AuditLog.objects.create(
                action='CLINICAL_REVIEW_APPROVED',
                user=request.user,
                model='ClinicalReviewItem',
                object_id=str(item.pk),
                client_ip=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                changes={
                    'item_id': item.pk,
                    'hn': item.patient.hn,
                    'review_type': item.review_type,
                    'reviewer_role': getattr(request.user, 'role', 'unknown'),
                    'history_id': history.pk if history else None
                }
            )

            return JsonResponse({
                'status': 'ok',
                'message': f'อนุมัติรายการเรียบร้อยแล้ว บันทึกลงเวชระเบียนคนไข้ {item.patient.full_name} (HN: {item.patient.hn}) สำเร็จ',
                'item_id': item.pk,
                'history_id': history.pk if history else None
            })

    except Exception as e:
        logger.error(f"[Staff UI] Error approving review item #{item_id}: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'เกิดข้อผิดพลาดในการอนุมัติ: {str(e)}'}, status=500)


@clinical_staff_required
@require_POST
def staff_reject_review_item_api(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    ปฏิเสธรายการในคิวตรวจทาน (ไม่บันทึกลง EMR) พร้อมระบุเหตุผล
    """
    reason = request.POST.get('reason', '').strip()
    if not reason:
        reason = 'ไม่เกี่ยวข้องกับการรักษาพยาบาลหรืออาการทางคลินิก'

    try:
        with transaction.atomic():
            item = ClinicalReviewItem.objects.select_for_update().filter(pk=item_id).first()
            if not item:
                return JsonResponse({'status': 'error', 'message': 'ไม่พบรายการที่ระบุ'}, status=404)

            if item.status != ClinicalReviewItem.StatusChoices.PENDING_REVIEW:
                return JsonResponse({
                    'status': 'error',
                    'message': f'รายการนี้ได้รับการประมวลผลแล้วโดยผู้อื่น (สถานะปัจจุบัน: {item.get_status_display()})'
                }, status=409)

            item.status = ClinicalReviewItem.StatusChoices.REJECTED
            item.reviewer = request.user
            item.reviewer_role = getattr(request.user, 'role', 'STAFF')
            item.reviewed_at = timezone.now()
            item.rejection_reason = reason
            item.save(update_fields=['status', 'reviewer', 'reviewer_role', 'reviewed_at', 'rejection_reason', 'updated_at'])

            AuditLog.objects.create(
                action='CLINICAL_REVIEW_REJECTED',
                user=request.user,
                model='ClinicalReviewItem',
                object_id=str(item.pk),
                client_ip=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                changes={
                    'item_id': item.pk,
                    'hn': item.patient.hn,
                    'reason': reason,
                    'reviewer_role': item.reviewer_role
                }
            )

            return JsonResponse({
                'status': 'ok',
                'message': 'ปฏิเสธคำขอเรียบร้อยแล้ว',
                'item_id': item.pk
            })

    except Exception as e:
        logger.error(f"[Staff UI] Error rejecting review item #{item_id}: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'เกิดข้อผิดพลาด: {str(e)}'}, status=500)


LINE_TEXT_MAX = 2000


@clinical_staff_required
@require_POST
def staff_inbox_reply_action(request: HttpRequest) -> HttpResponse:
    """
    ตอบแชท LINE จากหน้า Inbox (Push Message) เฉพาะผู้มีสิทธิ์ตอบแชท
    บันทึกเป็น CommunicationRecord ขาออกพร้อมผู้ส่ง และ AuditLog
    """
    from django.contrib import messages as flash
    from django.urls import reverse
    import uuid
    from patients.line_service import LineMessagingService

    line_user_id = request.POST.get('line_user_id', '').strip()
    text = request.POST.get('text', '').strip()
    back = f"{reverse('root_staff_inbox')}?user_id={line_user_id}"

    if not request.user.may_reply_line_chat:
        AuditLog.objects.create(
            user=request.user, action='LINE_REPLY_DENIED', model='LineUser', object_id=line_user_id,
            client_ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        raise PermissionDenied("บัญชีนี้ไม่มีสิทธิ์ตอบแชท LINE")

    line_user = get_object_or_404(LineUser, line_user_id=line_user_id)
    if not text:
        flash.error(request, "กรุณาพิมพ์ข้อความ")
        return redirect(back)
    if len(text) > LINE_TEXT_MAX:
        flash.error(request, f"ข้อความยาวเกิน {LINE_TEXT_MAX} ตัวอักษร")
        return redirect(back)

    if not LineMessagingService.push_message(line_user.line_user_id, [{"type": "text", "text": text}]):
        flash.error(request, "ส่งข้อความไป LINE ไม่สำเร็จ กรุณาลองใหม่")
        return redirect(back)

    record = CommunicationRecord.objects.create(
        line_message_id=f"out_{uuid.uuid4().hex}",
        line_user=line_user,
        patient=line_user.active_patient,
        direction=CommunicationRecord.DirectionChoices.OUTGOING,
        message_type=CommunicationRecord.MessageTypeChoices.TEXT,
        content=text,
        sent_by=request.user,
        raw_payload={},
    )
    AuditLog.objects.create(
        user=request.user, action='LINE_REPLY_SENT', model='CommunicationRecord', object_id=str(record.pk),
        changes={'line_user_id': line_user.line_user_id, 'length': len(text)},
        client_ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    return redirect(back)
