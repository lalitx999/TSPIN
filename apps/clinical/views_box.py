"""
Doctor Box Portal & Break-Glass Controllers (Phase 5).
Enforces Personal Box Password Authentication, HMAC Integrity Verification,
Full Multimedia Review (Audio, Lab, Video, SOAP, 39 Axes), and Audit Logging.
"""

import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.decorators import clinical_staff_required, doctor_only
from accounts.models import AuditLog
from accounts.views import get_client_ip
from clinical.models import Box

logger = logging.getLogger("tspi.box_portal")


def _back_to_box(request: HttpRequest, box: Box) -> HttpResponse:
    """กลับไปหน้าที่ส่งฟอร์มมา (เช่นหน้า LINE intake) ถ้าเป็น URL ภายในระบบ ไม่งั้นกลับหน้าดูกล่อง"""
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect('clinical:box_detail', box_id=box.id)


def is_box_unlocked(request: HttpRequest, box: Box) -> bool:
    """ปลดล็อกในเซสชันนี้แล้ว (รหัสเปิดกล่อง/Break-Glass) หรือเป็นผู้เปิดกล่องที่ตรวจเสร็จแล้ว"""
    return bool(request.session.get(f"box_unlocked_{box.id}")) or (
        box.opened_by_id == request.user.pk and box.status == Box.Status.REVIEWED
    )


