"""
เมนู "ซักถามพูดคุยผ่าน LINE": รายการรอบซักประวัติ, ดูบทสนทนา/ไฟล์, ให้ AI สรุป SOAP, บันทึกเข้าเวชระเบียน
หมอและพยาบาล (รวมผู้ช่วยพยาบาล) ใช้ได้ทุกขั้น โดยต้องปลดล็อกกล่องด้วยรหัสเปิดกล่องส่วนตัวก่อนเห็นเนื้อหา
"""

from django.contrib import messages
from django.db.models import Case, IntegerField, Value, When
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from accounts.decorators import clinical_staff_required
from accounts.models import AuditLog
from accounts.views import get_client_ip
from clinical import media_store, services_intake
from clinical.models import Box
from clinical.views_box import is_box_unlocked

INTAKE_SOURCES = (Box.Source.LINE, Box.Source.WEB, Box.Source.CLINIC)
STATUS_TABS = {
    'waiting': ('รอตรวจ', [Box.Status.DONE]),
    'open': ('กำลังคุย', [Box.Status.DRAFT]),
    'saved': ('บันทึกแล้ว', [Box.Status.REVIEWED]),
}


@clinical_staff_required
def intake_list_view(request: HttpRequest) -> HttpResponse:
    tab = request.GET.get('tab', 'waiting')
    if tab not in STATUS_TABS:
        tab = 'waiting'
    boxes = (
        Box.objects.filter(source__in=INTAKE_SOURCES, status__in=STATUS_TABS[tab][1], patient__isnull=False)
        .select_related('patient')
        .annotate(urgent_first=Case(When(contents__red_flag=True, then=Value(0)), default=Value(1), output_field=IntegerField()))
        .order_by('urgent_first', '-last_activity_at', '-created_at')[:100]
    )
    counts = {key: Box.objects.filter(source__in=INTAKE_SOURCES, status__in=st, patient__isnull=False).count()
              for key, (_, st) in STATUS_TABS.items()}
    return render(request, 'clinical/intake/list.html', {
        'boxes': boxes,
        'tab': tab,
        'tabs': [(key, label, counts[key]) for key, (label, _) in STATUS_TABS.items()],
    })


def _get_intake_box(box_id) -> Box:
    return get_object_or_404(Box.objects.select_related('patient', 'emr_history'), pk=box_id, source__in=INTAKE_SOURCES)


