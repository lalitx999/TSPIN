"""
API ของฟอร์มซักประวัติในหน้าแฟ้มคนไข้ (เรียกจาก static/js/visit_form.js ตอบเป็น JSON)
ทุกจุดทำงานกับร่างของผู้ใช้คนนั้นเท่านั้น ดูกติกาของร่างใน clinical/services_visit.py
"""

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from accounts.decorators import clinical_staff_required
from clinical import services_intake, services_visit
from clinical.services_visit import VisitError
from patients.forms import VisitVitalsForm
from patients.models import Patient

VITAL_FIELDS = tuple(VisitVitalsForm.RANGES)


def _fail(message: str, status: int = 400, **extra) -> JsonResponse:
    return JsonResponse({'ok': False, 'error': message, **extra}, status=status)


def _vitals_input(request: HttpRequest) -> dict:
    return {k: request.POST.get(k, '').strip() for k in VITAL_FIELDS}


def _soap_input(request: HttpRequest) -> dict:
    return {k: request.POST.get(k, '').strip() for k in services_intake.SOAP_FIELDS}


def _draft(request: HttpRequest, patient: Patient):
    return services_visit.get_draft(patient, request.user, request.POST.get('box_id') or request.GET.get('box_id'))


def _image_payload(box, meta) -> dict:
    from django.urls import reverse
    return {'media_id': meta['media_id'],
            'url': reverse('clinical:intake_media', kwargs={'box_id': box.id, 'media_id': meta['media_id']})}


@require_POST
@clinical_staff_required
def visit_save_view(request: HttpRequest, patient_id: int) -> JsonResponse:
    """บันทึกร่างอัตโนมัติ (สร้างร่างเมื่อเริ่มพิมพ์ครั้งแรก)"""
    patient = get_object_or_404(Patient, pk=patient_id)
    box_id = request.POST.get('box_id')
    try:
        box = services_visit.get_draft(patient, request.user, box_id) if box_id else \
            services_visit.get_or_create_draft(patient, request.user)
    except VisitError as exc:
        return _fail(str(exc), status=404)
    request.session[f"box_unlocked_{box.id}"] = True  # ผู้สร้างร่างเปิดรูปของตัวเองได้
    has_soap = request.POST.get('has_soap') == '1'
    services_visit.save_draft(box, request.POST.get('history_text', ''), _vitals_input(request),
                              soap=_soap_input(request) if has_soap else None)
    return JsonResponse({'ok': True, 'box_id': str(box.id)})


@require_POST
@clinical_staff_required
def visit_image_add_view(request: HttpRequest, patient_id: int) -> JsonResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    upload = request.FILES.get('image')
    if upload is None:
        return _fail('ไม่พบไฟล์รูป')
    try:
        box = services_visit.get_draft(patient, request.user, request.POST.get('box_id')) if request.POST.get('box_id') \
            else services_visit.get_or_create_draft(patient, request.user)
        request.session[f"box_unlocked_{box.id}"] = True
        meta = services_visit.add_image(box, upload.read(), upload.content_type or '', request.user)
    except VisitError as exc:
        return _fail(str(exc))
    return JsonResponse({'ok': True, 'box_id': str(box.id), 'image': _image_payload(box, meta)})


@require_POST
@clinical_staff_required
def visit_image_remove_view(request: HttpRequest, patient_id: int) -> JsonResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    try:
        services_visit.remove_image(_draft(request, patient), request.POST.get('media_id', ''), request.user)
    except VisitError as exc:
        return _fail(str(exc))
    return JsonResponse({'ok': True})


@require_POST
@clinical_staff_required
def visit_summarize_view(request: HttpRequest, patient_id: int) -> JsonResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    try:
        box = _draft(request, patient)
    except VisitError as exc:
        return _fail(str(exc), status=404)
    services_visit.save_draft(box, request.POST.get('history_text', ''), _vitals_input(request))
    form = VisitVitalsForm(request.POST)
    if not form.is_valid():
        return _fail('กรุณากรอกสัญญาณชีพให้ครบและถูกต้องก่อน', errors=form.error_list(), fields=list(form.errors))
    try:
        soap = services_visit.summarize(box, form.vitals(), request.user)
    except VisitError as exc:
        return _fail(str(exc), status=502, can_manual=True)
    return JsonResponse({'ok': True, 'soap': soap, 'gateway': (box.contents.get('ai_meta') or {}).get('gateway', '')})


@require_POST
@clinical_staff_required
def visit_manual_view(request: HttpRequest, patient_id: int) -> JsonResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    try:
        services_visit.unlock_manual_soap(_draft(request, patient), request.user)
    except VisitError as exc:
        return _fail(str(exc), status=404)
    return JsonResponse({'ok': True})


@require_POST
@clinical_staff_required
def visit_commit_view(request: HttpRequest, patient_id: int) -> JsonResponse:
    """บันทึกเข้าเวชระเบียน: ต้องยืนยันว่าตรวจทานแล้ว และสัญญาณชีพผ่านการตรวจค่า"""
    patient = get_object_or_404(Patient, pk=patient_id)
    try:
        box = _draft(request, patient)
    except VisitError as exc:
        return _fail(str(exc), status=404)
    if request.POST.get('reviewed') != '1':
        return _fail('กรุณาตรวจทาน SOAP และติ๊กยืนยันก่อนบันทึก')
    form = VisitVitalsForm(request.POST)
    if not form.is_valid():
        return _fail('กรุณากรอกสัญญาณชีพให้ครบและถูกต้องก่อน', errors=form.error_list(), fields=list(form.errors))
    services_visit.save_draft(box, request.POST.get('history_text', ''), _vitals_input(request))
    try:
        history = services_visit.commit(box, request.user, _soap_input(request), form.vitals())
    except ValueError as exc:  # รวม VisitError และข้อผิดพลาดจาก commit_to_emr
        return _fail(str(exc))
    html = render_to_string('patients/partials/history_soap_card.html', {'history': history}, request=request)
    return JsonResponse({'ok': True, 'history_id': history.pk, 'patient_id': patient.pk, 'html': html})


@require_POST
@clinical_staff_required
def visit_discard_view(request: HttpRequest, patient_id: int) -> JsonResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    try:
        services_visit.discard(_draft(request, patient), request.user)
    except VisitError as exc:
        return _fail(str(exc), status=404)
    return JsonResponse({'ok': True})
