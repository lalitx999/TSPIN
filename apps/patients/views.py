"""
Views for Doctor Portal & EMR Management (Pillars 2, 5, 8).
Enforces HTMX Live Search, SOAP Note Logging, and Full AuditLog.
"""

from datetime import date, datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Case, IntegerField, Q, Value, When
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
from accounts.decorators import clinical_staff_required
from accounts.models import AuditLog
from accounts.views import get_client_ip
from clinical import services_intake
from clinical.models import Box
from clinical.views_intake import INTAKE_SOURCES
from patients.line_links import pending_link_requests
from patients.models_line import CommunicationRecord
from patients.models import Patient, PatientHistory, Appointment
from patients.forms import PatientForm, PatientHistorySOAPForm, VisitVitalsForm


@clinical_staff_required
def doctor_dashboard(request):
    """
    หน้าหลัก Dashboard สถิติคลินิกสำหรับแพทย์และบุคลากรทางการแพทย์
    """
    total_patients = Patient.objects.count()
    urgent_cases = Patient.objects.filter(status='urgent').count()
    today = date.today()
    today_appointments = Appointment.objects.filter(appointment_date=today).exclude(status='cancelled').count()
    
    # ดึงคนไข้ล่าสุด 5 รายการ (Pillar 5: ป้องกัน N+1)
    recent_patients = Patient.objects.all().order_by('-created_at')[:5]

    return render(request, 'patients/dashboard.html', {
        'doctor': request.user,
        'total_patients': total_patients,
        'urgent_cases': urgent_cases,
        'today_appointments': today_appointments,
        'recent_patients': recent_patients,
        **_line_cases_context(),
    })


def _line_cases_context() -> dict:
    """รอบแชทที่มีเรื่องอาการและจบแล้ว รวมเคสฉุกเฉินที่ยังคุยอยู่ ไม่งั้นหมอจะไม่เห็นจนกว่าบอทจะปิด"""
    services_intake.close_idle_line_sessions()
    pending = Box.objects.filter(
        (Q(status=Box.Status.DONE) & services_intake.needs_doctor_q()) | Q(status=Box.Status.DRAFT, contents__red_flag=True),
        source__in=INTAKE_SOURCES, patient__isnull=False,
    )
    cases = (
        pending.select_related('patient')
        .annotate(urgent_first=Case(When(contents__red_flag=True, then=Value(0)), default=Value(1), output_field=IntegerField()))
        .order_by('urgent_first', '-last_activity_at')[:5]
    )
    unregistered_emergencies = list(
        CommunicationRecord.objects.filter(raw_payload__emergency_alert=True, patient__isnull=True,
                                           created_at__gte=timezone.now() - timedelta(hours=24))
        .select_related('line_user').order_by('-created_at')[:5]
    )
    return {
        'cases': cases,
        'unregistered_emergencies': unregistered_emergencies,
        'waiting_count': pending.count(),
        'urgent_count': pending.filter(contents__red_flag=True).count() + len(unregistered_emergencies),
        'link_request_count': pending_link_requests().count(),
    }