@clinical_staff_required
def box_dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Doctor Box Dashboard.
    Displays incoming patient intake boxes with status, source, and HMAC verification badges.
    """
    status_filter = request.GET.get('status', '')
    source_filter = request.GET.get('source', '')
    query = request.GET.get('q', '').strip()

    boxes_qs = Box.objects.select_related('patient', 'opened_by').order_by('-created_at')

    if status_filter and status_filter in Box.Status.values:
        boxes_qs = boxes_qs.filter(status=status_filter)
    if source_filter and source_filter in Box.Source.values:
        boxes_qs = boxes_qs.filter(source=source_filter)
    if query:
        boxes_qs = boxes_qs.filter(patient__full_name__icontains=query) | boxes_qs.filter(patient__hn__icontains=query)

    boxes = list(boxes_qs[:100])

    # Precompute integrity check for UI badges
    for b in boxes:
        b.is_hmac_valid = b.verify_integrity()

    counts = {
        "all": Box.objects.count(),
        "done": Box.objects.filter(status=Box.Status.DONE).count(),
        "reviewed": Box.objects.filter(status=Box.Status.REVIEWED).count(),
        "draft": Box.objects.filter(status=Box.Status.DRAFT).count(),
    }

    return render(request, 'clinical/boxes/dashboard.html', {
        'boxes': boxes,
        'counts': counts,
        'status_filter': status_filter,
        'source_filter': source_filter,
        'query': query,
    })


@clinical_staff_required
def box_detail_view(request: HttpRequest, box_id) -> HttpResponse:
    """
    Multimedia Clinical Box Viewer.
    Requires doctor's Personal Box Password or Break-Glass session token.
    """
    box = get_object_or_404(Box.objects.select_related('patient', 'opened_by'), pk=box_id)
    is_valid_hmac = box.verify_integrity()

    is_unlocked = is_box_unlocked(request, box)

    # If unlocked, unpack contents for the clinical viewer
    contents = box.contents or {}
    soap = contents.get('soap', {})
    relevant_axes = contents.get('relevant_axes', [])
    lab_markers = contents.get('lab_markers', [])
    lab_correlations = contents.get('lab_correlations', [])
    video_observations = contents.get('video_observations', '')

    return render(request, 'clinical/boxes/detail.html', {
        'box': box,
        'is_valid_hmac': is_valid_hmac,
        'is_unlocked': is_unlocked,
        'soap': soap,
        'relevant_axes': relevant_axes,
        'lab_markers': lab_markers,
        'lab_correlations': lab_correlations,
        'video_observations': video_observations,
        'has_box_password': request.user.has_box_password,
    })


from django.core.cache import cache

@require_POST
@clinical_staff_required
def box_unlock_action(request: HttpRequest, box_id) -> HttpResponse:
    """
    Unlocks Box contents using Doctor's Personal Box Password.
    Enforces Rate Limiting (5 attempts / 5 mins) and Audit Trail.
    """
    box = get_object_or_404(Box, pk=box_id)
    cache_key = f"unlock_attempts_{request.user.id}_{box.id}"
    attempts = cache.get(cache_key, 0)

    if attempts >= 5:
        AuditLog.objects.create(
            user=request.user,
            action="BOX_UNLOCK_LOCKED_OUT",
            model="Box",
            object_id=str(box.id),
            changes={"attempts": attempts, "status": "Temporary lock (5 minutes)"},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        messages.error(request, "ท่านกรอกรหัสผ่านผิดเกินกำหนด (5 ครั้ง) ระบบระงับชั่วคราวเป็นเวลา 5 นาที (ใช้ Break-Glass Protocol หากมีเหตุฉุกเฉิน)")
        return _back_to_box(request, box)

    password = request.POST.get('box_password', '').strip()

    if not request.user.has_box_password:
        messages.error(request, "ท่านยังไม่ได้ตั้งรหัสผ่านเปิดกล่องส่วนตัว กรุณาตั้งรหัสผ่านก่อนเข้าใช้งาน")
        return _back_to_box(request, box)

    # Verify Personal Box Password
    if not request.user.check_box_password(password):
        cache.set(cache_key, attempts + 1, timeout=300)
        AuditLog.objects.create(
            user=request.user,
            action="BOX_UNLOCK_FAILED",
            model="Box",
            object_id=str(box.id),
            changes={"attempt": attempts + 1, "reason": "Incorrect personal box password"},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        remaining = 5 - (attempts + 1)
        if remaining > 0:
            messages.error(request, f"รหัสผ่านเปิดกล่องส่วนตัวไม่ถูกต้อง (เหลือโอกาสอีก {remaining} ครั้ง)")
        else:
            messages.error(request, "รหัสผ่านเปิดกล่องส่วนตัวไม่ถูกต้อง ระบบระงับการลองเป็นเวลา 5 นาที")
        return _back_to_box(request, box)

    # Unlock Successful -> Clear rate limiter
    cache.delete(cache_key)
    session_key = f"box_unlocked_{box.id}"
    request.session[session_key] = True

    if not box.opened_at:
        box.opened_by = request.user
        box.opened_at = timezone.now()
        box.save(update_fields=['opened_by', 'opened_at'])

    AuditLog.objects.create(
        user=request.user,
        action="BOX_UNLOCKED",
        model="Box",
        object_id=str(box.id),
        changes={"opened_by": request.user.username, "box_id": str(box.id)},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    messages.success(request, f"ปลดล็อกกล่องประวัติคนไข้ ({box.id.hex[:8]}) เรียบร้อยแล้ว")
    return _back_to_box(request, box)


@require_POST
@clinical_staff_required
def box_decision_action(request: HttpRequest, box_id) -> HttpResponse:
    """
    Records Doctor's Clinical Verdict & Plan for the Box.
    Transitions Box status to 'reviewed'.
    """
    box = get_object_or_404(Box, pk=box_id)
    # ต้องปลดล็อกกล่องก่อน (รหัสเปิดกล่องส่วนตัวหรือ Break-Glass) เหมือนหน้าดูกล่อง ยิง POST ตรงข้ามไม่ได้
    if not is_box_unlocked(request, box):
        AuditLog.objects.create(
            user=request.user, action="BOX_DECISION_DENIED_LOCKED", model="Box", object_id=str(box.id),
            client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        messages.error(request, "กรุณาปลดล็อกกล่องก่อนบันทึกคำสั่งการรักษา")
        return _back_to_box(request, box)
    decision = request.POST.get('decision', '').strip()
    doctor_notes = request.POST.get('doctor_notes', '').strip()

    if decision not in Box.Decision.values:
        messages.error(request, "คำวินิจฉัย/การสั่งการไม่ถูกต้อง")
        return _back_to_box(request, box)

    box.decision = decision
    box.doctor_notes = doctor_notes
    box.status = Box.Status.REVIEWED
    box.save(update_fields=['decision', 'doctor_notes', 'status'])

    AuditLog.objects.create(
        user=request.user,
        action="BOX_DECISION_RECORDED",
        model="Box",
        object_id=str(box.id),
        changes={"decision": decision, "doctor_notes": doctor_notes[:200]},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    messages.success(request, f"บันทึกคำสั่งการรักษาสำหรับกล่อง {box.id.hex[:8]} เรียบร้อยแล้ว")
    return _back_to_box(request, box)


@require_POST
@clinical_staff_required
def box_break_glass_action(request: HttpRequest, box_id) -> HttpResponse:
    """
    Emergency Break-Glass Protocol.
    Allows emergency unlocking when attending physician is unavailable.
    Records high-severity Immutable Audit Trail and sends urgent notifications.
    """
    box = get_object_or_404(Box, pk=box_id)
    reason = request.POST.get('break_glass_reason', '').strip()

    if not reason or len(reason) < 10:
        messages.error(request, "การเปิดกล่องฉุกเฉิน (Break-Glass) ต้องระบุเหตุผลความจำเป็นทางคลินิกอย่างละเอียด (อย่างน้อย 10 ตัวอักษร)")
        return _back_to_box(request, box)

    box.is_break_glass = True
    box.break_glass_reason = reason
    if not box.opened_at:
        box.opened_by = request.user
        box.opened_at = timezone.now()
    box.save(update_fields=['is_break_glass', 'break_glass_reason', 'opened_by', 'opened_at'])

    session_key = f"box_unlocked_{box.id}"
    request.session[session_key] = True

    # High-severity Audit Log
    AuditLog.objects.create(
        user=request.user,
        action="BREAK_GLASS_UNLOCKED",
        model="Box",
        object_id=str(box.id),
        changes={
            "severity": "CRITICAL",
            "reason": reason,
            "operator": request.user.username,
            "box_id": str(box.id)
        },
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    logger.warning(f"[BREAK-GLASS ALERT] Box {box.id} unlocked by {request.user.username}. Reason: {reason}")
    messages.warning(request, f"🚨 ปลดล็อกกล่องฉุกเฉิน (Break-Glass) สำเร็จ — มีการบันทึก Audit Log ระดับวิกฤตเรียบร้อยแล้ว")
    return _back_to_box(request, box)
