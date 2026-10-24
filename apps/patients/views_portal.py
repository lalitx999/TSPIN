"""
Patient Portal Views for TSPI Clinic (Pillars 1, 2, 8, 15).
Provides Mobile-first, Patient-facing Dashboard, Health Status Visualization,
Strict IDOR Prevention, and Approved Reports Access.
"""

from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest, HttpResponseForbidden, Http404
from django.contrib.auth import login, logout, authenticate
from django.urls import reverse
from django.contrib import messages

from accounts.models import User, AuditLog
from patients.models import Patient, PatientLinkingToken, Appointment
from clinical.models import AnalysisRecord
from clinical.engine import TspiClinicalEngine


def patient_portal_required(view_func):
    """
    Decorator ป้องกันสิทธิ์การเข้าถึง Patient Portal (Pillar 2: RBAC & IDOR Prevention)
    ตรวจสอบว่ามีเซสชันของคนไข้ (Session portal_patient_id หรือ User role='patient')
    """
    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs):
        patient_id = request.session.get('portal_patient_id')
        patient = None

        if patient_id:
            patient = Patient.objects.filter(pk=patient_id).first()

        # กรณีล็อกอินด้วย User บัญชีทางการ
        if not patient and request.user.is_authenticated:
            if request.user.role == User.Role.PATIENT:
                patient = getattr(request.user, 'patient_record', None)
                if not patient:
                    patient = Patient.objects.filter(phone=request.user.phone).first()

        if not patient:
            return redirect('portal_patient:portal_login')

        request.portal_patient = patient
        return view_func(request, *args, **kwargs)

    return _wrapped


def portal_login_view(request: HttpRequest) -> HttpResponse:
    """
    หน้าเข้าสู่ระบบ Patient Portal
    รองรับทั้ง:
    1. เข้าสู่ระบบด้วย HN และเบอร์โทรศัพท์ที่ลงทะเบียนไว้
    2. เข้าสู่ระบบด้วยชื่อผู้ใช้/รหัสผ่าน (User role='patient')
    """
    if request.session.get('portal_patient_id'):
        return redirect('portal_patient:portal_dashboard')

    if request.method == 'POST':
        auth_mode = request.POST.get('auth_mode', 'hn_phone')

        if auth_mode == 'hn_phone':
            hn = request.POST.get('hn', '').strip().upper()
            phone = request.POST.get('phone', '').strip().replace('-', '').replace(' ', '')

            patient = Patient.objects.filter(hn=hn).first()
            if patient:
                # ตรวจสอบเบอร์โทรศัพท์ (Normalized comparison)
                clean_patient_phone = patient.phone.replace('-', '').replace(' ', '')
                if clean_patient_phone == phone or (len(phone) >= 9 and phone in clean_patient_phone):
                    # ตั้งค่าเซสชันของคนไข้
                    request.session['portal_patient_id'] = patient.pk

                    AuditLog.objects.create(
                        action='PATIENT_PORTAL_LOGIN_SUCCESS',
                        user=patient.user,
                        model='Patient',
                        object_id=str(patient.pk),
                        client_ip=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        changes={'details': f"Patient {patient.hn} ({patient.full_name}) logged into Portal"}
                    )
                    return redirect('portal_patient:portal_dashboard')

            AuditLog.objects.create(
                action='PATIENT_PORTAL_LOGIN_FAILED',
                user=None,
                model='Patient',
                object_id=hn,
                client_ip=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                changes={'details': f"Failed portal login attempt for HN: {hn}"}
            )
            messages.error(request, 'ไม่พบหมายเลข HN หรือเบอร์โทรศัพท์ไม่ตรงกับข้อมูลในระบบ')

        elif auth_mode == 'credentials':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            user = authenticate(request, username=username, password=password)

            if user and user.is_active and user.role == User.Role.PATIENT:
                login(request, user)
                patient = getattr(user, 'patient_record', None) or Patient.objects.filter(phone=user.phone).first()
                if patient:
                    request.session['portal_patient_id'] = patient.pk
                return redirect('portal_patient:portal_dashboard')
            else:
                messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง หรือไม่มีสิทธิ์เข้าถึงพอร์ทัลคนไข้')

    return render(request, 'portal/portal_login.html')


def portal_logout_view(request: HttpRequest) -> HttpResponse:
    """ออกจากระบบ Patient Portal"""
    patient_id = request.session.get('portal_patient_id')
    if patient_id:
        del request.session['portal_patient_id']
    if request.user.is_authenticated:
        logout(request)
    return redirect('portal_patient:portal_login')


