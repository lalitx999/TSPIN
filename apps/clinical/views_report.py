"""
Views for Precision Medicine Reports, WeasyPrint PDF Generation, and Approval Workflow (EP 6).
Enforces Human-in-the-loop Sign-off (Pillar 15), RBAC 403 (Pillar 2), and Complete AuditLog (Pillar 8).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from accounts.decorators import clinical_staff_required
from accounts.models import AuditLog
from accounts.views import get_client_ip
from patients.models import Patient
from clinical.models import AnalysisRecord, BiologicalRecord
from clinical.reports import PrecisionReportGenerator
from clinical.services.report_generator import ReportGeneratorService


@clinical_staff_required
def report_dashboard_view(request):
    """
    ศูนย์รวมและแดชบอร์ดจัดการรายงานการแพทย์แม่นยำ (Precision Reports Dashboard)
    แสดงรายการรายงานทั้งหมด สถานะการลงนามแพทย์ และลิงก์ดาวน์โหลด PDF (พร้อมระบบแบ่งหน้า Paginator)
    """
    status_filter = request.GET.get('status', 'all')
    patient_id = request.GET.get('patient_id')

    queryset = AnalysisRecord.objects.select_related('patient', 'physician').all()

    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)
    if patient_id:
        queryset = queryset.filter(patient_id=patient_id)

    queryset = queryset.order_by('-analysis_date')
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    patients = Patient.objects.all().order_by('first_name')[:100]

    return render(request, 'clinical/reports/report_dashboard.html', {
        'page_obj': page_obj,
        'analyses': page_obj.object_list,
        'patients': patients,
        'status_filter': status_filter,
        'selected_patient_id': patient_id,
        'total_count': paginator.count,
        'approved_count': AnalysisRecord.objects.filter(status__in=['approved', 'released']).count(),
        'draft_count': AnalysisRecord.objects.filter(status='draft').count(),
    })


@clinical_staff_required
@require_http_methods(["GET", "POST"])
def report_create_view(request, patient_id):
    """
    สร้าง Snapshot รายงานการแพทย์แม่นยำฉบับใหม่จากข้อมูล 39 แกนของคนไข้
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    latest_bio = patient.biological_records.first()

    if not latest_bio:
        messages.error(request, f"ผู้ป่วย {patient.full_name} ยังไม่มีบันทึกคะแนน 39 แกนชีวภาพ กรุณาประเมินคะแนนก่อนออกรายงาน")
        return redirect('clinical:axes_explorer', patient_id=patient.pk)

    if request.method == 'POST':
        doctor_summary = request.POST.get('doctor_summary', '').strip()
        status = request.POST.get('status', 'draft')

        # แช่แข็งคะแนน 39 แกน ณ เวลาที่ออกรายงาน
        snapshot_scores = latest_bio.to_scores_dict()

        analysis = AnalysisRecord.objects.create(
            patient=patient,
            biological_record=latest_bio,
            physician=request.user,
            status=status,
            snapshot_scores=snapshot_scores,
            doctor_summary=doctor_summary,
            approved_at=timezone.now() if status in ['approved', 'released'] else None
        )

        AuditLog.objects.create(
            user=request.user,
            action="REPORT_SNAPSHOT_CREATED",
            model="AnalysisRecord",
            object_id=str(analysis.pk),
            changes={"patient_hn": patient.hn, "status": status},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )

        messages.success(request, f"สร้างรายงานการแพทย์แม่นยำสำหรับ {patient.full_name} เรียบร้อยแล้ว (สถานะ: {analysis.get_status_display()})")
        return redirect('clinical:report_preview', analysis_id=analysis.pk)

    return render(request, 'clinical/reports/report_create.html', {
        'patient': patient,
        'latest_bio': latest_bio,
    })


