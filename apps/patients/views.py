"""
Views for Doctor Portal & EMR Management (Pillars 2, 5, 8).
Enforces HTMX Live Search, SOAP Note Logging, and Full AuditLog.
"""

from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from accounts.decorators import clinical_staff_required
from accounts.models import AuditLog
from accounts.views import get_client_ip
from patients.models import Patient, PatientHistory, Appointment
from patients.forms import PatientForm, PatientHistorySOAPForm

@clinical_staff_required
def doctor_dashboard(request):
    """
    หน้าหลัก Dashboard สถิติคลินิกสำหรับแพทย์และบุคลากรทางการแพทย์
    """
    total_patients = Patient.objects.count()
    urgent_cases = Patient.objects.filter(status='urgent').count()
    today = date.today()
    today_appointments = Appointment.objects.filter(appointment_date=today).count()
    
    # ดึงคนไข้ล่าสุด 5 รายการ (Pillar 5: ป้องกัน N+1)
    recent_patients = Patient.objects.all().order_by('-created_at')[:5]

    return render(request, 'patients/dashboard.html', {
        'doctor': request.user,
        'total_patients': total_patients,
        'urgent_cases': urgent_cases,
        'today_appointments': today_appointments,
        'recent_patients': recent_patients,
    })


@clinical_staff_required
def patient_list_view(request):
    """
    ตารางรายชื่อคนไข้ (Patient Roster)
    รองรับ HTMX Live Search (ค้นหาแบบพิมพ์ปุ๊บ ผลลัพธ์อัปเดตทันทีโดยไม่ต้องโหลดใหม่)
    """
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    # Base Queryset
    queryset = Patient.objects.all()

    # Search Filter
    if search_query:
        queryset = queryset.filter(
            Q(hn__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    # Status Filter
    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    patients = queryset.order_by('-created_at')[:50]

    context = {
        'patients': patients,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': queryset.count(),
    }

    # ⚠️ HTMX Response: ถ้าส่งมาจาก HTMX ให้ส่งเฉพาะ Partial HTML ของตาราง
    if request.headers.get('HX-Request'):
        return render(request, 'patients/partials/patient_table_rows.html', context)

    return render(request, 'patients/patient_list.html', context)


@clinical_staff_required
def patient_detail_view(request, patient_id):
    """
    แฟ้มเวชระเบียนผู้ป่วยรายบุคคล (Comprehensive Patient EMR)
    """
    # ⚠️ Pillar 5: ใช้ prefetch_related โหลดประวัติการรักษาและแพทย์ผู้บันทึกใน Query เดียว ป้องกัน N+1
    patient = get_object_or_404(
        Patient.objects.prefetch_related('histories__doctor'),
        pk=patient_id
    )

    # บันทึก AuditLog ทุกครั้งที่มีการเปิดแฟ้มเวชระเบียน (PDPA Sensitive Access Tracking)
    AuditLog.objects.create(
        user=request.user,
        action="EMR_PATIENT_VIEW",
        model="Patient",
        object_id=str(patient.pk),
        changes={"hn": patient.hn, "name": patient.full_name},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    soap_form = PatientHistorySOAPForm()
    histories = patient.histories.all()

    return render(request, 'patients/patient_detail.html', {
        'patient': patient,
        'histories': histories,
        'soap_form': soap_form,
    })


@clinical_staff_required
@require_http_methods(["GET", "POST"])
def patient_create_view(request):
    """
    ลงทะเบียนคนไข้ใหม่โดยบุคลากรทางการแพทย์
    """
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            
            # บันทึก AuditLog
            AuditLog.objects.create(
                user=request.user,
                action="PATIENT_EMR_CREATED",
                model="Patient",
                object_id=str(patient.pk),
                changes={"hn": patient.hn, "name": patient.full_name},
                client_ip=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )

            messages.success(request, f"สร้างแฟ้มเวชระเบียนสำหรับ {patient.full_name} (HN: {patient.hn}) สำเร็จ")
            return redirect('patients:patient_detail', patient_id=patient.pk)
    else:
        # สุ่มตัวเลข HN เริ่มต้นให้สะดวก
        form = PatientForm()

    return render(request, 'patients/patient_form.html', {'form': form, 'title': 'เพิ่มคนไข้ใหม่เข้าสู่ระบบ'})


@clinical_staff_required
@require_http_methods(["GET", "POST"])
def patient_edit_view(request, patient_id):
    """
    แก้ไขข้อมูลเวชระเบียนคนไข้
    """
    patient = get_object_or_404(Patient, pk=patient_id)

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            patient = form.save()

            AuditLog.objects.create(
                user=request.user,
                action="PATIENT_EMR_UPDATED",
                model="Patient",
                object_id=str(patient.pk),
                changes={"hn": patient.hn},
                client_ip=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )

            messages.success(request, "อัปเดตข้อมูลเวชระเบียนเรียบร้อยแล้ว")
            return redirect('patients:patient_detail', patient_id=patient.pk)
    else:
        form = PatientForm(instance=patient)

    return render(request, 'patients/patient_form.html', {
        'form': form,
        'patient': patient,
        'title': f'แก้ไขเวชระเบียน: {patient.full_name}'
    })


@clinical_staff_required
@require_http_methods(["POST"])
def patient_add_soap_view(request, patient_id):
    """
    เพิ่มบันทึกการตรวจรักษา (SOAP Note) ใหม่เข้าสู่เวชระเบียน
    รองรับ HTMX Seamless Append
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    form = PatientHistorySOAPForm(request.POST)

    if form.is_valid():
        history = form.save(commit=False)
        history.patient = patient
        history.doctor = request.user
        history.save()

        # บันทึก AuditLog
        AuditLog.objects.create(
            user=request.user,
            action="SOAP_NOTE_RECORDED",
            model="PatientHistory",
            object_id=str(history.pk),
            changes={"patient_hn": patient.hn},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )

        messages.success(request, "บันทึกการตรวจรักษา (SOAP Note) สำเร็จ")

        # ⚠️ หากส่งมาจาก HTMX ให้ส่ง Partial Note กลับไปแทรกในหน้าจอทันที
        if request.headers.get('HX-Request'):
            return render(request, 'patients/partials/history_soap_card.html', {'history': history})

    return redirect('patients:patient_detail', patient_id=patient.pk)
