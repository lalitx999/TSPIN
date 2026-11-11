"""
ปฏิทินนัดหมาย (/doctor/appointments/)

หน้าเดียวแสดงทั้งเดือน: กดวันไหนก็เลื่อนลงไปดูรายชื่อนัดของวันนั้นทันที (ข้อมูลทั้งเดือนส่งมากับหน้า ไม่ต้องโหลดใหม่)
สร้างนัด / เปลี่ยนสถานะ / ดูเวลาที่ไม่ว่าง เรียกผ่าน fetch ตอบเป็น JSON
"""

import calendar
from datetime import date, time, timedelta

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import clinical_staff_required
from accounts.models import AuditLog, User
from accounts.views import get_client_ip
from patients.forms import AppointmentForm
from patients.models import Appointment

THAI_MONTHS = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
               'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
STATUS_SHORT = {'scheduled': 'รอยืนยัน', 'confirmed': 'ยืนยันแล้ว', 'completed': 'มาตรวจแล้ว', 'cancelled': 'ยกเลิก'}
# ช่วงเวลาให้เลือกเร็วในฟอร์ม (คลินิกเปิด 09:00–18:00) เลือกเวลาอื่นเองได้
SLOT_TIMES = [time(h, m) for h in range(9, 18) for m in (0, 30)]


def _doctor_name(user) -> str:
    if not user:
        return 'ยังไม่ระบุแพทย์'
    return user.get_full_name() or user.username


def _month_from(request: HttpRequest, today: date) -> date:
    raw = request.GET.get('month', '')
    try:
        year, month = (int(x) for x in raw.split('-')[:2])
        return date(year, month, 1)
    except (ValueError, TypeError):
        return today.replace(day=1)


def _serialize(appt: Appointment) -> dict:
    return {
        'id': appt.pk,
        'date': appt.appointment_date.isoformat(),
        'time': appt.appointment_time.strftime('%H:%M'),
        'status': appt.status,
        'status_label': STATUS_SHORT.get(appt.status, appt.status),
        'notes': appt.notes,
        'patient': {'id': appt.patient_id, 'name': appt.patient.full_name, 'hn': appt.patient.hn,
                    'initial': appt.patient.first_name[:1], 'phone': appt.patient.phone or ''},
        'doctor': _doctor_name(appt.doctor),
        'doctor_id': appt.doctor_id,
        'urls': {
            'patient': reverse('patients:patient_detail', args=[appt.patient_id]),
            'previsit': f"{reverse('patients:doctor_pre_visit')}?patient_id={appt.patient_id}&appointment_id={appt.pk}",
            'status': reverse('patients:appointment_status', args=[appt.pk]),
        },
    }