@clinical_staff_required
def report_preview_html_view(request, analysis_id):
    """
    เปิดดูตัวอย่างรายงานฉบับเต็มในรูปแบบ HTML ก่อนพิมพ์หรือดาวน์โหลด
    """
    analysis = get_object_or_404(AnalysisRecord.objects.select_related('patient', 'physician'), pk=analysis_id)
    edition = request.GET.get('edition', 'physician')

    AuditLog.objects.create(
        user=request.user,
        action="REPORT_HTML_PREVIEWED",
        model="AnalysisRecord",
        object_id=str(analysis.pk),
        changes={"patient_hn": analysis.patient.hn, "edition": edition},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    context = PrecisionReportGenerator.get_report_context(analysis, edition=edition)
    return render(request, 'clinical/reports/report_preview_wrapper.html', {
        'context': context,
        'analysis': analysis,
        'edition': edition,
    })


def report_download_pdf_view(request, analysis_id=None, pk=None):
    """
    เรนเดอร์และสตรีมไฟล์ PDF 300 DPI ผ่าน WeasyPrint
    ความปลอดภัย: อนุญาตเฉพาะบุคลากรทางการแพทย์ หรือคนไข้เจ้าของรายงาน (ฉบับอนุมัติแล้วเท่านั้น)
    """
    report_id = analysis_id or pk
    analysis = get_object_or_404(AnalysisRecord.objects.select_related('patient', 'physician'), pk=report_id)
    
    is_staff = request.user.is_authenticated and request.user.role in ['doctor', 'nurse', 'nursing_assistant', 'staff', 'admin']
    portal_patient_id = request.session.get('portal_patient_id')
    is_patient_owner = (
        (portal_patient_id and portal_patient_id == analysis.patient_id) or
        (request.user.is_authenticated and getattr(request.user, 'patient_record', None) and request.user.patient_record.pk == analysis.patient_id)
    )

    if not (is_staff or is_patient_owner):
        return HttpResponseForbidden("ไม่มีสิทธิ์เข้าถึงรายงานนี้")

    if is_patient_owner and not is_staff and analysis.status not in ['approved', 'released']:
        return HttpResponseForbidden("รายงานฉบับนี้ยังไม่ได้รับการอนุมัติโดยแพทย์")

    # ผู้ป่วยได้เฉพาะฉบับผู้ป่วย เปลี่ยน ?edition= เพื่อโหลดฉบับแพทย์ไม่ได้
    if is_staff:
        edition = request.GET.get('edition', 'physician').lower()
    else:
        edition = 'patient'

    # Option 2 Engine: Single Source of Truth CoreAnalysisPayload
    payload = ReportGeneratorService.payload_from_analysis_record(analysis)

    if edition == 'patient':
        pdf_bytes = ReportGeneratorService.generate_patient_pdf(payload)
    elif edition in ['omics', 'multiomics', 'multi_omics']:
        pdf_bytes = ReportGeneratorService.generate_multiomics_pdf(payload)
    else:
        pdf_bytes = ReportGeneratorService.generate_physician_pdf(payload)

    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action="REPORT_PDF_DOWNLOADED",
        model="AnalysisRecord",
        object_id=str(analysis.pk),
        changes={"patient_hn": analysis.patient.hn, "edition": edition, "pdf_size_bytes": len(pdf_bytes)},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    filename = f"TSPI_Report_{analysis.patient.hn}_{edition.upper()}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@clinical_staff_required
@require_http_methods(["POST"])
def report_signoff_action_view(request, analysis_id):
    """
    การลงนามอนุมัติ (Sign-off) และส่งมอบรายงานให้คนไข้ (Release to Patient)
    """
    analysis = get_object_or_404(AnalysisRecord, pk=analysis_id)
    action = request.POST.get('action')  # 'approve', 'release', 'revert'
    doctor_summary = request.POST.get('doctor_summary', '').strip()

    if doctor_summary:
        analysis.doctor_summary = doctor_summary

    if action == 'approve':
        analysis.status = 'approved'
        analysis.approved_at = timezone.now()
        analysis.physician = request.user
        analysis.save()

        AuditLog.objects.create(
            user=request.user,
            action="REPORT_CLINICALLY_APPROVED",
            model="AnalysisRecord",
            object_id=str(analysis.pk),
            changes={"patient_hn": analysis.patient.hn},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        messages.success(request, f"อนุมัติรายงาน #TSPI-{analysis.pk} ทางการแพทย์เรียบร้อยแล้ว (ปลดลายน้ำฉบับร่างออกแล้ว)")

    elif action == 'release':
        analysis.status = 'released'
        if not analysis.approved_at:
            analysis.approved_at = timezone.now()
        analysis.released_at = timezone.now()
        analysis.save()

        AuditLog.objects.create(
            user=request.user,
            action="REPORT_RELEASED_TO_PATIENT",
            model="AnalysisRecord",
            object_id=str(analysis.pk),
            changes={"patient_hn": analysis.patient.hn},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        messages.success(request, f"ส่งมอบรายงาน #TSPI-{analysis.pk} เข้าสู่พอร์ทัลคนไข้ (Patient Portal) สำเร็จ")

    elif action == 'revert':
        analysis.status = 'draft'
        analysis.approved_at = None
        analysis.released_at = None
        analysis.save()
        messages.warning(request, f"ปรับสถานะรายงาน #TSPI-{analysis.pk} กลับเป็นฉบับร่าง (Draft)")

    return redirect('clinical:report_preview', analysis_id=analysis.pk)
