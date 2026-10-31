"""
Views for Doctor Portal & EMR Management (Pillars 2, 5, 8).
Enforces HTMX Live Search, SOAP Note Logging, and Full AuditLog.
"""

from datetime import date, datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
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

    queryset = Patient.objects.all()

    from django.core.paginator import Paginator

    if search_query:
        queryset = queryset.filter(
            Q(hn__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    total_count = queryset.count()
    paginator = Paginator(queryset.order_by('-created_at'), 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'patients': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': total_count,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'patients/partials/patient_table_rows.html', context)

    return render(request, 'patients/patient_list.html', context)


@clinical_staff_required
def patient_detail_view(request, patient_id):
    """
    แฟ้มเวชระเบียนผู้ป่วยรายบุคคล (Comprehensive Patient EMR)
    """
    patient = get_object_or_404(
        Patient.objects.prefetch_related('histories__doctor'),
        pk=patient_id
    )

    # บันทึก AuditLog
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
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    form = PatientHistorySOAPForm(request.POST)

    if form.is_valid():
        history = form.save(commit=False)
        history.patient = patient
        history.doctor = request.user
        history.save()

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

        if request.headers.get('HX-Request'):
            return render(request, 'patients/partials/history_soap_card.html', {'history': history})

    return redirect('patients:patient_detail', patient_id=patient.pk)


# =========================================================================
# DOCTOR PORTAL COMPREHENSIVE VIEWS (Prevent all 404s & Full Legacy Parity)
# =========================================================================

@clinical_staff_required
def doctor_pre_visit(request):
    """
    Pre-visit Clinical Briefing & Anamnesis Review (/doctor/pre-visit/)
    สรุปข้อมูลคนไข้ก่อนเข้าพบแพทย์: สัญญาณชีพ อาการสำคัญ ผลแล็บที่ผิดปกติ และแกนชีววิทยาที่ต้องโฟกัส
    """
    patient_id = request.GET.get('patient_id') or request.GET.get('id')
    appointment_id = request.GET.get('appointment_id')
    
    selected_patient = None
    selected_appointment = None

    if appointment_id:
        selected_appointment = Appointment.objects.filter(pk=appointment_id).select_related('patient').first()
        if selected_appointment:
            selected_patient = selected_appointment.patient

    if not selected_patient and patient_id:
        selected_patient = Patient.objects.filter(pk=patient_id).first()

    # ถ้ายังไม่ได้เลือกคนไข้ ให้ดึงคิวตรวจแรกของวันนี้ หรือคนไข้คนล่าสุด
    if not selected_patient:
        selected_patient = Patient.objects.prefetch_related('biological_records').order_by('-updated_at').first()

    waiting_patients = Patient.objects.all().order_by('-created_at')[:10]
    recent_appointments = Appointment.objects.select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')[:10]

    # สรุปข้อมูลชีววิทยา 39 แกนจริงของคนไข้จากฐานข้อมูล (No mockup data!)
    bio_record = selected_patient.biological_records.first() if selected_patient else None
    
    # None = ยังไม่ได้ประเมิน ห้ามเติมคะแนนสมมติ
    score_1 = bio_record.axis_1 if bio_record else None
    score_5 = bio_record.axis_5 if bio_record else None
    score_15 = bio_record.axis_15 if bio_record else None
    score_16 = bio_record.axis_16 if bio_record else None
    score_37 = bio_record.axis_37 if bio_record else None

    def get_status(score):
        if score is None:
            return 'unassessed'
        if score >= 75:
            return 'critical'
        elif score >= 60:
            return 'warning'
        return 'normal'

    focus_axes = [
        {"code": "Axis 1", "name": "Systemic Inflammatory Load", "status": get_status(score_1), "score": score_1, "biomarker": "hsCRP / IL-6 Signaling", "target_module": "KERRA, MINOZA, KS"},
        {"code": "Axis 5", "name": "Glucose–Insulin Regulation", "status": get_status(score_5), "score": score_5, "biomarker": "HOMA-IR / Fasting Blood Sugar", "target_module": "DB1, BOVA, BENJAKUL"},
        {"code": "Axis 15", "name": "Detoxification & Cellular Defense", "status": get_status(score_15), "score": score_15, "biomarker": "Hepatic Phase 1/2 Clearances", "target_module": "HEPA1, HEPA2, LIVITA"},
        {"code": "Axis 16", "name": "Digestive–Absorptive Function", "status": get_status(score_16), "score": score_16, "biomarker": "Gut Barrier & Zonulin Integrity", "target_module": "CINNARA, KURMA, STOMMA"},
        {"code": "Axis 37", "name": "Oncologic & Cellular Defense", "status": get_status(score_37), "score": score_37, "biomarker": "Apoptosis & Cell Cycle Checkpoints", "target_module": "BETA X, MERDANA, RESHIMUNO"},
    ]

    return render(request, 'patients/doctor_pre_visit.html', {
        'patient': selected_patient,
        'appointment': selected_appointment,
        'waiting_patients': waiting_patients,
        'recent_appointments': recent_appointments,
        'focus_axes': focus_axes,
    })


@clinical_staff_required
def doctor_appointments(request):
    """
    ปฏิทินและตารางนัดหมายแพทย์ (/doctor/appointments/)
    """
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        appt_date = request.POST.get('appointment_date')
        appt_time = request.POST.get('appointment_time')
        notes = request.POST.get('notes', '')
        
        if patient_id and appt_date and appt_time:
            patient = get_object_or_404(Patient, pk=patient_id)
            Appointment.objects.create(
                patient=patient,
                doctor=request.user,
                appointment_date=appt_date,
                appointment_time=appt_time,
                notes=notes,
                status='scheduled'
            )
            messages.success(request, f"สร้างนัดหมายสำหรับ {patient.full_name} สำเร็จ")
            return redirect('patients:doctor_appointments')

    appointment_qs = Appointment.objects.select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')
    from django.core.paginator import Paginator
    paginator = Paginator(appointment_qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'patients/doctor_appointments.html', {
        'appointments': page_obj.object_list,
        'page_obj': page_obj,
    })


@clinical_staff_required
def doctor_clinical_review(request):
    """
    ตรวจทานเคสทางคลินิก (/doctor/clinical-review/)
    """
    patients = list(Patient.objects.prefetch_related('biological_records').order_by('-updated_at')[:20])
    for p in patients:
        # แกนหลักมาจากผลประเมินล่าสุดจริงเท่านั้น (ไม่มีผล = ว่าง)
        records = list(p.biological_records.all())
        p.focus_axes = [f"A{ax['axis_id']:02d}" for ax in records[0].get_dysfunctional_axes(threshold=60)[:3]] if records else []
        p.has_assessment = bool(records)
    return render(request, 'patients/doctor_clinical_review.html', {
        'patients': patients,
    })


@clinical_staff_required
def doctor_outcomes(request):
    """
    ติดตามผลลัพธ์การรักษาและไทม์ไลน์การฟื้นฟู (/doctor/outcomes/)
    แสดงเฉพาะผู้ป่วยที่มีผลประเมิน 39 แกนจริง พร้อมจำนวนครั้งที่ประเมินและวันที่ล่าสุด
    """
    from django.db.models import Count, Max, Q
    patients = (
        Patient.objects
        .annotate(
            assessment_count=Count('biological_records', filter=Q(biological_records__is_deleted=False)),
            last_assessed=Max('biological_records__record_date', filter=Q(biological_records__is_deleted=False)),
        )
        .filter(assessment_count__gt=0)
        .order_by('-last_assessed')[:15]
    )
    return render(request, 'patients/doctor_outcomes.html', {
        'patients': patients,
    })


@clinical_staff_required
def doctor_voice_form(request):
    """
    บันทึกเสียงแพทย์แปลงเป็นบันทึก SOAP Note (/doctor/voice-form/)
    """
    patients = Patient.objects.all().order_by('-updated_at')[:10]
    return render(request, 'patients/doctor_voice_form.html', {
        'patients': patients,
    })


@clinical_staff_required
def doctor_axes_mapping(request):
    """
    การแมปตัวชี้วัดแล็บและอาการเข้ากับ 38 แกนชีววิทยา (/doctor/axes-mapping/)
    """
    return render(request, 'patients/doctor_axes_mapping.html')


@clinical_staff_required
def doctor_modules(request):
    """
    ทะเบียนสูตรตำรับโมดูลสมุนไพร 200 โมดูล (/doctor/modules/)
    """
    return render(request, 'patients/doctor_modules.html')


@clinical_staff_required
def doctor_digital_twin(request):
    """
    แบบจำลองสรีรวิทยา Digital Twin 3 มิติ (/doctor/digital-twin/)
    """
    patients = Patient.objects.all().order_by('-updated_at')[:10]
    return render(request, 'patients/doctor_digital_twin.html', {
        'patients': patients,
    })


@clinical_staff_required
def doctor_lab_review(request):
    """
    ตรวจทานผลแล็บที่วิเคราะห์แล้ว (/doctor/lab-review/)
    """
    from intelligence.models import AgenticArtifact

    # ผลแล็บจริงจาก Lab OCR (AgenticArtifact) แตกเป็นแถวละหนึ่งค่า
    lab_rows = []
    artifacts = AgenticArtifact.objects.filter(artifact_type='lab_extraction').select_related('patient').order_by('-created_at')[:30]
    for art in artifacts:
        data = art.proposed_data or {}
        markers = data.get('extracted_biomarkers', data) if isinstance(data, dict) else {}
        for key, m in markers.items():
            if not isinstance(m, dict) or 'value' not in m:
                continue
            is_abnormal = m.get('is_abnormal')
            if is_abnormal is None:
                is_abnormal = str(m.get('status', '')).upper() not in ('', 'NORMAL')
            lab_rows.append({
                'artifact': art,
                'marker': m.get('name') or key,
                'value': m.get('value'),
                'unit': m.get('unit', ''),
                'reference': f"≤ {m['normal_max']}" if m.get('normal_max') is not None else '',
                'is_abnormal': is_abnormal,
            })
    return render(request, 'patients/doctor_lab_review.html', {
        'lab_rows': lab_rows,
    })


@clinical_staff_required
def doctor_knowledge_rag(request):
    """
    สืบค้นองค์ความรู้และงานวิจัยคลินิก RAG (/doctor/knowledge-rag/)
    """
    return render(request, 'patients/doctor_knowledge_rag.html')


@clinical_staff_required
def doctor_tspi_brain(request):
    """
    ระบบแสดงกลไกการคิดและให้เหตุผลของ AI Engine (/doctor/tspi-brain/)
    """
    return render(request, 'patients/doctor_tspi_brain.html')


@clinical_staff_required
def doctor_chats(request):
    """
    ห้องแชทสื่อสารระหว่างแพทย์กับคนไข้ผ่าน LINE OA (/doctor/chats/)
    """
    patients = Patient.objects.all().order_by('-updated_at')[:10]
    return render(request, 'patients/doctor_chats.html', {
        'patients': patients,
    })


@clinical_staff_required
def doctor_audit(request):
    """
    บันทึกการเข้าถึงและประวัติการตรวจสอบตามมาตรฐาน PDPA (/doctor/audit/)
    """
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:50]
    return render(request, 'patients/doctor_audit.html', {
        'logs': logs,
    })


@clinical_staff_required
def doctor_settings(request):
    """
    ตั้งค่าบัญชีแพทย์ ลายเซ็นดิจิทัล และข้อมูลคลินิก (/doctor/settings/)
    รองรับการตั้ง/เปลี่ยนรหัสเปิดกล่องส่วนตัว (ต้องยืนยันด้วยรหัสผ่านเข้าสู่ระบบ)
    """
    if request.method == 'POST' and request.POST.get('action') == 'set_box_password':
        new_pw = request.POST.get('box_password', '')
        if not request.user.check_password(request.POST.get('current_password', '')):
            messages.error(request, "รหัสผ่านเข้าสู่ระบบไม่ถูกต้อง")
        elif len(new_pw) < 8:
            messages.error(request, "รหัสเปิดกล่องต้องมีอย่างน้อย 8 ตัวอักษร")
        elif new_pw != request.POST.get('box_password_confirm', ''):
            messages.error(request, "รหัสเปิดกล่องทั้งสองช่องไม่ตรงกัน")
        elif request.user.check_password(new_pw):
            messages.error(request, "รหัสเปิดกล่องต้องไม่ซ้ำกับรหัสผ่านเข้าสู่ระบบ")
        else:
            request.user.set_box_password(new_pw)
            AuditLog.objects.create(
                user=request.user, action='BOX_PASSWORD_SET', model='User', object_id=str(request.user.pk),
                client_ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            messages.success(request, "บันทึกรหัสเปิดกล่องเรียบร้อยแล้ว")
        return redirect('patients:doctor_settings')

    ai_usage = None
    if request.user.is_superuser or request.user.role == 'admin':
        from intelligence.ai_budget import monthly_summary
        ai_usage = monthly_summary()
    return render(request, 'patients/doctor_settings.html', {'ai_usage': ai_usage})


@clinical_staff_required
def api_patient_search(request):
    """
    API ค้นหาคนไข้แบบ Real-time AJAX Autocomplete (Pillar 5 Performance)
    รองรับค้นหาด้วยชื่อ, นามสกุล, HN หรือเบอร์โทรศัพท์ คืนผลลัพธ์ทันที
    """
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'patients': []})
    
    patients = Patient.objects.filter(
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q) |
        Q(hn__icontains=q) |
        Q(phone__icontains=q)
    ).order_by('-created_at')[:15]
    
    data = [{
        'id': p.id,
        'hn': p.hn,
        'full_name': p.full_name,
        'first_name': p.first_name,
        'last_name': p.last_name,
        'age': p.age,
        'gender': p.get_gender_display(),
        'phone': p.phone or '-',
    } for p in patients]
    
    return JsonResponse({'results': data, 'patients': data})
