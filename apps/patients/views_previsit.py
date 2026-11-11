"""
คิวคนไข้วันนี้ (/doctor/pre-visit/) แทนหน้า "Pre-Visit Anamnesis" เดิมที่แสดงข้อความตัวอย่างเหมือนข้อมูลจริง

ซ้าย: นัดของวันจากปฏิทิน (+ ค้นหาคนไข้ walk-in)
ขวา: สรุปก่อนเข้าห้องตรวจ จากข้อมูลจริงเท่านั้น ช่องไหนไม่มีข้อมูลต้องบอกตรง ๆ
     (โดยเฉพาะแพ้ยา: ไม่มีข้อมูล = "ยังไม่ได้บันทึก ต้องถาม" ห้ามขึ้นว่า "ปฏิเสธการแพ้")
ปุ่ม "เริ่มตรวจ": บันทึกว่าคนไข้มาตรวจแล้ว แล้วเปิดฟอร์มบันทึกการตรวจในแฟ้มคนไข้
"""

from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import clinical_staff_required
from accounts.models import AuditLog, User
from accounts.views import get_client_ip
from clinical import services_visit
from clinical.invariants import CANONICAL_39_AXES
from clinical.models import Box
from patients.models import Appointment, Patient
from patients.views_appointments import STATUS_SHORT, THAI_MONTHS

THAI_DAYS = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์']  # date.weekday()
AXIS_THRESHOLD = 60


def thai_long_date(day: date) -> str:
    return f"วัน{THAI_DAYS[day.weekday()]}ที่ {day.day} {THAI_MONTHS[day.month - 1]} {day.year + 543}"


def _day_from(request: HttpRequest, today: date) -> date:
    try:
        return date.fromisoformat(request.GET.get('date', ''))
    except ValueError:
        return today


def _briefing(patient: Patient, user, day: date, appointment) -> dict:
    """ทุกค่ามาจากฐานข้อมูล ไม่มีค่าตั้งต้นแต่งขึ้น"""
    from intelligence.models import AgenticArtifact

    last_visit = patient.histories.select_related('doctor').order_by('-visit_date').first()
    visit_count = patient.histories.count()

    line_boxes = list(
        Box.objects.filter(patient=patient, source=Box.Source.LINE, status__in=[Box.Status.DRAFT, Box.Status.DONE])
        .order_by('-last_activity_at')[:3]
    )
    for box in line_boxes:
        contents = box.contents or {}
        box.red_flag = bool(contents.get('red_flag'))
        box.has_symptoms = bool(contents.get('has_symptoms'))
        box.message_count = len(contents.get('messages', []))

    record = patient.biological_records.order_by('-record_date').first()
    abnormal_axes = []
    if record:
        abnormal_axes = [{'id': ax['axis_id'], 'name': CANONICAL_39_AXES.get(ax['axis_id'], f"Axis {ax['axis_id']}"),
                          'score': ax['score']}
                         for ax in record.get_dysfunctional_axes(threshold=AXIS_THRESHOLD)[:6]]

    next_appt = (Appointment.objects.filter(patient=patient, appointment_date__gt=day)
                 .exclude(status='cancelled').select_related('doctor').order_by('appointment_date', 'appointment_time').first())

    return {
        'allergies': (patient.allergies or '').strip(),
        'chief_complaint': (patient.chief_complaint or '').strip(),
        'medical_history': (patient.medical_history or '').strip(),
        'current_medications': (getattr(patient, 'current_medications', '') or '').strip(),
        'last_visit': last_visit,
        'visit_count': visit_count,
        'line_boxes': line_boxes,
        'record': record,
        'abnormal_axes': abnormal_axes,
        'pending_labs': AgenticArtifact.objects.filter(patient=patient, artifact_type='lab_extraction', status='pending').count(),
        'own_draft': services_visit.own_draft(patient, user),
        'next_appt': next_appt,
        'next_appt_label': thai_long_date(next_appt.appointment_date) if next_appt else '',
    }