@clinical_staff_required
def doctor_line_cases(request):
    return render(request, 'patients/partials/line_cases.html', _line_cases_context())


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

    histories = patient.histories.all()

    # ร่างซักประวัติของผู้ใช้คนนี้ (ถ้ามี) ให้ฟอร์มกลับมาทำต่อได้ ร่างของคนอื่นแสดงแค่ว่ามีอยู่
    from clinical import services_visit
    draft = services_visit.own_draft(patient, request.user)
    visit_state = {'box_id': None, 'history_text': '', 'vitals': {}, 'soap': {}, 'soap_source': 'none', 'images': []}
    if draft:
        request.session[f"box_unlocked_{draft.id}"] = True
        contents = draft.contents or {}
        visit_state = {
            'box_id': str(draft.id),
            'history_text': contents.get('history_text', ''),
            'vitals': contents.get('vitals_input', {}),
            'soap': contents.get('soap_edit') or contents.get('soap') or {},
            'soap_source': contents.get('soap_source', 'none'),
            'images': [{'media_id': m['media']['media_id'],
                        'url': reverse('clinical:intake_media', kwargs={'box_id': draft.id, 'media_id': m['media']['media_id']})}
                       for m in services_visit.images(draft)],
        }

    # ดึงผลแล็บล่าสุดของคนไข้
    from intelligence.models import AgenticArtifact
    latest_lab_art = AgenticArtifact.objects.filter(
        patient=patient,
        artifact_type='lab_extraction'
    ).order_by('-created_at').first()

    patient_labs = []
    latest_lab_date = None
    if latest_lab_art and isinstance(latest_lab_art.proposed_data, dict):
        latest_lab_date = latest_lab_art.created_at
        markers = latest_lab_art.proposed_data.get('extracted_biomarkers', latest_lab_art.proposed_data)
        if isinstance(markers, dict):
            for k, m in markers.items():
                if isinstance(m, dict) and 'value' in m:
                    patient_labs.append({
                        'code': k,
                        'name': m.get('name') or k,
                        'value': m.get('value'),
                        'unit': m.get('unit', ''),
                        'is_abnormal': bool(m.get('is_abnormal')),
                        'target_axis': m.get('target_axis', ''),
                    })
    elif patient.extra_data and isinstance(patient.extra_data.get('biomarkers'), dict):
        markers = patient.extra_data['biomarkers']
        for k, m in markers.items():
            if isinstance(m, dict) and 'value' in m:
                patient_labs.append({
                    'code': k,
                    'name': m.get('name') or k,
                    'value': m.get('value'),
                    'unit': m.get('unit', ''),
                    'is_abnormal': bool(m.get('is_abnormal')),
                    'target_axis': m.get('target_axis', ''),
                })

    abnormal_axes_from_labs = []
    for l in patient_labs:
        if l.get('is_abnormal') and l.get('target_axis'):
            ax_name = l['target_axis']
            if ax_name not in abnormal_axes_from_labs:
                abnormal_axes_from_labs.append(ax_name)

    lab_documents = []
    if isinstance(patient.extra_data, dict):
        lab_documents = patient.extra_data.get('lab_documents') or []

    return render(request, 'patients/patient_detail.html', {
        'patient': patient,
        'histories': histories,
        'visit_state': visit_state,
        'visit_ranges': VisitVitalsForm.RANGES,
        'open_visit': bool(draft) or request.GET.get('visit') == '1',
        'other_drafts': services_visit.drafts_for(patient).exclude(opened_by=request.user),
        'patient_labs': patient_labs,
        'latest_lab_date': latest_lab_date,
        'abnormal_axes_from_labs': abnormal_axes_from_labs,
        'lab_documents': lab_documents,
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
    แสดงผู้ป่วยที่มีผลประเมิน 39 แกนจริง พร้อมระบบค้นหาคนไข้และกรองสถานะ
    """
    from django.db.models import Count, Max, Q
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all').strip()
    include_all = request.GET.get('include_all', '0').strip() == '1'

    qs = Patient.objects.annotate(
        assessment_count=Count('biological_records', filter=Q(biological_records__is_deleted=False)),
        last_assessed=Max('biological_records__record_date', filter=Q(biological_records__is_deleted=False)),
    )

    if not include_all:
        qs = qs.filter(assessment_count__gt=0)

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(hn__icontains=q) |
            Q(phone__icontains=q)
        )

    if status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)

    patients = qs.order_by('-last_assessed', '-updated_at')[:50]
    total_active_count = Patient.objects.annotate(c=Count('biological_records')).filter(c__gt=0).count()

    return render(request, 'patients/doctor_outcomes.html', {
        'patients': patients,
        'search_q': q,
        'status_filter': status_filter,
        'include_all': include_all,
        'total_active_count': total_active_count,
    })


@clinical_staff_required
def doctor_voice_form(request):
    """
    ระบบบันทึกเสียงแปลงเป็น SOAP Note ปัจจุบันผสานรวมอยู่ในฟอร์มตรวจคนไข้ (EMR Visit Form) แล้ว
    ทำ Redirect ไปยังหน้าแฟ้มคนไข้โดยอัตโนมัติ
    """
    patient_id = request.GET.get('patient_id')
    if patient_id and str(patient_id).isdigit():
        return redirect('patients:patient_detail', patient_id=patient_id)
    return redirect('patients:patient_list')


@clinical_staff_required
def doctor_axes_mapping(request):
    """
    การแมปตัวชี้วัดแล็บและอาการเข้ากับ 39 แกนชีววิทยา (/doctor/axes-mapping/)
    """
    patient_id = request.GET.get('patient_id')
    patient = None
    patient_labs = []

    if patient_id and str(patient_id).isdigit():
        patient = Patient.objects.filter(pk=patient_id).first()
        if patient:
            from intelligence.models import AgenticArtifact
            lab_art = AgenticArtifact.objects.filter(
                patient=patient,
                artifact_type='lab_extraction'
            ).order_by('-created_at').first()
            if lab_art and isinstance(lab_art.proposed_data, dict):
                data = lab_art.proposed_data
                markers = data.get('extracted_biomarkers', data) if isinstance(data, dict) else {}
                for key, m in markers.items():
                    if isinstance(m, dict) and 'value' in m:
                        patient_labs.append({
                            'code': key,
                            'name': m.get('name') or key,
                            'value': m.get('value'),
                            'unit': m.get('unit', ''),
                            'is_abnormal': bool(m.get('is_abnormal', False)),
                            'target_axis': m.get('target_axis', ''),
                        })
            elif patient.extra_data and isinstance(patient.extra_data.get('biomarkers'), dict):
                markers = patient.extra_data['biomarkers']
                for key, m in markers.items():
                    if isinstance(m, dict) and 'value' in m:
                        patient_labs.append({
                            'code': key,
                            'name': m.get('name') or key,
                            'value': m.get('value'),
                            'unit': m.get('unit', ''),
                            'is_abnormal': bool(m.get('is_abnormal', False)),
                            'target_axis': m.get('target_axis', ''),
                        })

    recent_patients = Patient.objects.order_by('-updated_at')[:6]

    import json
    return render(request, 'patients/doctor_axes_mapping.html', {
        'patient': patient,
        'patient_labs': patient_labs,
        'patient_labs_json': json.dumps(patient_labs, ensure_ascii=False),
        'recent_patients': recent_patients,
    })


@clinical_staff_required
def doctor_modules(request):
    """
    ทะเบียนสูตรตำรับโมดูลสมุนไพร 200 โมดูล (/doctor/modules/)
    """
    from clinical.engine import TspiClinicalEngine
    all_modules = TspiClinicalEngine.get_modules_data()
    q = request.GET.get('q', '').strip().lower()
    
    modules = all_modules
    if q:
        modules = [
            m for m in all_modules
            if q in str(m.get('code') or '').lower()
            or q in str(m.get('name') or '').lower()
            or q in str(m.get('botanical') or '').lower()
            or q in str(m.get('description') or '').lower()
            or q in str(m.get('axis_mapping') or '').lower()
        ]
    
    return render(request, 'patients/doctor_modules.html', {
        'modules': modules[:60],
        'total_count': len(modules),
        'all_count': len(all_modules),
        'search_q': q,
    })


@clinical_staff_required
def doctor_digital_twin(request):
    """
    แบบจำลอง Digital Twin สรีรวิทยาบุคคล (/doctor/digital-twin/)
    วิเคราะห์และจำลอง 8 ระบบอวัยวะมนุษย์จากคะแนน 39 แกนชีววิทยา และผลแล็บระดับโมเลกุล
    """
    patient_id = request.GET.get('patient_id')
    patient = None
    if patient_id and str(patient_id).isdigit():
        patient = Patient.objects.filter(pk=patient_id).first()
    
    if not patient:
        patient = Patient.objects.filter(biological_records__isnull=False).order_by('-updated_at').first() or Patient.objects.order_by('-updated_at').first()

    latest_record = None
    scores_dict = {}
    if patient:
        latest_record = patient.biological_records.order_by('-record_date').first()
        if latest_record:
            scores_dict = {k: (v if v is not None else 50) for k, v in latest_record.to_scores_dict().items()}
        else:
            scores_dict = {i: 50 for i in range(1, 40)}

    from clinical.invariants import CANONICAL_39_AXES
    from intelligence.models import AgenticArtifact
    
    patient_labs = []
    if patient:
        lab_art = AgenticArtifact.objects.filter(
            patient=patient,
            artifact_type='lab_extraction'
        ).order_by('-created_at').first()
        if lab_art and isinstance(lab_art.proposed_data, dict):
            markers = lab_art.proposed_data.get('extracted_biomarkers', lab_art.proposed_data)
            if isinstance(markers, dict):
                for k, m in markers.items():
                    if isinstance(m, dict) and 'value' in m:
                        patient_labs.append({
                            'code': k,
                            'name': m.get('name') or k,
                            'value': m.get('value'),
                            'unit': m.get('unit', ''),
                            'is_abnormal': bool(m.get('is_abnormal')),
                            'target_axis': m.get('target_axis', '')
                        })
        elif patient.extra_data and isinstance(patient.extra_data.get('biomarkers'), dict):
            markers = patient.extra_data['biomarkers']
            for k, m in markers.items():
                if isinstance(m, dict) and 'value' in m:
                    patient_labs.append({
                        'code': k,
                        'name': m.get('name') or k,
                        'value': m.get('value'),
                        'unit': m.get('unit', ''),
                        'is_abnormal': bool(m.get('is_abnormal')),
                        'target_axis': m.get('target_axis', '')
                    })

    SYSTEMS_CONFIG = [
        {
            'id': 'brain',
            'name_th': 'สมองและระบบประสาท',
            'name_en': 'Brain & Neuro-Axis',
            'icon': 'fas fa-brain',
            'axes_ids': [34, 35, 36, 37],
            'description': 'การควบคุมสารสื่อประสาท, วงจรการนอนหลับ, Vagal Tone, และแผงกั้นเลือด-สมอง',
            'matched_modules': ['TSPI-NEURO-CALM-01', 'TSPI-CIRCADIAN-ZEN-04'],
        },
        {
            'id': 'cardiovascular',
            'name_th': 'หัวใจและหลอดเลือด',
            'name_en': 'Cardio-Vascular Network',
            'icon': 'fas fa-heart-pulse',
            'axes_ids': [20, 21, 22, 23],
            'description': 'การทำงานของเซลล์เยื่อบุหลอดเลือด (Endothelium), ความยืดหยุ่นของหลอดเลือดแดง, และการไหลเวียนโลหิตฝอย',
            'matched_modules': ['TSPI-VASCO-FLOW-02', 'TSPI-NITRIC-PLUS-06'],
        },
        {
            'id': 'liver_detox',
            'name_th': 'ตับและการขจัดสารพิษ',
            'name_en': 'Hepatic & Detoxification',
            'icon': 'fas fa-flask-vial',
            'axes_ids': [11, 15, 38],
            'description': 'กระบวนการขับสารพิษของตับ Phase I & II, ภาวะตับคั่งไขมัน (MASH), และการขับของเสียออกทางไต',
            'matched_modules': ['TSPI-CURCUMA-01 (Detox)', 'TSPI-HEPATIC-CLEAR-03'],
        },
        {
            'id': 'gut_ecosystem',
            'name_th': 'ลำไส้และไมโครไบโอม',
            'name_en': 'Gut Ecosystem & Barrier',
            'icon': 'fas fa-utensils',
            'axes_ids': [16, 17, 18, 19],
            'description': 'ความสมบูรณ์ของเยื่อบุลำไส้ (Intestinal Permeability / Zonulin), ความหลากหลายของจุลชีพ, และแกนลำไส้-ภูมิคุ้มกัน',
            'matched_modules': ['TSPI-ABSORN-03 (Gut Barrier)', 'TSPI-SYNBIOTIC-12'],
        },
        {
            'id': 'metabolic_endocrine',
            'name_th': 'ต่อมไร้ท่อและพลังงาน',
            'name_en': 'Metabolic & Endocrine Core',
            'icon': 'fas fa-fire-flame-curved',
            'axes_ids': [5, 6, 7, 31, 32, 33],
            'description': 'การควบคุมกลูโคส-อินซูลิน (HOMA-IR), ภาวะเป็นพิษจากไขมัน, ต่อมไทรอยด์, และแกนความเครียด HPA (Cortisol)',
            'matched_modules': ['TSPI-GLUCO-SHIELD-05', 'TSPI-ADRENAL-SUPPORT-08'],
        },
        {
            'id': 'immune_shield',
            'name_th': 'ภูมิคุ้มกันและการอักเสบ',
            'name_en': 'Immune Shield & Inflammation',
            'icon': 'fas fa-shield-virus',
            'axes_ids': [1, 2, 3, 4, 39],
            'description': 'ภาวะอักเสบระดับระบบ (Systemic Inflammation / hsCRP), ภูมิคุ้มกันชราภาพ, และระบบเฝ้าระวังภูมิคุ้มกันโมเลกุล',
            'matched_modules': ['TSPI-INFLAM-OFF-01', 'TSPI-IMMUNO-REGEN-07'],
        },
        {
            'id': 'cellular_mitochondria',
            'name_th': 'ไมโทคอนเดรียและเซลล์',
            'name_en': 'Mitochondria & Longevity',
            'icon': 'fas fa-dna',
            'axes_ids': [8, 9, 10, 14],
            'description': 'การผลิตพลังงาน ATP, ภาวะ Oxidative Stress (8-OHdG), การซ่อมแซมดีเอ็นเอ, และเซลล์ชราภาพ (SASP)',
            'matched_modules': ['TSPI-MITO-POWER-09', 'TSPI-LONGEVITY-NAD-11'],
        },
        {
            'id': 'musculoskeletal',
            'name_th': 'กล้ามเนื้อ กระดูก และข้อ',
            'name_en': 'Musculoskeletal & Structure',
            'icon': 'fas fa-bone',
            'axes_ids': [26, 28, 29, 30],
            'description': 'มวลและคุณภาพของกล้ามเนื้อ (Sarcopenia), ความหนาแน่นกระดูก, และการฟื้นฟูเนื้อเยื่อเกี่ยวพัน/ข้อต่อ',
            'matched_modules': ['TSPI-DERRIS-SCANDENS-04', 'TSPI-OSTEO-MATRIX-10'],
        },
    ]

    organ_systems = []
    total_stress = 0
    for sys in SYSTEMS_CONFIG:
        axis_scores = []
        axes_list = []
        for ax_id in sys['axes_ids']:
            score = scores_dict.get(ax_id, 50)
            axis_scores.append(score)
            axes_list.append({
                'id': ax_id,
                'name': CANONICAL_39_AXES.get(ax_id, f"Axis {ax_id}"),
                'score': score,
            })
        
        avg_score = round(sum(axis_scores) / len(axis_scores)) if axis_scores else 50
        total_stress += avg_score

        triggers = []
        for l in patient_labs:
            if l.get('is_abnormal'):
                code = l.get('code', '').lower()
                name = l.get('name', '').lower()
                if sys['id'] == 'immune_shield' and ('crp' in code or 'crp' in name or 'il6' in code):
                    triggers.append(f"{l['name']}: {l['value']} {l['unit']}")
                elif sys['id'] == 'metabolic_endocrine' and ('insulin' in code or 'homair' in code or 'hba1c' in code or 'cortisol' in code):
                    triggers.append(f"{l['name']}: {l['value']} {l['unit']}")
                elif sys['id'] == 'gut_ecosystem' and ('zonulin' in code or 'calprotectin' in code):
                    triggers.append(f"{l['name']}: {l['value']} {l['unit']}")
                elif sys['id'] == 'liver_detox' and ('alt' in code or 'ast' in code or 'egfr' in code):
                    triggers.append(f"{l['name']}: {l['value']} {l['unit']}")
                elif sys['id'] == 'cellular_mitochondria' and ('ohdg' in code or 'dna' in code):
                    triggers.append(f"{l['name']}: {l['value']} {l['unit']}")
                elif sys['id'] == 'cardiovascular' and ('tghdl' in code or 'endothelin' in code):
                    triggers.append(f"{l['name']}: {l['value']} {l['unit']}")

        if avg_score >= 75:
            tier = 'Critical'
            color = 'danger'
            status_th = 'พยาธิสภาพรุนแรง / วิกฤต (Severe)'
        elif avg_score >= 60:
            tier = 'Warning'
            color = 'warning'
            status_th = 'ความเสื่อมหน้าที่ชัดเจน (Dysfunctional)'
        elif avg_score >= 40:
            tier = 'Attention'
            color = 'primary'
            status_th = 'มีความเครียดระดับเซลล์ (Subclinical)'
        else:
            tier = 'Optimal'
            color = 'success'
            status_th = 'สมบูรณ์ปกติ (Optimal)'

        organ_systems.append({
            'id': sys['id'],
            'name_th': sys['name_th'],
            'name_en': sys['name_en'],
            'icon': sys['icon'],
            'score': avg_score,
            'tier': tier,
            'color': color,
            'status_th': status_th,
            'description': sys['description'],
            'axes': axes_list,
            'lab_triggers': triggers,
            'matched_modules': sys['matched_modules'],
        })

    avg_system_stress = round(total_stress / len(organ_systems)) if organ_systems else 50
    cellular_resilience = max(10, min(95, 100 - avg_system_stress))
    recent_patients = Patient.objects.order_by('-updated_at')[:15]

    import json
    return render(request, 'patients/doctor_digital_twin.html', {
        'patient': patient,
        'recent_patients': recent_patients,
        'latest_record': latest_record,
        'organ_systems': organ_systems,
        'organ_systems_json': json.dumps(organ_systems, ensure_ascii=False),
        'cellular_resilience': cellular_resilience,
        'patient_labs': patient_labs,
    })


@clinical_staff_required
def doctor_lab_review(request):
    """
    ตรวจทานผลแล็บและนำเข้าเอกสารผลตรวจทางห้องปฏิบัติการ (/doctor/lab-review/)
    รองรับการค้นหา กรองสถานะ และอัปโหลดเอกสารผลแล็บหลายไฟล์ผ่าน Modal
    """
    from intelligence.models import AgenticArtifact

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all').strip()
    patient_id_param = request.GET.get('patient_id')
    selected_patient = None
    if patient_id_param and str(patient_id_param).isdigit():
        selected_patient = Patient.objects.filter(pk=patient_id_param, is_deleted=False).first()

    qs = AgenticArtifact.objects.filter(artifact_type='lab_extraction').select_related('patient')
    if status_filter in ('pending', 'approved', 'rejected'):
        qs = qs.filter(status=status_filter)
    if selected_patient:
        qs = qs.filter(patient=selected_patient)
    if q:
        qs = qs.filter(
            Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__hn__icontains=q)
            | Q(title__icontains=q)
        )

    artifacts = qs.order_by('-created_at')[:40]
    lab_rows = []
    for art in artifacts:
        data = art.proposed_data or {}
        docs = data.get('documents', []) if isinstance(data, dict) else []
        markers = data.get('extracted_biomarkers', data) if isinstance(data, dict) else {}
        row_added = False
        if isinstance(markers, dict):
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
                    'documents': docs,
                })
                row_added = True
        if not row_added:
            # แสดงแถวเอกสารแนบแม้ยังไม่พบตัวเลขจาก OCR อัตโนมัติ (เพื่อให้แพทย์เปิดดูไฟล์และตรวจทานได้)
            lab_rows.append({
                'artifact': art,
                'marker': art.title or 'เอกสารผลตรวจแล็บแนบ',
                'value': 'เอกสารแนบ',
                'unit': f"({len(docs)} ไฟล์)" if docs else '',
                'reference': '—',
                'is_abnormal': False,
                'documents': docs,
                'is_document_only': True,
            })

    recent_patients = Patient.objects.filter(is_deleted=False).order_by('-created_at')[:6]
    pending_count = AgenticArtifact.objects.filter(artifact_type='lab_extraction', status='pending').count()

    return render(request, 'patients/doctor_lab_review.html', {
        'lab_rows': lab_rows,
        'q': q,
        'status_filter': status_filter,
        'selected_patient': selected_patient,
        'recent_patients': recent_patients,
        'pending_count': pending_count,
        'open_upload': request.GET.get('open_upload') == '1',
    })


def _commit_lab_artifact_to_emr(artifact, user):
    """นำค่าแล็บที่อนุมัติแล้วบันทึกลงแฟ้ม EMR ของคนไข้ และอัปเดตคะแนน 39 แกนหากมี"""
    from clinical.models import BiologicalRecord
    patient = artifact.patient
    data = artifact.proposed_data if isinstance(artifact.proposed_data, dict) else {}
    markers = data.get('extracted_biomarkers') or {}

    if isinstance(markers, dict) and markers:
        if not isinstance(patient.extra_data, dict):
            patient.extra_data = {}
        existing_bio = patient.extra_data.get('biomarkers')
        if not isinstance(existing_bio, dict):
            existing_bio = {}
        existing_bio.update(markers)
        patient.extra_data['biomarkers'] = existing_bio
        patient.extra_data['latest_lab_date'] = timezone.now().isoformat()
        patient.save(update_fields=['extra_data'])

    affected_scores = data.get('affected_axes_scores') or {}
    if isinstance(affected_scores, dict) and affected_scores:
        record = patient.biological_records.first()
        if not record:
            record = BiologicalRecord.objects.create(patient=patient, doctor=user)
        for ax_id, score in affected_scores.items():
            try:
                ax_num = int(ax_id)
                if 1 <= ax_num <= 39:
                    setattr(record, f'axis_{ax_num}', int(score))
            except (TypeError, ValueError):
                continue
        record.notes = f"อัปเดตผลแล็บจาก Lab Review #{artifact.pk}"
        record.save()


@clinical_staff_required
@require_http_methods(["POST"])
def doctor_lab_intake_action(request):
    """
    รับอัปโหลดเอกสารผลแล็บหลายไฟล์ + ข้อความจาก Modal ในหน้า Lab Review
    - เข้ารหัสไฟล์ต้นฉบับเก็บใน PRIVATE_MEDIA_ROOT และผูกในเวชระเบียน (patient.extra_data['lab_documents'])
    - สกัดค่า Biomarkers ด้วย pypdf/AI Vision + DeterministicLabParser
    - สร้าง AgenticArtifact (และอนุมัติเข้า EMR ทันทีหากเลือก auto_approve)
    """
    import io
    import httpx
    from django.conf import settings
    from clinical import media_store
    from intelligence.models import AgenticArtifact
    from intelligence.services import DeterministicLabParser, ClinicalSafetyChecker

    patient_id = request.POST.get('patient_id')
    if not patient_id or not str(patient_id).isdigit():
        messages.error(request, "กรุณาค้นหาและเลือกคนไข้ก่อนบันทึกผลแล็บ")
        return redirect('patients:doctor_lab_review')

    patient = get_object_or_404(Patient, pk=patient_id, is_deleted=False)
    files = request.FILES.getlist('lab_files')
    raw_text = request.POST.get('raw_text', '').strip()
    auto_approve = request.POST.get('auto_approve') == '1'

    if not files and not raw_text:
        messages.error(request, "กรุณาแนบไฟล์เอกสารผลแล็บอย่างน้อย 1 ไฟล์ หรือวางข้อความผลแล็บ")
        return redirect(f"{reverse('patients:doctor_lab_review')}?patient_id={patient.pk}")

    allowed_mimes = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}
    max_file_bytes = 15 * 1024 * 1024  # 15 MB

    saved_docs = []
    combined_text_parts = [raw_text] if raw_text else []
    vision_biomarkers = {}

    for f in files:
        content_type = (f.content_type or '').lower()
        name_lower = (f.name or '').lower()
        if content_type not in allowed_mimes:
            if name_lower.endswith('.pdf'):
                content_type = 'application/pdf'
            elif name_lower.endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif name_lower.endswith('.png'):
                content_type = 'image/png'
            elif name_lower.endswith('.webp'):
                content_type = 'image/webp'
            else:
                messages.warning(request, f"ข้ามไฟล์ {f.name}: รองรับเฉพาะ PDF, JPG, PNG, WEBP")
                continue

        raw_bytes = f.read()
        if not raw_bytes or len(raw_bytes) > max_file_bytes:
            messages.warning(request, f"ข้ามไฟล์ {f.name}: ไฟล์ว่างหรือมีขนาดเกิน 15 MB")
            continue

        # 1. เข้ารหัสและจัดเก็บไฟล์ต้นฉบับอย่างปลอดภัย (Pillar 14)
        meta = media_store.save_encrypted(raw_bytes, content_type, kind='lab_documents')
        meta['filename'] = f.name[:180]
        meta['uploaded_by'] = request.user.get_full_name() or request.user.username
        saved_docs.append(meta)

        # 2. สกัดข้อความ/ตัวเลขผลแล็บ
        if content_type == 'application/pdf':
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(raw_bytes))
                pdf_text = "\n".join((page.extract_text() or '') for page in reader.pages)
                if pdf_text.strip():
                    combined_text_parts.append(pdf_text)
            except Exception:
                pass
        elif content_type.startswith('image/'):
            ai_url = getattr(settings, 'AI_SERVICE_URL', '').rstrip('/')
            if ai_url:
                try:
                    headers = {}
                    internal_secret = getattr(settings, 'AI_INTERNAL_TOKEN', '')
                    if internal_secret:
                        headers['X-Internal-Token'] = internal_secret
                    resp = httpx.post(
                        f"{ai_url}/api/intake/lab",
                        files={'file': (f.name, raw_bytes, content_type)},
                        headers=headers,
                        timeout=8.0,
                    )
                    if resp.status_code == 200:
                        payload = resp.json()
                        for item in payload.get('markers', []):
                            if isinstance(item, dict) and 'marker' in item and 'value' in item:
                                try:
                                    val_num = float(item['value'])
                                    flag = str(item.get('flag', '')).lower()
                                    key = str(item['marker']).lower().replace(' ', '_')[:32]
                                    vision_biomarkers[key] = {
                                        'name': item['marker'],
                                        'value': val_num,
                                        'unit': item.get('unit', ''),
                                        'normal_max': None,
                                        'is_abnormal': flag in ('high', 'low', 'abnormal', 'critical'),
                                        'target_axis': None,
                                    }
                                except (TypeError, ValueError):
                                    continue
                except Exception:
                    pass

    # บันทึกเอกสารแนบเข้า patient.extra_data['lab_documents'] ในเวชระเบียน
    if saved_docs:
        if not isinstance(patient.extra_data, dict):
            patient.extra_data = {}
        existing_docs = patient.extra_data.get('lab_documents')
        if not isinstance(existing_docs, list):
            existing_docs = []
        patient.extra_data['lab_documents'] = saved_docs + existing_docs
        patient.save(update_fields=['extra_data'])

    # รัน Deterministic Parser จากข้อความที่รวบรวมได้
    combined_text = "\n".join(combined_text_parts).strip()
    parse_result = DeterministicLabParser.parse_text(combined_text) if combined_text else {
        'extracted_biomarkers': {},
        'affected_axes_scores': {},
        'total_biomarkers_found': 0,
        'abnormal_count': 0,
    }

    # รวมผลจาก Vision และ Deterministic Parser (ให้ Deterministic ทับซ้อนเพื่อได้ target_axis แม่นยำ)
    merged_markers = dict(vision_biomarkers)
    merged_markers.update(parse_result.get('extracted_biomarkers', {}))
    parse_result['extracted_biomarkers'] = merged_markers
    parse_result['total_biomarkers_found'] = len(merged_markers)
    parse_result['abnormal_count'] = sum(1 for m in merged_markers.values() if m.get('is_abnormal'))
    parse_result['documents'] = saved_docs
    if raw_text:
        parse_result['raw_text'] = raw_text[:2000]

    safety_res = ClinicalSafetyChecker.verify_safety(patient, parse_result)
    doc_names = ", ".join(d['filename'] for d in saved_docs[:3])
    title = f"นำเข้าผลแล็บ ({len(saved_docs)} เอกสาร: {doc_names})" if saved_docs else f"ผลสกัดแล็บ ({parse_result['total_biomarkers_found']} ค่า)"

    artifact = AgenticArtifact.objects.create(
        patient=patient,
        doctor=request.user,
        artifact_type='lab_extraction',
        title=title[:245],
        proposed_data=parse_result,
        safety_checks=safety_res,
        status='approved' if auto_approve else 'pending',
        reviewed_at=timezone.now() if auto_approve else None,
        doctor_notes='อนุมัติอัตโนมัติขณะนำเข้าเอกสารแล็บ' if auto_approve else '',
    )

    if auto_approve:
        _commit_lab_artifact_to_emr(artifact, request.user)

    AuditLog.objects.create(
        user=request.user,
        action="LAB_DOCUMENT_UPLOADED",
        model="AgenticArtifact",
        object_id=str(artifact.pk),
        changes={
            "patient_hn": patient.hn,
            "files_count": len(saved_docs),
            "biomarkers_found": parse_result['total_biomarkers_found'],
            "auto_approved": auto_approve,
        },
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    if auto_approve:
        messages.success(
            request,
            f"บันทึกเอกสารแล็บ {len(saved_docs)} ไฟล์ และนำเข้าค่าชีวเคมี {parse_result['total_biomarkers_found']} รายการเข้าแฟ้ม EMR ของ {patient.full_name} เรียบร้อยแล้ว"
        )
    else:
        messages.success(
            request,
            f"บันทึกเอกสารแล็บ {len(saved_docs)} ไฟล์ ของ {patient.full_name} แล้ว (สกัดได้ {parse_result['total_biomarkers_found']} รายการ — รอแพทย์ตรวจทาน)"
        )
    return redirect('patients:doctor_lab_review')


@clinical_staff_required
@require_http_methods(["POST"])
def doctor_lab_artifact_approve(request, artifact_id):
    """อนุมัติหรือปฏิเสธผลแล็บโดยตรงจากหน้า Lab Review และบันทึกลง EMR"""
    from intelligence.models import AgenticArtifact

    artifact = get_object_or_404(AgenticArtifact, pk=artifact_id, artifact_type='lab_extraction')
    action = request.POST.get('action', 'approve')
    artifact.doctor = request.user
    artifact.reviewed_at = timezone.now()

    if action == 'approve':
        artifact.status = 'approved'
        artifact.save()
        _commit_lab_artifact_to_emr(artifact, request.user)
        AuditLog.objects.create(
            user=request.user,
            action="ARTIFACT_APPROVED_BY_PHYSICIAN",
            model="AgenticArtifact",
            object_id=str(artifact.pk),
            changes={"status": "approved", "patient_hn": artifact.patient.hn},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        messages.success(request, f"อนุมัติผลแล็บของ {artifact.patient.full_name} เข้าสู่แฟ้ม EMR และอัปเดต 39 แกนเรียบร้อยแล้ว")
    elif action == 'reject':
        artifact.status = 'rejected'
        artifact.save()
        AuditLog.objects.create(
            user=request.user,
            action="ARTIFACT_REJECTED_BY_PHYSICIAN",
            model="AgenticArtifact",
            object_id=str(artifact.pk),
            changes={"status": "rejected", "patient_hn": artifact.patient.hn},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        messages.warning(request, f"ปฏิเสธรายการผลแล็บ #{artifact.pk} แล้ว")

    return redirect('patients:doctor_lab_review')


@clinical_staff_required
def patient_lab_document_view(request, patient_id, media_id):
    """
    เปิดดูเอกสารผลแล็บที่เข้ารหัสไว้ใน PRIVATE_MEDIA_ROOT อย่างปลอดภัย พร้อมบันทึก AuditLog
    """
    from django.http import HttpResponse, Http404
    from clinical import media_store

    patient = get_object_or_404(Patient, pk=patient_id, is_deleted=False)
    docs = (patient.extra_data or {}).get('lab_documents', []) if isinstance(patient.extra_data, dict) else []
    target_meta = next((d for d in docs if isinstance(d, dict) and d.get('media_id') == media_id), None)

    if not target_meta:
        # ค้นหาใน AgenticArtifact เผื่อกรณีเอกสารติดอยู่ใน proposed_data
        from intelligence.models import AgenticArtifact
        for art in AgenticArtifact.objects.filter(patient=patient, artifact_type='lab_extraction'):
            art_docs = (art.proposed_data or {}).get('documents', []) if isinstance(art.proposed_data, dict) else []
            target_meta = next((d for d in art_docs if isinstance(d, dict) and d.get('media_id') == media_id), None)
            if target_meta:
                break

    if not target_meta:
        raise Http404("ไม่พบเอกสารแล็บที่ต้องการ")

    data = media_store.read_decrypted(target_meta)
    if data is None:
        raise Http404("ไม่สามารถถอดรหัสเอกสารได้ หรือไฟล์สูญหาย")

    AuditLog.objects.create(
        user=request.user,
        action="LAB_DOCUMENT_VIEWED",
        model="Patient",
        object_id=str(patient.pk),
        changes={"patient_hn": patient.hn, "media_id": media_id, "filename": target_meta.get('filename', '')},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    resp = HttpResponse(data, content_type=target_meta.get('content_type', 'application/octet-stream'))
    filename = target_meta.get('filename', f'lab_{media_id}')
    resp['Content-Disposition'] = f'inline; filename="{filename}"'
    return resp


def _load_clinical_json(filename: str) -> dict:
    """โหลดไฟล์ JSON จาก apps/clinical/data อย่างปลอดภัย"""
    import json
    from pathlib import Path
    from django.conf import settings
    path = Path(settings.BASE_DIR) / 'apps' / 'clinical' / 'data' / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


@clinical_staff_required
def doctor_knowledge_rag(request):
    """
    สืบค้นองค์ความรู้และหลักฐานทางคลินิก RAG (/doctor/knowledge-rag/)
    ค้นหาจากฐานข้อมูลจริง: 39 แกนชีววิทยา, 281 โมดูลพฤกษเคมี, กฎคลินิก และเกณฑ์แล็บ
    """
    from clinical.engine import TspiClinicalEngine
    from intelligence.models import KnowledgeDocument

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', 'all').strip()
    if cat not in ('all', 'external', 'axes', 'modules', 'rules', 'labs'):
        cat = 'all'

    all_axes = TspiClinicalEngine.get_all_axes()
    all_modules = TspiClinicalEngine.get_modules_data()
    rules = _load_clinical_json('clinical_rules.json').get('rules', [])
    lab_mappings = _load_clinical_json('lab_mapping.json').get('mappings', [])
    ext_docs = list(KnowledgeDocument.objects.filter(is_active=True).select_related('created_by')[:200])

    corpus = []

    # 0. Index External / Clinic Knowledge Documents (ความรู้ภายนอกที่คลินิกนำเข้าใหม่)
    for doc in ext_docs:
        tag_list = doc.tag_list()
        corpus.append({
            'id': doc.pk,
            'is_external': True,
            'category': 'external',
            'category_label': doc.get_category_display(),
            'title': doc.title,
            'source': doc.source_name or f"Clinic External KB • เพิ่มโดย {doc.created_by.get_full_name() or doc.created_by.username if doc.created_by else 'Physician'}",
            'source_url': doc.source_url,
            'created_at': doc.created_at,
            'excerpt': doc.content,
            'safety_note': '',
            'tags': tag_list or [doc.get_category_display()],
            'search_blob': f"{doc.title} {doc.source_name} {doc.content} {doc.tags}".lower(),
            'copilot_query': f"ช่วยวิเคราะห์และสรุปการประยุกต์ใช้ทางคลินิกจากองค์ความรู้นี้: {doc.title}",
        })

    # 1. Index 39 Axes
    for ax in all_axes:
        ax_id = ax.get('axis_id')
        sub_texts = []
        if isinstance(ax.get('sub_axes'), dict):
            for k, v in ax['sub_axes'].items():
                if isinstance(v, dict):
                    sub_texts.append(f"[{k}] {v.get('name', '')}: {v.get('description', '')}")
        excerpt = " | ".join(sub_texts) or ax.get('description', '')
        corpus.append({
            'category': 'axes',
            'category_label': '39 แกนชีววิทยา',
            'title': f"Axis {ax_id}: {ax.get('name', '')}",
            'source': f"TSPI Canonical Ontology • {ax.get('domain_title', '')}",
            'excerpt': excerpt,
            'safety_note': '',
            'tags': [f"Axis {ax_id}", ax.get('domain_title', '')] + list((ax.get('modules') or [])[:3]),
            'search_blob': f"axis {ax_id} {ax.get('name', '')} {ax.get('domain_title', '')} {excerpt} {' '.join(ax.get('modules') or [])}".lower(),
            'copilot_query': f"ช่วยอธิบายกลไกระดับเซลล์ของ Axis {ax_id}: {ax.get('name', '')} และแนวทางฟื้นฟูทางคลินิก",
        })

    # 2. Index 281 Therapeutic Modules
    for mod in all_modules:
        code = mod.get('code', 'MOD')
        prod_id = mod.get('Code /_Product ID', '')
        name = mod.get('name', '')
        botanical = mod.get('Botanical Composition', '')
        mech = mod.get('Mechanistic Function') or mod.get('description') or mod.get('Summary of Biological Activity') or ''
        markers = mod.get('Key Bioactive Markers_(LC-MS)', '')
        axis_map = mod.get('TSPI Axis Mapping', '')
        safety = mod.get('Safety Profile', '')
        risk_score = mod.get('Drug-Herb Interaction_Risk Score', '')
        dose = mod.get('Recommended Dose /_Treatment Duration', '')
        safety_parts = []
        if dose:
            safety_parts.append(f"ขนาด/ระยะเวลา: {dose}")
        if risk_score:
            safety_parts.append(f"Interaction Risk: {risk_score}")
        if safety:
            safety_parts.append(f"ความปลอดภัย: {safety[:160]}")

        tags = [code]
        if prod_id:
            tags.append(prod_id)
        if botanical:
            tags.append(botanical[:40])
        if markers:
            tags.extend([m.strip() for m in str(markers).split()[:3] if len(m.strip()) > 2])

        corpus.append({
            'category': 'modules',
            'category_label': '281 โมดูลพฤกษเคมี',
            'title': f"{code} — {name}",
            'source': f"TSPI Phytochemical Compendium ({prod_id or code}) • {botanical}",
            'excerpt': mech or f"สารสกัดสำคัญ: {markers} | แกนที่เกี่ยวข้อง: {axis_map}",
            'safety_note': " | ".join(safety_parts),
            'tags': tags[:6],
            'search_blob': f"{code} {prod_id} {name} {botanical} {mech} {markers} {axis_map} {safety}".lower(),
            'copilot_query': f"ช่วยวิเคราะห์กลไกการออกฤทธิ์ ข้อบ่งใช้ และข้อควรระวัง (Drug-Herb Interaction) ของโมดูล {code} ({name})",
        })

    # 3. Index Clinical Rules
    for rule in rules:
        params = rule.get('params', {})
        corpus.append({
            'category': 'rules',
            'category_label': 'กฎเชื่อมโยงคลินิก',
            'title': f"{rule.get('id', '')}: {rule.get('name', '')}",
            'source': f"Deterministic Cross-Axis Rule • Priority: {params.get('priority', 'STANDARD')}",
            'excerpt': f"เงื่อนไข: {rule.get('condition', '')} — {params.get('reason', '')}",
            'safety_note': f"แนะนำโมดูลเป้าหมาย: {params.get('moduleId', '-')}",
            'tags': [rule.get('id', ''), params.get('moduleId', ''), params.get('priority', '')],
            'search_blob': f"{rule.get('id', '')} {rule.get('name', '')} {rule.get('condition', '')} {params.get('reason', '')} {params.get('moduleId', '')}".lower(),
            'copilot_query': f"ช่วยอธิบายเหตุผลทางคลินิกของกฎ {rule.get('name', '')} ({rule.get('condition', '')})",
        })

    # 4. Index Lab Mappings
    for lm in lab_mappings:
        marker = lm.get('marker', '')
        axis_id = lm.get('axisId', '')
        opt = lm.get('optimalRange', {})
        crit = lm.get('criticalRange', {})
        corpus.append({
            'category': 'labs',
            'category_label': 'เกณฑ์แล็บชีวเคมี',
            'title': f"Biomarker: {marker} → {axis_id}",
            'source': f"TSPI Lab Ontology • Weight: {lm.get('weight', '-')}",
            'excerpt': f"ค่าเหมาะสม (Optimal): {opt.get('min', 0)} – {opt.get('max', '-')} | ค่าวิกฤต (Critical): ≥ {crit.get('min', '-')}",
            'safety_note': '',
            'tags': [marker, axis_id, f"Weight {lm.get('weight', '')}"],
            'search_blob': f"{marker} {axis_id} lab biomarker optimal critical".lower(),
            'copilot_query': f"ช่วยอธิบายความสัมพันธ์ระหว่างค่าแล็บ {marker} กับ {axis_id} ในเชิงการแพทย์แม่นยำ",
        })

    filtered_corpus = [item for item in corpus if cat == 'all' or item['category'] == cat]

    if q:
        terms = [t.strip().lower() for t in q.split() if len(t.strip()) >= 2] or [q.lower()]
        scored = []
        for item in filtered_corpus:
            score = 0
            title_l = item['title'].lower()
            blob_l = item['search_blob']
            for term in terms:
                if term in title_l:
                    score += 10
                if term in blob_l:
                    score += 3 + blob_l.count(term)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item for _, item in scored[:24]]
        total_matched = len(scored)
    else:
        # เมื่อยังไม่พิมพ์ค้นหา แสดงความรู้ที่เพิ่มใหม่ล่าสุด + ภาพรวมจากคลังข้อมูลจริง
        if cat == 'all':
            results = (
                [c for c in corpus if c['category'] == 'external'][:4]
                + [c for c in corpus if c['category'] == 'rules'][:3]
                + [c for c in corpus if c['category'] == 'axes'][:3]
                + [c for c in corpus if c['category'] == 'modules'][:4]
            )
        else:
            results = filtered_corpus[:12]
        total_matched = len(filtered_corpus)

    return render(request, 'patients/doctor_knowledge_rag.html', {
        'q': q,
        'cat': cat,
        'results': results,
        'total_matched': total_matched,
        'counts': {
            'external': len(ext_docs),
            'axes': len(all_axes),
            'modules': len(all_modules),
            'rules': len(rules),
            'labs': len(lab_mappings),
        },
        'kb_categories': KnowledgeDocument.CATEGORY_CHOICES,
    })


@clinical_staff_required
@require_http_methods(["POST"])
def doctor_knowledge_rag_add(request):
    """
    เพิ่มองค์ความรู้ภายนอก/งานวิจัย/โปรโตคอลใหม่เข้าคลัง Knowledge RAG
    รองรับทั้งกรอกข้อความโดยตรงและอัปโหลดไฟล์ PDF / TXT / MD (สกัดข้อความด้วย pypdf)
    """
    import io
    from intelligence.models import KnowledgeDocument

    title = request.POST.get('title', '').strip()
    category = request.POST.get('category', 'research').strip()
    source_name = request.POST.get('source_name', '').strip()
    source_url = request.POST.get('source_url', '').strip()
    content = request.POST.get('content', '').strip()
    tags = request.POST.get('tags', '').strip()
    doc_file = request.FILES.get('doc_file')

    valid_cats = dict(KnowledgeDocument.CATEGORY_CHOICES)
    if category not in valid_cats:
        category = 'research'

    extracted_file_text = ''
    if doc_file:
        fname = (doc_file.name or '').lower()
        raw_bytes = doc_file.read()
        if fname.endswith('.pdf'):
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(raw_bytes))
                extracted_file_text = "\n".join((p.extract_text() or '') for p in reader.pages[:20]).strip()
            except Exception:
                extracted_file_text = ''
        elif fname.endswith(('.txt', '.md', '.csv')):
            try:
                extracted_file_text = raw_bytes.decode('utf-8', errors='replace').strip()
            except Exception:
                extracted_file_text = ''
        if not source_name and doc_file.name:
            source_name = f"เอกสารแนบ: {doc_file.name[:160]}"

    full_content = "\n\n".join(part for part in [content, extracted_file_text] if part).strip()

    if not title or not full_content:
        messages.error(request, "กรุณาระบุหัวข้อและเนื้อหา (หรือแนบไฟล์ PDF/TXT ที่มีข้อความ)")
        return redirect('patients:doctor_knowledge_rag')

    doc = KnowledgeDocument.objects.create(
        title=title[:250],
        category=category,
        source_name=source_name[:200],
        source_url=source_url[:500] if source_url else '',
        content=full_content[:20000],
        tags=tags[:300],
        created_by=request.user,
    )

    AuditLog.objects.create(
        user=request.user,
        action="KNOWLEDGE_DOCUMENT_ADDED",
        model="KnowledgeDocument",
        object_id=str(doc.pk),
        changes={"title": doc.title, "category": doc.category, "has_file": bool(doc_file)},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    messages.success(request, f"เพิ่มองค์ความรู้ \"{doc.title}\" เข้าสู่ระบบ Knowledge RAG เรียบร้อยแล้ว")
    return redirect(f"{reverse('patients:doctor_knowledge_rag')}?cat=external")


@clinical_staff_required
@require_http_methods(["POST"])
def doctor_knowledge_rag_delete(request, doc_id):
    """ซ่อน/นำองค์ความรู้ที่เพิ่มเองออกจากคลัง RAG (Soft Archive)"""
    from intelligence.models import KnowledgeDocument

    doc = get_object_or_404(KnowledgeDocument, pk=doc_id, is_active=True)
    doc.is_active = False
    doc.save(update_fields=['is_active'])

    AuditLog.objects.create(
        user=request.user,
        action="KNOWLEDGE_DOCUMENT_ARCHIVED",
        model="KnowledgeDocument",
        object_id=str(doc.pk),
        changes={"title": doc.title},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    messages.info(request, f"นำรายการ \"{doc.title}\" ออกจากคลังสืบค้นแล้ว")
    return redirect('patients:doctor_knowledge_rag')


def _eval_rule_condition(condition: str, scores_dict: dict) -> bool:
    """ประเมินเงื่อนไขกฎข้ามแกนเช่น 'AXIS_1 > 70 AND AXIS_19 > 60' อย่างปลอดภัย"""
    import re
    if not condition or not scores_dict:
        return False
    parts = [p.strip() for p in re.split(r'\s+AND\s+', condition, flags=re.IGNORECASE)]
    for part in parts:
        m = re.match(r'^AXIS_(\d+)\s*(>=|<=|>|<|==)\s*(\d+(?:\.\d+)?)$', part, flags=re.IGNORECASE)
        if not m:
            return False
        ax_id = int(m.group(1))
        op = m.group(2)
        threshold = float(m.group(3))
        val = scores_dict.get(ax_id)
        if val is None:
            return False
        if op == '>' and not (val > threshold):
            return False
        elif op == '>=' and not (val >= threshold):
            return False
        elif op == '<' and not (val < threshold):
            return False
        elif op == '<=' and not (val <= threshold):
            return False
        elif op == '==' and not (val == threshold):
            return False
    return True


def _build_tspi_brain_trace(patient):
    """สร้าง Trace 4 ขั้นตอนจริงจากเวชระเบียนของคนไข้"""
    from clinical.engine import TspiClinicalEngine
    from intelligence.models import AgenticArtifact

    latest_soap = patient.histories.filter(is_deleted=False).order_by('-visit_date', '-id').first()
    latest_vitals = latest_soap.vitals if latest_soap and isinstance(latest_soap.vitals, dict) else {}

    # Stage 1: Labs & Biomarkers
    patient_labs = []
    if isinstance(patient.extra_data, dict) and isinstance(patient.extra_data.get('biomarkers'), dict):
        for k, m in patient.extra_data['biomarkers'].items():
            if isinstance(m, dict) and 'value' in m:
                patient_labs.append(m)

    # Stage 2: 39 Axes & Cross-Axis Rules
    latest_record = patient.biological_records.first()
    scores_dict = latest_record.to_scores_dict() if latest_record else {}
    all_axes = TspiClinicalEngine.get_all_axes()
    dysfunctional_axes = []
    if scores_dict:
        for ax in all_axes:
            ax_id = ax.get('axis_id')
            sc = scores_dict.get(ax_id)
            if sc is not None and sc >= 60:
                dysfunctional_axes.append({
                    'axis_id': ax_id,
                    'name': ax.get('name'),
                    'domain_title': ax.get('domain_title'),
                    'score': sc,
                })
        dysfunctional_axes.sort(key=lambda x: x['score'], reverse=True)

    rules = _load_clinical_json('clinical_rules.json').get('rules', [])
    evaluated_rules = []
    for r in rules:
        triggered = _eval_rule_condition(r.get('condition', ''), scores_dict)
        evaluated_rules.append({
            'id': r.get('id'),
            'name': r.get('name'),
            'condition': r.get('condition'),
            'params': r.get('params', {}),
            'triggered': triggered,
        })

    # Stage 3: 3-Phase Protocol Alignment
    phase_defs = [
        ('Phase 1: Gut Barrier, Detox & Acute Inflammation', [1, 2, 15, 16, 17, 18, 19]),
        ('Phase 2: Metabolic, Glucose-Insulin & Mitochondrial Core', [5, 6, 7, 8, 9, 10]),
        ('Phase 3: Neuro-Endocrine, Vascular & Tissue Regeneration', [20, 21, 24, 25, 26, 31, 34, 35]),
    ]
    phases = []
    for title, axis_ids in phase_defs:
        vals = [scores_dict[a] for a in axis_ids if a in scores_dict and scores_dict[a] is not None]
        avg_score = round(sum(vals) / len(vals), 1) if vals else None
        high_axes = [a for a in axis_ids if (scores_dict.get(a) or 0) >= 60]
        phases.append({
            'title': title,
            'avg_score': avg_score,
            'high_count': len(high_axes),
            'is_priority': bool(high_axes),
        })

    # Stage 4: Module Dispatch & Artifact Status
    matched_modules = TspiClinicalEngine.match_therapeutic_recommendations(dysfunctional_axes, limit=6) if dysfunctional_axes else []
    pending_artifacts = AgenticArtifact.objects.filter(patient=patient, status='pending').count()
    approved_artifacts = AgenticArtifact.objects.filter(patient=patient, status='approved').count()

    return {
        'latest_soap': latest_soap,
        'latest_vitals': latest_vitals,
        'patient_labs': patient_labs,
        'latest_record': latest_record,
        'scores_dict': scores_dict,
        'dysfunctional_axes': dysfunctional_axes,
        'evaluated_rules': evaluated_rules,
        'triggered_rules_count': sum(1 for r in evaluated_rules if r['triggered']),
        'phases': phases,
        'matched_modules': matched_modules,
        'pending_artifacts': pending_artifacts,
        'approved_artifacts': approved_artifacts,
    }


@clinical_staff_required
def doctor_tspi_brain(request):
    """
    ระบบแสดงกลไกการคิดและตรวจสอบรอยแยกการให้เหตุผลของ TSPI Brain Engine (/doctor/tspi-brain/)
    เชื่อมโยงข้อมูลจริง 4 ขั้นตอนของคนไข้แต่ละราย (Zero-Mock)
    """
    patient_id = request.GET.get('patient_id')
    patient = None
    if patient_id and str(patient_id).isdigit():
        patient = get_object_or_404(Patient, pk=patient_id, is_deleted=False)

    recent_patients = Patient.objects.filter(is_deleted=False).order_by('-created_at')[:6]
    trace = _build_tspi_brain_trace(patient) if patient else None

    return render(request, 'patients/doctor_tspi_brain.html', {
        'patient': patient,
        'recent_patients': recent_patients,
        'trace': trace,
    })


@clinical_staff_required
@require_http_methods(["POST"])
def doctor_tspi_brain_dispatch(request, patient_id):
    """
    ส่งแผนโมดูลที่ TSPI Brain Engine คำนวณได้เข้าสู่ Artifact Review Gate เพื่อรอแพทย์ลงนาม
    """
    from intelligence.models import AgenticArtifact
    from intelligence.services import ClinicalSafetyChecker

    patient = get_object_or_404(Patient, pk=patient_id, is_deleted=False)
    trace = _build_tspi_brain_trace(patient)

    if not trace['dysfunctional_axes'] and not trace['matched_modules']:
        messages.warning(request, f"ไม่พบแกนชีวภาพผิดปกติหรือโมดูลแนะนำสำหรับ {patient.full_name} กรุณาประเมิน 39 แกนก่อนส่งตรวจทาน")
        return redirect(f"{reverse('patients:doctor_tspi_brain')}?patient_id={patient.pk}")

    affected_scores = {str(ax['axis_id']): ax['score'] for ax in trace['dysfunctional_axes']}
    recommended_modules = [
        {
            'code': m.get('code'),
            'name': m.get('name'),
            'description': (m.get('description') or '')[:220],
        }
        for m in trace['matched_modules']
    ]
    triggered_rules = [r for r in trace['evaluated_rules'] if r['triggered']]

    proposed_data = {
        'affected_axes_scores': affected_scores,
        'recommended_modules': recommended_modules,
        'triggered_rules': triggered_rules,
        'priority_phases': [p['title'] for p in trace['phases'] if p['is_priority']],
    }
    safety_res = ClinicalSafetyChecker.verify_safety(patient, proposed_data)

    artifact = AgenticArtifact.objects.create(
        patient=patient,
        doctor=request.user,
        artifact_type='therapeutic_plan',
        title=f"แผนบำบัด TSPI Brain ({len(recommended_modules)} โมดูล • {len(affected_scores)} แกนวิกฤต)",
        proposed_data=proposed_data,
        safety_checks=safety_res,
        status='pending',
    )

    AuditLog.objects.create(
        user=request.user,
        action="TSPI_BRAIN_DISPATCHED_ARTIFACT",
        model="AgenticArtifact",
        object_id=str(artifact.pk),
        changes={"patient_hn": patient.hn, "modules_count": len(recommended_modules)},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    messages.success(request, f"ส่งแผนบำบัดของ {patient.full_name} เข้าคิวตรวจทานผล AI (Artifact Review Gate) เรียบร้อยแล้ว")
    return redirect('intelligence:artifact_review')


@clinical_staff_required
def doctor_chats(request):
    """
    ห้องแชทผ่าน LINE OA (/doctor/chats/) — เดิมเป็นหน้าจำลองที่ไม่ได้ส่งข้อความจริง
    ส่งต่อไปยัง Unified Inbox ที่อ่าน/ตอบแชทจริง
    """
    return redirect('root_staff_inbox')


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
    if request.method == 'POST' and request.POST.get('action') == 'set_chat_permissions':
        if not request.user.is_superuser:
            raise PermissionDenied("เฉพาะเจ้าของระบบ (owner) เท่านั้น")
        from accounts.models import User
        allowed_ids = {int(x) for x in request.POST.getlist('can_reply') if x.isdigit()}
        changed = []
        for staff in User.objects.filter(is_superuser=False, role__in=['admin', 'nurse', 'nursing_assistant', 'staff']):
            new_value = staff.pk in allowed_ids
            if staff.can_reply_line_chat != new_value:
                staff.can_reply_line_chat = new_value
                staff.save(update_fields=['can_reply_line_chat'])
                changed.append({'user': staff.username, 'can_reply_line_chat': new_value})
        AuditLog.objects.create(
            user=request.user, action='LINE_CHAT_PERMISSIONS_UPDATED', model='User', object_id='bulk',
            changes={'changed': changed}, client_ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        messages.success(request, f"บันทึกสิทธิ์ตอบแชทแล้ว ({len(changed)} รายการเปลี่ยน)")
        return redirect('patients:doctor_settings')

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
    chat_staff = None
    if request.user.is_superuser:
        from accounts.models import User
        chat_staff = User.objects.filter(is_active=True, role__in=['doctor', 'admin', 'nurse', 'nursing_assistant', 'staff']).order_by('role', 'username')
    return render(request, 'patients/doctor_settings.html', {'ai_usage': ai_usage, 'chat_staff': chat_staff})


@clinical_staff_required
def api_patient_search(request):
    """
    API ค้นหาคนไข้แบบ Real-time AJAX Autocomplete (Pillar 5 Performance)
    รองรับค้นหาด้วยชื่อ, นามสกุล, HN หรือเบอร์โทรศัพท์ คืนผลลัพธ์ทันที
    """
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'patients': []})
    
    # พิมพ์ชื่อเต็ม "สมชาย ใจดี" ได้: ทุกคำต้องตรงกับชื่อ นามสกุล HN หรือเบอร์ อย่างใดอย่างหนึ่ง
    condition = Q()
    for term in q.split()[:4]:
        condition &= (Q(first_name__icontains=term) | Q(last_name__icontains=term) |
                      Q(hn__icontains=term) | Q(phone__icontains=term))
    patients = Patient.objects.filter(condition).order_by('-created_at')[:15]

    data = [{
        'id': p.id,
        'hn': p.hn,
        'full_name': p.full_name,
        'first_name': p.first_name,
        'last_name': p.last_name,
        'age': p.age,
        'gender': p.get_gender_display(),
        'gender_code': p.gender,
        'phone': p.phone or '-',
    } for p in patients]
    
    return JsonResponse({'results': data, 'patients': data})


@clinical_staff_required
@require_http_methods(["POST"])
def patient_lab_save_view(request, patient_id):
    """
    บันทึกหรืออัปเดตผลตรวจแล็บของคนไข้เข้าสู่เวชระเบียน และแมปเข้ากับ 39 แกนชีววิทยา
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    from intelligence.models import AgenticArtifact
    
    # กำหนดนิยามตัวชี้วัดแล็บ เกณฑ์ Cutoff และแกนชีวภาพเป้าหมาย
    LAB_CONFIG = [
        ('hscrp', 'hsCRP', 'mg/L', lambda v: v > 3.0, 'Axis 1: Systemic Inflammation'),
        ('il6', 'IL-6', 'pg/mL', lambda v: v > 5.0, 'Axis 1: Systemic Inflammation'),
        ('insulin', 'Fasting Insulin', 'uIU/mL', lambda v: v > 10.0, 'Axis 5: Glucose-Insulin'),
        ('homair', 'HOMA-IR', 'Index', lambda v: v > 2.0, 'Axis 5: Glucose-Insulin'),
        ('hba1c', 'HbA1c', '%', lambda v: v >= 5.7, 'Axis 5: Glucose-Insulin'),
        ('tghdl', 'TG / HDL Ratio', 'Ratio', lambda v: v > 2.5, 'Axis 6: Lipid Lipotoxicity'),
        ('zonulin', 'Zonulin', 'ng/mL', lambda v: v > 38.0, 'Axis 15: Gut Mucosal Barrier'),
        ('calprotectin', 'Calprotectin', 'ug/g', lambda v: v > 50.0, 'Axis 15: Gut Mucosal Barrier'),
        ('alt', 'ALT / AST', 'U/L', lambda v: v > 35.0, 'Axis 11: Hepatic Biotransformation'),
        ('ohdg', '8-OHdG', 'ng/mg', lambda v: v > 5.0, 'Axis 9: DNA Damage & Repair'),
        ('cortisol', 'Cortisol (Morning)', 'ug/dL', lambda v: not (10.0 <= v <= 20.0), 'Axis 26: HPA Axis Dynamics'),
        ('egfr', 'eGFR', 'mL/min', lambda v: v < 90.0, 'Axis 33: Cardiorenal Synergies'),
    ]
    
    extracted_biomarkers = {}
    for code, name, unit, is_abnormal_fn, target_axis in LAB_CONFIG:
        val_str = request.POST.get(code, '').strip()
        if val_str:
            try:
                val = float(val_str)
                extracted_biomarkers[code] = {
                    'name': name,
                    'value': val,
                    'unit': unit,
                    'is_abnormal': is_abnormal_fn(val),
                    'target_axis': target_axis,
                }
            except ValueError:
                pass
                
    if extracted_biomarkers:
        # 1. บันทึกลงใน AgenticArtifact (ชิ้นงานแล็บที่อนุมัติแล้ว)
        AgenticArtifact.objects.update_or_create(
            patient=patient,
            artifact_type='lab_extraction',
            defaults={
                'doctor': request.user,
                'title': f'ผลตรวจแล็บ {patient.full_name} ({timezone.now().strftime("%d/%m/%Y")})',
                'proposed_data': {'extracted_biomarkers': extracted_biomarkers},
                'status': 'approved',
                'doctor_notes': 'บันทึกผ่านแฟ้มเวชระเบียนคนไข้โดยแพทย์/พยาบาล'
            }
        )
        # 2. บันทึกลงใน patient.extra_data
        if not isinstance(patient.extra_data, dict):
            patient.extra_data = {}
        patient.extra_data['biomarkers'] = extracted_biomarkers
        patient.extra_data['latest_lab_date'] = timezone.now().isoformat()
        patient.save(update_fields=['extra_data'])

        AuditLog.objects.create(
            user=request.user,
            action="PATIENT_LABS_UPDATED",
            model="Patient",
            object_id=str(patient.pk),
            changes={"biomarkers_count": len(extracted_biomarkers), "hn": patient.hn},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        messages.success(request, f"บันทึกผลแล็บ {len(extracted_biomarkers)} รายการของ {patient.full_name} เรียบร้อยแล้ว")
    else:
        messages.warning(request, "ไม่พบค่าตัวเลขผลแล็บที่กรอก กรุณาระบุค่าตัวเลขอย่างน้อย 1 รายการ")

    return redirect('patients:patient_detail', patient_id=patient.pk)
