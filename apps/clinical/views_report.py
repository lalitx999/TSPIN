"""
Views for Precision Medicine Reports, WeasyPrint PDF Generation, and Approval Workflow (EP 6).
Enforces Human-in-the-loop Sign-off (Pillar 15), RBAC 403 (Pillar 2), and Complete AuditLog (Pillar 8).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.views.decorators.clickjacking import xframe_options_sameorigin
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
from clinical.services.report_ai import PrecisionReportAIWriter
from clinical.invariants import ClinicalInvariantValidator


@clinical_staff_required
def report_dashboard_view(request):
    """
    ศูนย์รวมและแดชบอร์ดจัดการรายงานการแพทย์แม่นยำ (Precision Reports Dashboard)
    แสดงรายการรายงานทั้งหมด สถานะการลงนามแพทย์ และลิงก์ดู/ดาวน์โหลดครบทั้ง 3 ฉบับ (แพทย์ / คนไข้ / Multi-Omics)
    """
    status_filter = request.GET.get('status', 'all')
    patient_id = request.GET.get('patient_id')
    q = request.GET.get('q', '').strip()

    queryset = AnalysisRecord.objects.select_related('patient', 'physician').all()

    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)
    if patient_id and str(patient_id).isdigit():
        queryset = queryset.filter(patient_id=patient_id)
    if q:
        queryset = queryset.filter(
            Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__hn__icontains=q)
        )

    queryset = queryset.order_by('-analysis_date')
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    recent_patients = Patient.objects.filter(is_deleted=False).order_by('-created_at')[:6]

    return render(request, 'clinical/reports/report_dashboard.html', {
        'page_obj': page_obj,
        'analyses': page_obj.object_list,
        'recent_patients': recent_patients,
        'q': q,
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
    สร้าง Snapshot รายงานการแพทย์แม่นยำ 3 ฉบับ (Physician, Patient, Multi-Omics)
    ดึงข้อมูล SOAP, Vitals, Labs, 39 แกน และ Omics อัตโนมัติ พร้อมให้ AI เขียนบทวิเคราะห์
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    latest_bio = patient.biological_records.first()

    if not latest_bio:
        messages.error(request, f"ผู้ป่วย {patient.full_name} ยังไม่มีบันทึกคะแนน 39 แกนชีวภาพ กรุณาประเมินคะแนนก่อนออกรายงาน")
        return redirect(f"{reverse('clinical:axes_explorer')}?patient_id={patient.pk}")

    snapshot_scores = latest_bio.to_scores_dict()
    clinical_snap = PrecisionReportAIWriter.extract_patient_clinical_snapshot(patient, snapshot_scores)

    if request.method == 'POST':
        doctor_summary = request.POST.get('doctor_summary', '').strip()
        status = request.POST.get('status', 'draft')
        use_ai = request.POST.get('use_ai', '1') == '1'

        ai_editions = {}
        if use_ai:
            ai_editions = PrecisionReportAIWriter.compose_three_editions(
                patient=patient,
                scores_dict=snapshot_scores,
                doctor_summary=doctor_summary,
                use_ai=True,
            )

        therapeutic_plan = [
            {'code': m.get('code'), 'name': m.get('name')}
            for m in clinical_snap.get('matched_modules', [])
        ]

        analysis = AnalysisRecord.objects.create(
            patient=patient,
            biological_record=latest_bio,
            physician=request.user,
            status=status,
            snapshot_scores=snapshot_scores,
            key_findings=[
                {'axis_id': ax['axis_id'], 'name': ax['name'], 'score': ax['score']}
                for ax in clinical_snap.get('dysfunctional_axes', [])[:10]
            ],
            therapeutic_plan=therapeutic_plan,
            doctor_summary=doctor_summary,
            ai_editions_json=ai_editions,
            approved_at=timezone.now() if status in ['approved', 'released'] else None
        )

        AuditLog.objects.create(
            user=request.user,
            action="REPORT_SNAPSHOT_CREATED",
            model="AnalysisRecord",
            object_id=str(analysis.pk),
            changes={
                "patient_hn": patient.hn,
                "status": status,
                "ai_generated_by": ai_editions.get('generated_by', 'none'),
                "omics_available": ai_editions.get('omics_available', False),
            },
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )

        messages.success(request, f"สร้างรายงานการแพทย์แม่นยำ 3 ฉบับสำหรับ {patient.full_name} เรียบร้อยแล้ว")
        return redirect('clinical:report_preview', analysis_id=analysis.pk)

    return render(request, 'clinical/reports/report_create.html', {
        'patient': patient,
        'latest_bio': latest_bio,
        'snap': clinical_snap,
    })


@clinical_staff_required
def report_preview_html_view(request, analysis_id):
    """
    เปิดดูตัวอย่างรายงานฉบับเต็มทั้ง 3 ฉบับ (Physician / Patient / Multi-Omics) ที่ตรงกับ PDF 100%
    พร้อมเครื่องมือให้ AI เขียนใหม่ หรือแก้ไขข้อความก่อนลงนามอนุมัติ
    """
    analysis = get_object_or_404(AnalysisRecord.objects.select_related('patient', 'physician'), pk=analysis_id)
    edition = request.GET.get('edition', 'physician').lower()
    if edition not in ('physician', 'patient', 'omics', 'multiomics'):
        edition = 'physician'
    ed_key = 'multiomics' if edition in ('omics', 'multiomics') else edition

    AuditLog.objects.create(
        user=request.user,
        action="REPORT_HTML_PREVIEWED",
        model="AnalysisRecord",
        object_id=str(analysis.pk),
        changes={"patient_hn": analysis.patient.hn, "edition": ed_key},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    editions = analysis.ai_editions_json if isinstance(analysis.ai_editions_json, dict) else {}
    active_chapters = editions.get(ed_key) or []

    return render(request, 'clinical/reports/report_preview_wrapper.html', {
        'analysis': analysis,
        'edition': edition,
        'ed_key': ed_key,
        'active_chapters': active_chapters,
        'has_ai_editions': bool(editions.get('physician') or editions.get('patient') or editions.get('multiomics')),
        'omics_available': bool(editions.get('omics_available')),
        'generated_by': editions.get('generated_by', ''),
    })


@clinical_staff_required
@xframe_options_sameorigin
def report_raw_html_view(request, analysis_id):
    """
    เรนเดอร์ HTML ฉบับจริงที่ตรงกับ WeasyPrint PDF 100% สำหรับแสดงใน Iframe Preview
    """
    analysis = get_object_or_404(AnalysisRecord.objects.select_related('patient', 'physician'), pk=analysis_id)
    edition = request.GET.get('edition', 'physician').lower()
    html_str = ReportGeneratorService.render_html_for_edition(analysis, edition=edition)
    return HttpResponse(html_str)


@clinical_staff_required
@require_http_methods(["POST"])
def report_ai_generate_action(request, analysis_id):
    """
    สั่ง AI เขียน/ปรับปรุงบทวิเคราะห์ 3 ฉบับใหม่ หรือบันทึกการแก้ไขข้อความของแพทย์
    (ล็อกห้ามแก้ไขหากรายงานได้รับอนุมัติหรือส่งมอบแล้ว เพื่อคงความ Immutable ตาม Pillar 8)
    """
    analysis = get_object_or_404(AnalysisRecord.objects.select_related('patient'), pk=analysis_id)
    edition = request.POST.get('edition', 'physician').lower()
    ed_key = 'multiomics' if edition in ('omics', 'multiomics') else edition
    action = request.POST.get('action', 'regenerate')

    if analysis.status in ('approved', 'released'):
        messages.warning(request, "รายงานฉบับนี้ได้รับการอนุมัติแล้ว กรุณาปรับกลับเป็น Draft ก่อนแก้ไขเนื้อหา")
        return redirect(f"{request.META.get('HTTP_REFERER') or '/clinical/reports/'}")

    if action == 'regenerate':
        raw_scores = analysis.snapshot_scores or {}
        scores_dict = {i: None for i in range(1, 40)}
        for k, v in raw_scores.items():
            try:
                scores_dict[int(k)] = int(v) if v is not None else None
            except (TypeError, ValueError):
                continue

        ai_editions = PrecisionReportAIWriter.compose_three_editions(
            patient=analysis.patient,
            scores_dict=scores_dict,
            doctor_summary=analysis.doctor_summary or "",
            use_ai=True,
        )
        analysis.ai_editions_json = ai_editions
        analysis.save(update_fields=['ai_editions_json'])
        messages.success(request, "AI ได้เขียนเนื้อหารายงานทั้ง 3 ฉบับ (แพทย์ / คนไข้ / Multi-Omics) เรียบร้อยแล้ว")

    elif action == 'save_edits':
        editions = dict(analysis.ai_editions_json or {})
        chapters = list(editions.get(ed_key) or [])
        updated_chapters = []
        for idx, ch in enumerate(chapters):
            title = request.POST.get(f'chapter_title_{idx}', ch.get('title', '')).strip()
            content = request.POST.get(f'chapter_content_{idx}', ch.get('content', '')).strip()
            if ed_key == 'patient':
                title = ClinicalInvariantValidator.sanitize_patient_prose(title)
                content = ClinicalInvariantValidator.sanitize_patient_prose(content)
            updated_chapters.append({'title': title, 'content': content})
        editions[ed_key] = updated_chapters
        analysis.ai_editions_json = editions
        analysis.save(update_fields=['ai_editions_json'])
        messages.success(request, f"บันทึกการแก้ไขเนื้อหาฉบับ {ed_key.upper()} เรียบร้อยแล้ว")

    from django.urls import reverse
    return redirect(f"{reverse('clinical:report_preview', args=[analysis.pk])}?edition={edition}")


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