@clinical_staff_required
def previsit_view(request: HttpRequest):
    today = timezone.localdate()
    day = _day_from(request, today)
    mine = request.GET.get('mine') == '1' and request.user.role == User.Role.DOCTOR

    appointment = None
    patient = None
    appt_id = request.GET.get('appointment_id', '')
    if appt_id.isdigit():
        appointment = Appointment.objects.select_related('patient', 'doctor').filter(pk=int(appt_id)).first()
        patient = appointment.patient if appointment else None
        if appointment and 'date' not in request.GET:  # มาจากปฏิทิน: แสดงคิวของวันนัดนั้น
            day = appointment.appointment_date

    queue_qs = Appointment.objects.filter(appointment_date=day).select_related('patient', 'doctor')
    if mine:
        queue_qs = queue_qs.filter(doctor=request.user)
    # ยกเลิกไว้ท้ายสุด ที่เหลือเรียงตามเวลา
    queue = list(queue_qs.annotate(
        cancelled_last=Case(When(status='cancelled', then=Value(1)), default=Value(0), output_field=IntegerField()),
    ).order_by('cancelled_last', 'appointment_time'))

    patient_id = request.GET.get('patient_id', '')
    if patient is None and patient_id.isdigit():
        patient = Patient.objects.filter(pk=int(patient_id)).first()
        if patient:  # walk-in ที่บังเอิญมีนัดวันนี้ด้วย
            appointment = next((a for a in queue if a.patient_id == patient.pk and a.status != 'cancelled'), None)
    if patient is None:
        appointment = next((a for a in queue if a.status in ('scheduled', 'confirmed')), None) or (queue[0] if queue else None)
        patient = appointment.patient if appointment else None

    counts = {key: sum(1 for a in queue if a.status == key) for key in STATUS_SHORT}
    return render(request, 'patients/doctor_pre_visit.html', {
        'day': day,
        'day_label': thai_long_date(day),
        'is_today': day == today,
        'prev_day': (day - timedelta(days=1)).isoformat(),
        'next_day': (day + timedelta(days=1)).isoformat(),
        'today': today.isoformat(),
        'mine': mine,
        'is_doctor': request.user.role == User.Role.DOCTOR,
        'queue': queue,
        'counts': counts,
        'waiting': counts['scheduled'] + counts['confirmed'],
        'status_short': STATUS_SHORT,
        'appointment': appointment,
        'appointment_day_label': thai_long_date(appointment.appointment_date) if appointment else '',
        'patient': patient,
        'brief': _briefing(patient, request.user, day, appointment) if patient else None,
        'axis_threshold': AXIS_THRESHOLD,
    })


@require_POST
@clinical_staff_required
def previsit_start_view(request: HttpRequest, appointment_id: int):
    """เริ่มตรวจ: นัดวันนี้ -> มาตรวจแล้ว แล้วเปิดฟอร์มบันทึกการตรวจในแฟ้มคนไข้"""
    appt = get_object_or_404(Appointment.objects.select_related('patient'), pk=appointment_id)
    if appt.status == 'cancelled':
        messages.error(request, 'นัดนี้ถูกยกเลิกแล้ว ถ้าคนไข้มาตรวจ ให้เปลี่ยนสถานะนัดในปฏิทินก่อน')
        return redirect(f"{reverse('patients:doctor_pre_visit')}?date={appt.appointment_date.isoformat()}&appointment_id={appt.pk}")
    if appt.appointment_date != timezone.localdate():
        messages.error(request, 'เริ่มตรวจได้เฉพาะนัดของวันนี้')
        return redirect(f"{reverse('patients:doctor_pre_visit')}?date={appt.appointment_date.isoformat()}&appointment_id={appt.pk}")
    if appt.status != 'completed':
        old = appt.status
        appt.status = 'completed'
        appt.save(update_fields=['status'])
        AuditLog.objects.create(
            user=request.user, action='APPOINTMENT_STATUS_CHANGED', model='Appointment', object_id=str(appt.pk),
            changes={'from': old, 'to': 'completed', 'patient_hn': appt.patient.hn, 'via': 'pre_visit_start'},
            client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
    return redirect(f"{reverse('patients:patient_detail', args=[appt.patient_id])}?visit=1#new-soap")