@clinical_staff_required
def appointments_calendar_view(request: HttpRequest):
    today = timezone.localdate()
    first = _month_from(request, today)
    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(first.year, first.month)  # เริ่มวันอาทิตย์
    start, end = weeks[0][0], weeks[-1][-1]

    doctors = list(User.objects.filter(role=User.Role.DOCTOR, is_active=True).order_by('first_name', 'username'))
    doctor_filter = request.GET.get('doctor', '')
    qs = Appointment.objects.filter(appointment_date__range=(start, end)).select_related('patient', 'doctor')
    if doctor_filter.isdigit():
        qs = qs.filter(doctor_id=int(doctor_filter))
    appts = [_serialize(a) for a in qs.order_by('appointment_date', 'appointment_time')]

    selected = request.GET.get('day', '')
    try:
        selected_day = date.fromisoformat(selected)
    except ValueError:
        selected_day = today if (today.year, today.month) == (first.year, first.month) else first

    in_month = [a for a in appts if a['date'][:7] == first.isoformat()[:7]]
    stats = {key: sum(1 for a in in_month if a['status'] == key) for key in STATUS_SHORT}
    upcoming = (Appointment.objects.filter(appointment_date__gte=today).exclude(status__in=['cancelled', 'completed'])
                .select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')[:6])

    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    default_doctor = request.user.pk if request.user.role == User.Role.DOCTOR else ''

    return render(request, 'patients/doctor_appointments.html', {
        'calendar_data': {
            'weeks': [[d.isoformat() for d in week] for week in weeks],
            'month': first.isoformat()[:7],
            'today': today.isoformat(),
            'selected': selected_day.isoformat(),
            'appointments': appts,
            'months': THAI_MONTHS,
            'slots': [t.strftime('%H:%M') for t in SLOT_TIMES],
            'default_doctor': default_doctor,
            'urls': {
                'create': reverse('patients:appointment_create'),
                'taken': reverse('patients:appointment_taken'),
                'search': reverse('patients:api_patient_search'),
                'page': reverse('patients:doctor_appointments'),
            },
        },
        'month_title': f"{THAI_MONTHS[first.month - 1]} {first.year + 543}",
        'month_value': first.isoformat()[:7],
        'prev_month': prev_month.isoformat()[:7],
        'next_month': next_month.isoformat()[:7],
        'this_month': today.isoformat()[:7],
        'doctors': [{'id': d.pk, 'name': _doctor_name(d)} for d in doctors],
        'doctor_filter': doctor_filter,
        'stats': stats,
        'month_total': len(in_month),
        'upcoming': upcoming,
        'status_short': STATUS_SHORT,
    })


@require_POST
@clinical_staff_required
def appointment_create_view(request: HttpRequest) -> JsonResponse:
    form = AppointmentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.error_list(), 'fields': list(form.errors)}, status=400)
    data = form.cleaned_data
    appt = Appointment.objects.create(
        patient=form.patient, doctor=form.doctor, appointment_date=data['appointment_date'],
        appointment_time=data['appointment_time'], notes=data.get('notes', '').strip(), status='scheduled',
    )
    AuditLog.objects.create(
        user=request.user, action='APPOINTMENT_CREATED', model='Appointment', object_id=str(appt.pk),
        changes={'patient_hn': form.patient.hn, 'doctor': form.doctor.username,
                 'date': appt.appointment_date.isoformat(), 'time': appt.appointment_time.strftime('%H:%M')},
        client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    return JsonResponse({'ok': True, 'appointment': _serialize(appt)})


@require_POST
@clinical_staff_required
def appointment_status_view(request: HttpRequest, appointment_id: int) -> JsonResponse:
    appt = get_object_or_404(Appointment.objects.select_related('patient', 'doctor'), pk=appointment_id)
    status = request.POST.get('status', '')
    if status not in STATUS_SHORT:
        return JsonResponse({'ok': False, 'error': 'สถานะไม่ถูกต้อง'}, status=400)
    if status == 'completed' and appt.appointment_date > timezone.localdate():
        return JsonResponse({'ok': False, 'error': 'ยังไม่ถึงวันนัด จึงบันทึกว่ามาตรวจแล้วไม่ได้'}, status=400)
    old = appt.status
    appt.status = status
    appt.save(update_fields=['status'])
    AuditLog.objects.create(
        user=request.user, action='APPOINTMENT_STATUS_CHANGED', model='Appointment', object_id=str(appt.pk),
        changes={'from': old, 'to': status, 'patient_hn': appt.patient.hn},
        client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    return JsonResponse({'ok': True, 'appointment': _serialize(appt)})


@require_GET
@clinical_staff_required
def appointment_taken_view(request: HttpRequest) -> JsonResponse:
    """เวลาที่แพทย์คนนั้นมีนัดแล้วในวันที่เลือก (ใช้ปิดปุ่มเวลาในฟอร์ม)"""
    try:
        day = date.fromisoformat(request.GET.get('date', ''))
    except ValueError:
        return JsonResponse({'taken': []})
    qs = Appointment.objects.filter(appointment_date=day).exclude(status='cancelled')
    doctor = request.GET.get('doctor', '')
    patient = request.GET.get('patient', '')
    taken = sorted({a.strftime('%H:%M') for a in qs.filter(doctor_id=doctor).values_list('appointment_time', flat=True)}) \
        if doctor.isdigit() else []
    patient_times = sorted({a.strftime('%H:%M') for a in qs.filter(patient_id=patient).values_list('appointment_time', flat=True)}) \
        if patient.isdigit() else []
    return JsonResponse({'taken': taken, 'patient_times': patient_times})
