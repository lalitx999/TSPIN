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

    # ดึงบริบท SOAP, สัญญาณชีพ, แล็บชีวเคมี และ 39 แกนชีววิทยา
    latest_soap = None
    latest_vitals = {}
    dysfunctional_axes = []
    patient_labs = []

    if patient:
        latest_soap = patient.histories.filter(is_deleted=False).order_by('-visit_date', '-id').first()
        if latest_soap and isinstance(latest_soap.vitals, dict):
            latest_vitals = latest_soap.vitals

        if latest_record:
            from clinical.invariants import CANONICAL_39_AXES
            for item in latest_record.get_dysfunctional_axes(threshold=60):
                dysfunctional_axes.append({
                    'axis_id': item['axis_id'],
                    'name': CANONICAL_39_AXES.get(item['axis_id'], f"Axis {item['axis_id']}"),
                    'score': item['score']
                })

        from intelligence.models import AgenticArtifact
        lab_art = AgenticArtifact.objects.filter(
            patient=patient,
            artifact_type='lab_extraction'
        ).order_by('-created_at').first()
        if lab_art and isinstance(lab_art.proposed_data, dict):
            data = lab_art.proposed_data
            markers = data.get('extracted_biomarkers', data) if isinstance(data, dict) else {}
            for k, m in markers.items():
                if isinstance(m, dict) and 'value' in m:
                    patient_labs.append(m)
        elif patient.extra_data and isinstance(patient.extra_data.get('biomarkers'), dict):
            for k, m in patient.extra_data['biomarkers'].items():
                if isinstance(m, dict) and 'value' in m:
                    patient_labs.append(m)

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
        'latest_soap': latest_soap,
        'latest_vitals': latest_vitals,
        'dysfunctional_axes': dysfunctional_axes,
        'patient_labs': patient_labs,
        'session': session,
        'past_messages': past_messages,
        'prefill': request.GET.get('prefill', '').strip(),
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
    ระบบสแกนและสกัดค่าผลแล็บถูกย้ายรวมเข้าหน้า 'ตรวจทานผลแล็บ (Lab Review)' แบบ Modal แล้ว
    หากเข้าผ่าน GET จะนำทางไปที่หน้า Lab Review พร้อมเปิด Modal ให้โดยอัตโนมัติ
    """
    patient_id = request.GET.get('patient_id')
    if request.method == 'GET':
        from django.urls import reverse
        url = reverse('patients:doctor_lab_review')
        params = ['open_upload=1']
        if patient_id and str(patient_id).isdigit():
            params.append(f"patient_id={patient_id}")
        return redirect(f"{url}?{'&'.join(params)}")

    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id)

    parse_result = None
    sample_text = ""

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
    ศูนย์ตรวจทานข้อเสนอ AI และประวัติลงนามแพทย์ (Artifact Review Gate - Pillar 15)
    รองรับการค้นหาคนไข้ กรองประเภทชิ้นงาน และแสดงผลโครงสร้างทางคลินิกโดยไม่แสดง JSON ดิบ
    """
    from django.db.models import Q
    from clinical.invariants import CANONICAL_39_AXES

    patient_id = request.GET.get('patient_id')
    status_filter = request.GET.get('status', 'pending')
    type_filter = request.GET.get('type', 'all')
    q = request.GET.get('q', '').strip()

    queryset = AgenticArtifact.objects.select_related('patient', 'doctor').all()
    if patient_id and str(patient_id).isdigit():
        queryset = queryset.filter(patient_id=patient_id)
    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)
    if type_filter in ('lab_extraction', 'axis_recommendation', 'therapeutic_plan'):
        queryset = queryset.filter(artifact_type=type_filter)
    if q:
        queryset = queryset.filter(
            Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__hn__icontains=q)
            | Q(title__icontains=q)
        )

    artifacts = list(queryset.order_by('-created_at')[:30])
    for art in artifacts:
        data = art.proposed_data if isinstance(art.proposed_data, dict) else {}
        axes_scores = data.get('affected_axes_scores') or data.get('suggested_scores') or {}
        resolved_axes = []
        if isinstance(axes_scores, dict):
            for ax_id_raw, sc in axes_scores.items():
                try:
                    ax_id = int(ax_id_raw)
                    resolved_axes.append({
                        'axis_id': ax_id,
                        'name': CANONICAL_39_AXES.get(ax_id, f"Axis {ax_id}"),
                        'score': int(sc),
                    })
                except (TypeError, ValueError):
                    continue
        resolved_axes.sort(key=lambda x: x['score'], reverse=True)
        art.resolved_axes = resolved_axes
        art.resolved_modules = data.get('recommended_modules') or []
        art.resolved_rules = data.get('triggered_rules') or []
        art.resolved_phases = data.get('priority_phases') or []
        art.resolved_docs = data.get('documents') or []

    return render(request, 'intelligence/artifact_review.html', {
        'artifacts': artifacts,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'q': q,
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

        data = artifact.proposed_data if isinstance(artifact.proposed_data, dict) else {}
        affected_scores = data.get('affected_axes_scores') or data.get('suggested_scores') or {}
        if isinstance(affected_scores, dict) and affected_scores:
            record = artifact.patient.biological_records.first()
            if not record:
                record = BiologicalRecord.objects.create(patient=artifact.patient, doctor=request.user)

            for ax_id, score in affected_scores.items():
                try:
                    ax_num = int(ax_id)
                    if 1 <= ax_num <= 39:
                        setattr(record, f'axis_{ax_num}', int(score))
                except (TypeError, ValueError):
                    continue
            record.notes = f"อัปเดตผลลัพธ์จาก Artifact #{artifact.pk}: {doctor_notes}"
            record.save()

        # อัปเดตผลแล็บ / แผนบำบัดเข้าแฟ้มเวชระเบียนของคนไข้
        patient = artifact.patient
        changed_extra = False
        markers = data.get('extracted_biomarkers')
        if isinstance(markers, dict) and markers:
            if not isinstance(patient.extra_data, dict):
                patient.extra_data = {}
            bio = patient.extra_data.get('biomarkers')
            if not isinstance(bio, dict):
                bio = {}
            bio.update(markers)
            patient.extra_data['biomarkers'] = bio
            patient.extra_data['latest_lab_date'] = timezone.now().isoformat()
            changed_extra = True

        modules = data.get('recommended_modules')
        if isinstance(modules, list) and modules:
            if not isinstance(patient.extra_data, dict):
                patient.extra_data = {}
            protocols = patient.extra_data.get('approved_protocols')
            if not isinstance(protocols, list):
                protocols = []
            protocols.insert(0, {
                'artifact_id': artifact.pk,
                'title': artifact.title,
                'modules': [m.get('code') for m in modules if isinstance(m, dict)],
                'approved_at': timezone.now().isoformat(),
                'doctor_notes': doctor_notes,
            })
            patient.extra_data['approved_protocols'] = protocols[:10]
            changed_extra = True

        if changed_extra:
            patient.save(update_fields=['extra_data'])

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