@clinical_staff_required
def intake_detail_view(request: HttpRequest, box_id) -> HttpResponse:
    box = _get_intake_box(box_id)
    unlocked = is_box_unlocked(request, box)
    contents = box.contents or {}
    chat_messages = []
    if unlocked:
        for m in contents.get('messages', []):
            at = parse_datetime(m.get('at') or '')
            chat_messages.append({**m, 'at_display': timezone.localtime(at) if at else None})
        AuditLog.objects.create(
            user=request.user, action='INTAKE_VIEWED', model='Box', object_id=str(box.id),
            client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
    return render(request, 'clinical/intake/detail.html', {
        'box': box,
        'is_unlocked': unlocked,
        'has_box_password': request.user.has_box_password,
        'chat_messages': chat_messages,
        'soap': (contents.get('committed_soap') or contents.get('soap') or {}) if unlocked else {},
        'soap_source': contents.get('soap_source', 'none'),
        'ai_meta': contents.get('ai_meta', {}),
    })


@require_POST
@clinical_staff_required
def intake_summarize_action(request: HttpRequest, box_id) -> HttpResponse:
    box = _get_intake_box(box_id)
    if not is_box_unlocked(request, box):
        messages.error(request, "กรุณาปลดล็อกกล่องก่อน")
    elif box.emr_history_id:
        messages.error(request, "กล่องนี้บันทึกเข้าเวชระเบียนแล้ว")
    else:
        ok, error = services_intake.summarize_with_ai(box, request.user)
        if ok:
            messages.success(request, "AI ร่าง SOAP เรียบร้อย กรุณาตรวจทานและแก้ไขก่อนบันทึก")
        else:
            messages.error(request, error)
    return redirect('clinical:intake_detail', box_id=box.id)


@require_POST
@clinical_staff_required
def intake_commit_action(request: HttpRequest, box_id) -> HttpResponse:
    box = _get_intake_box(box_id)
    if not is_box_unlocked(request, box):
        messages.error(request, "กรุณาปลดล็อกกล่องก่อน")
        return redirect('clinical:intake_detail', box_id=box.id)
    soap = {field: request.POST.get(field, '') for field in services_intake.SOAP_FIELDS}
    try:
        history = services_intake.commit_to_emr(box, request.user, soap)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('clinical:intake_detail', box_id=box.id)
    messages.success(request, "บันทึกเข้าเวชระเบียนเรียบร้อยแล้ว")
    return redirect('patients:patient_detail', patient_id=history.patient_id)


@clinical_staff_required
def intake_media_view(request: HttpRequest, box_id, media_id: str) -> HttpResponse:
    """เปิดไฟล์ที่เข้ารหัสไว้ เฉพาะผู้ที่ปลดล็อกกล่องแล้ว และบันทึก AuditLog ทุกครั้ง"""
    box = _get_intake_box(box_id)
    if not is_box_unlocked(request, box):
        raise Http404
    meta = next((m['media'] for m in (box.contents or {}).get('messages', [])
                 if m.get('media') and m['media'].get('media_id') == media_id), None)
    data = media_store.read_decrypted(meta) if meta else None
    if data is None:
        raise Http404
    AuditLog.objects.create(
        user=request.user, action='INTAKE_MEDIA_VIEWED', model='Box', object_id=str(box.id),
        changes={'media_id': media_id, 'content_type': meta.get('content_type')},
        client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    response = HttpResponse(data, content_type=meta.get('content_type', 'application/octet-stream'))
    response['Cache-Control'] = 'no-store'
    response['Content-Disposition'] = 'inline'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@require_POST
@clinical_staff_required
def voice_soap_action(request: HttpRequest) -> HttpResponse:
    """
    บันทึกเสียงแพทย์ (ถอดความในเบราว์เซอร์) -> กล่องช่องทางคลินิก -> AI ร่าง SOAP -> หน้าตรวจทาน/บันทึกเข้าเวชระเบียน
    ผู้บันทึกเป็นเจ้าของเนื้อหาเอง จึงปลดล็อกกล่องนี้ให้ในเซสชันทันที
    """
    from patients.models import Patient
    patient = get_object_or_404(Patient, pk=request.POST.get('patient_id') or 0)
    transcript = request.POST.get('transcript', '').strip()
    if not transcript:
        messages.error(request, "ยังไม่มีข้อความจากการบันทึกเสียง")
        return redirect('patients:doctor_voice_form')

    box = Box.objects.create(
        patient=patient, source=Box.Source.CLINIC, status=Box.Status.DONE,
        contents={'messages': [], 'soap': {}, 'soap_source': 'none', 'origin': 'voice_dictation'},
        last_activity_at=timezone.now(), processed_at=timezone.now(), opened_by=request.user, opened_at=timezone.now(),
    )
    services_intake.append_message(box, 'text', text=transcript, sender='staff')
    request.session[f"box_unlocked_{box.id}"] = True
    AuditLog.objects.create(
        user=request.user, action='VOICE_DICTATION_CAPTURED', model='Box', object_id=str(box.id),
        changes={'patient_hn': patient.hn, 'length': len(transcript)},
        client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )

    ok, error = services_intake.summarize_with_ai(box, request.user)
    if ok:
        messages.success(request, "AI ร่าง SOAP จากเสียงบันทึกแล้ว กรุณาตรวจทานก่อนบันทึกเข้าเวชระเบียน")
    else:
        messages.warning(request, f"{error} สามารถพิมพ์ SOAP เองแล้วบันทึกได้")
    return redirect('clinical:intake_detail', box_id=box.id)
