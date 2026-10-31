"""
Views for AI Physician Assistant, Lab OCR, and Artifact Review Gates (EP 5).
Enforces SSE Streaming, RBAC (@clinical_staff_required), and Complete AuditLog (Pillar 8).
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from accounts.decorators import clinical_staff_required
from accounts.models import AuditLog
from accounts.views import get_client_ip
from patients.models import Patient
from clinical.models import BiologicalRecord
from intelligence.models import AIConsultationSession, AIConsultationMessage, AgenticArtifact
from intelligence.services import DeterministicLabParser, ClinicalCopilotEngine, ClinicalSafetyChecker


def _recently_updated_patients(limit: int = 5):
    """คนไข้ที่มีข้อมูลเข้าล่าสุด (รอบซักประวัติ LINE/เว็บ หรือบันทึก SOAP) เรียงจากใหม่ไปเก่า"""
    from django.db.models import Max
    from django.db.models.functions import Coalesce, Greatest
    from django.utils import timezone
    epoch = timezone.make_aware(timezone.datetime(2000, 1, 1))
    return list(
        Patient.objects
        .annotate(
            last_box=Coalesce(Max('intake_boxes__last_activity_at'), epoch),
            last_note=Coalesce(Max('histories__visit_date'), epoch),
        )
        .annotate(last_data=Greatest('last_box', 'last_note'))
        .filter(last_data__gt=epoch)
        .order_by('-last_data')[:limit]
    )


@clinical_staff_required
def ai_physician_view(request):
    """
    หน้าต่างห้องสนทนาผู้ช่วยแพทย์ AI Physician Assistant
    รองรับการปรึกษาเคสแบบเชื่อมโยงกับบริบท EMR และ 39 แกนชีววิทยา
    """
    patient_id = request.GET.get('patient_id')
    patient = None
    latest_record = None
    recent_patients = _recently_updated_patients(limit=5)
    auto_selected = False

    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id)
    elif recent_patients and request.GET.get('general') != '1':
        # เลือกคนไข้ล่าสุดที่มีข้อมูลเข้าให้ แต่ยังไม่วิเคราะห์จนกว่าแพทย์จะกดส่งคำถามเอง
        patient = recent_patients[0]
        auto_selected = True
    if patient:
        latest_record = patient.biological_records.first()

    # ดึงเซสชันล่าสุดของแพทย์สำหรับคนไข้รายนี้ หรือสร้างเซสชันใหม่
    session, _ = AIConsultationSession.objects.get_or_create(
        doctor=request.user,
        patient=patient,
        defaults={'title': f"ปรึกษาเคส: {patient.full_name if patient else 'ทั่วไป'}"}
    )

    past_messages = session.messages.all()

    # บันทึก AuditLog
    AuditLog.objects.create(
        user=request.user,
        action="AI_PHYSICIAN_VIEW",
        model="AIConsultationSession",
        object_id=str(session.pk),
        changes={"patient_hn": patient.hn if patient else None},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    return render(request, 'intelligence/ai_physician.html', {
        'patient': patient,
        'auto_selected': auto_selected,
        'recent_patients': recent_patients,
        'latest_record': latest_record,
        'session': session,
        'past_messages': past_messages,
    })


@clinical_staff_required
def ai_physician_stream_api(request):
    """
    Server-Sent Events (SSE) Streaming Endpoint สำหรับ AI Physician Copilot
    """
    query = request.GET.get('q', '').strip()
    session_id = request.GET.get('session_id')

    if not query:
        return JsonResponse({'error': 'Query required'}, status=400)

    session = get_object_or_404(AIConsultationSession, pk=session_id, doctor=request.user)
    patient = session.patient
    latest_record = patient.biological_records.first() if patient else None

    # บันทึกข้อความของผู้ใช้ (Doctor Query)
    AIConsultationMessage.objects.create(
        session=session,
        role='user',
        content=query
    )

    # บันทึก AuditLog
    AuditLog.objects.create(
        user=request.user,
        action="AI_QUERY_STREAMED",
        model="AIConsultationMessage",
        object_id=str(session.pk),
        changes={"query": query[:100], "patient_hn": patient.hn if patient else None},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    generator = ClinicalCopilotEngine.generate_streaming_consultation(
        query=query,
        patient=patient,
        latest_record=latest_record
    )

    response = StreamingHttpResponse(generator, content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@clinical_staff_required
def lab_ocr_view(request):
    """
    ระบบสแกนและสกัดค่าผลแล็บ (Lab OCR & Biomarker Value Extractor)
    คำนวณความเสี่ยงและส่งต่อผลลัพธ์เข้าสู่ Artifact Review Gate
    """
    patient_id = request.GET.get('patient_id')
    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id)

    parse_result = None
    sample_text = (
        "CBC and Chemistry Profile:\n"
        "Fasting Blood Sugar: 128 mg/dL\n"
        "HbA1c: 6.8 %\n"
        "hs-CRP: 3.4 mg/L\n"
        "Total Cholesterol: 245 mg/dL\n"
        "Triglycerides: 210 mg/dL\n"
        "LDL: 155 mg/dL\n"
        "SGPT (ALT): 48 U/L\n"
        "Creatinine: 1.1 mg/dL"
    )

    if request.method == 'POST':
        raw_text = request.POST.get('lab_text', '').strip()
        patient_pk = request.POST.get('patient_id')
        if patient_pk:
            patient = get_object_or_404(Patient, pk=patient_pk)

        if raw_text:
            parse_result = DeterministicLabParser.parse_text(raw_text)

            # ตรวจสอบการคลิกส่งเข้า Artifact Review
            if 'save_as_artifact' in request.POST and patient:
                safety_res = ClinicalSafetyChecker.verify_safety(patient, parse_result)
                artifact = AgenticArtifact.objects.create(
                    patient=patient,
                    doctor=request.user,
                    artifact_type='lab_extraction',
                    title=f"ผลสกัดแล็บอัตโนมัติ ({parse_result['abnormal_count']} ค่าผิดปกติ)",
                    proposed_data=parse_result,
                    safety_checks=safety_res,
                    status='pending'
                )

                AuditLog.objects.create(
                    user=request.user,
                    action="LAB_ARTIFACT_SUBMITTED",
                    model="AgenticArtifact",
                    object_id=str(artifact.pk),
                    changes={"patient_hn": patient.hn, "abnormal_count": parse_result['abnormal_count']},
                    client_ip=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )

                messages.success(request, "สร้างชิ้นงานผลแล็บสำเร็จ และส่งเข้าสู่ระบบตรวจทาน (Artifact Review Gate) แล้ว")
                return redirect('intelligence:artifact_review')

    return render(request, 'intelligence/lab_ocr.html', {
        'patient': patient,
        'parse_result': parse_result,
        'sample_text': sample_text,
    })


@clinical_staff_required
def artifact_review_view(request):
    """
    หน้าจอตรวจทานผลวิเคราะห์ AI (Artifact Review Gate - Pillar 15)
    แพทย์ต้องเป็นผู้ลงนามอนุมัติ (Approve) ก่อนที่ข้อมูลจะถูกนำไปปรับปรุงในเวชระเบียนจริง
    """
    patient_id = request.GET.get('patient_id')
    status_filter = request.GET.get('status', 'pending')

    queryset = AgenticArtifact.objects.all()
    if patient_id:
        queryset = queryset.filter(patient_id=patient_id)
    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    artifacts = queryset.order_by('-created_at')[:30]

    return render(request, 'intelligence/artifact_review.html', {
        'artifacts': artifacts,
        'status_filter': status_filter,
        'pending_count': AgenticArtifact.objects.filter(status='pending').count(),
    })


@clinical_staff_required
@require_http_methods(["POST"])
def artifact_action_view(request, artifact_id):
    """
    การอนุมัติหรือปฏิเสธชิ้นงาน AI โดยแพทย์ผู้รักษา (Physician Sign-Off Gate)
    """
    artifact = get_object_or_404(AgenticArtifact, pk=artifact_id)
    action = request.POST.get('action')  # 'approve' or 'reject'
    doctor_notes = request.POST.get('doctor_notes', '').strip()

    artifact.doctor = request.user
    artifact.doctor_notes = doctor_notes
    artifact.reviewed_at = timezone.now()

    if action == 'approve':
        artifact.status = 'approved'
        artifact.save()

        # หากเป็นผลแล็บที่มีคะแนนแกนชีวภาพ ให้บันทึกอัปเดตเข้า BiologicalRecord ของคนไข้จริง
        affected_scores = artifact.proposed_data.get('affected_axes_scores', {})
        if affected_scores:
            record = artifact.patient.biological_records.first()
            if not record:
                record = BiologicalRecord.objects.create(patient=artifact.patient, doctor=request.user)

            for ax_id, score in affected_scores.items():
                if 1 <= int(ax_id) <= 39:
                    setattr(record, f'axis_{ax_id}', score)
            record.notes = f"อัปเดตผลลัพธ์จาก Artifact #{artifact.pk}: {doctor_notes}"
            record.save()

        AuditLog.objects.create(
            user=request.user,
            action="ARTIFACT_APPROVED_BY_PHYSICIAN",
            model="AgenticArtifact",
            object_id=str(artifact.pk),
            changes={"status": "approved", "patient_hn": artifact.patient.hn},
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )

        messages.success(request, f"อนุมัติ Artifact #{artifact.pk} และนำผลลัพธ์เข้าสู่แฟ้มเวชระเบียนของ {artifact.patient.full_name} แล้ว")

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

        messages.warning(request, f"ปฏิเสธ Artifact #{artifact.pk} เรียบร้อยแล้ว (ไม่นำเข้าสู่เวชระเบียน)")

    return redirect('intelligence:artifact_review')