@patient_portal_required
def portal_dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    หน้าแรกของผู้ป่วย (Patient Portal Dashboard)
    แสดงภาพรวมสุขภาพ 12 โดเมน, ตารางนัดหมาย, และรายงานที่แพทย์อนุมัติแล้ว
    """
    patient = request.portal_patient

    # ตารางนัดหมายที่กำลังจะมาถึง
    upcoming_appointments = patient.appointments.filter(
        status__in=['scheduled', 'confirmed']
    ).order_by('appointment_date', 'appointment_time')

    # รายงานการแพทย์แม่นยำ (แสดงเฉพาะฉบับที่อนุมัติแล้วเท่านั้น! Pillar 15)
    approved_reports = AnalysisRecord.objects.filter(
        patient=patient,
        status__in=['approved', 'released']
    ).order_by('-analysis_date')

    # ดึงค่าคะแนนแกนชีวภาพเพื่อแสดงเรดาร์ 12 โดเมน
    bio_record = getattr(patient, 'biological_record', None)
    domain_scores = []
    if bio_record:
        scores_dict = bio_record.to_scores_dict()
        domain_scores = TspiClinicalEngine.calculate_domain_scores(scores_dict)

    # ตรวจสอบว่าผูก LINE OA แล้วหรือยัง
    is_line_bound = bool(patient.line_user_id)

    return render(request, 'portal/portal_dashboard.html', {
        'patient': patient,
        'upcoming_appointments': upcoming_appointments,
        'approved_reports': approved_reports,
        'domain_scores': domain_scores,
        'is_line_bound': is_line_bound,
    })


@patient_portal_required
def portal_report_detail_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    ดูรายงานการแพทย์แม่นยำฉบับคนไข้ (Patient Edition)
    ความปลอดภัยเข้มงวด:
    - IDOR Prevention: ตรวจสอบว่ารายงานนี้เป็นของตนเองเท่านั้น (Pillar 2)
    - Pillar 15: ตรวจสอบว่ารายงานได้รับการอนุมัติแล้วเท่านั้น (ห้ามดูฉบับร่าง)
    """
    patient = request.portal_patient
    analysis = get_object_or_404(AnalysisRecord, pk=pk)

    # 1. IDOR Check: ห้ามดูรายงานของคนไข้คนอื่นเด็ดขาด!
    if analysis.patient_id != patient.pk:
        AuditLog.objects.create(
            action='SUSPICIOUS_IDOR_ATTEMPT',
            user=patient.user,
            model='AnalysisRecord',
            object_id=str(analysis.pk),
            client_ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            changes={'details': f"Patient {patient.hn} attempted to view Analysis #{analysis.pk} belonging to {analysis.patient.hn}"}
        )
        return HttpResponseForbidden("ไม่อนุญาตให้เข้าถึงรายงานของผู้ป่วยท่านอื่น")

    # 2. Status Check: แสดงเฉพาะรายงานที่แพทย์อนุมัติแล้วเท่านั้น
    if analysis.status not in ['approved', 'released']:
        raise Http404("รายงานนี้ยังอยู่ระหว่างการตรวจทานโดยแพทย์ ยังไม่เปิดให้คนไข้เข้าดู")

    # บันทึก AuditLog การเข้าดูรายงานของตนเอง
    AuditLog.objects.create(
        action='PATIENT_PORTAL_REPORT_VIEW',
        user=patient.user,
        model='AnalysisRecord',
        object_id=str(analysis.pk),
        client_ip=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        changes={'details': f"Patient {patient.hn} viewed approved report #{analysis.pk}"}
    )

    # คำนวณ Context สำหรับเรนเดอร์ในโหมด Patient Edition
    from clinical.reports import PrecisionReportGenerator
    context = PrecisionReportGenerator.get_report_context(analysis, edition='patient')

    return render(request, 'portal/portal_report_detail.html', {
        'patient': patient,
        'analysis': analysis,
        'report_context': context,
    })


@patient_portal_required
def portal_appointments_view(request: HttpRequest) -> HttpResponse:
    """ดูตารางนัดหมายทั้งหมดของผู้ป่วย"""
    patient = request.portal_patient
    appointments = patient.appointments.all().order_by('-appointment_date', '-appointment_time')

    return render(request, 'portal/portal_appointments.html', {
        'patient': patient,
        'appointments': appointments,
    })


@patient_portal_required
def portal_create_line_token_view(request: HttpRequest) -> HttpResponse:
    """สร้าง One-Time Token สำหรับเชื่อมต่อ LINE OA จากใน Portal"""
    patient = request.portal_patient

    token = PatientLinkingToken.create_token(
        patient=patient,
        action_type='line_binding',
        expires_in_minutes=30
    )

    bind_url = request.build_absolute_uri(
        reverse('portal_patient:line_binding_confirm') + f"?token={token.token}"
    )

    return render(request, 'portal/portal_line_binding.html', {
        'patient': patient,
        'token': token,
        'bind_url': bind_url,
    })
