"""
Views for TSPI 39 Biological Axes Framework & Visualizer (EP 4).
Enforces RBAC (@clinical_staff_required), AuditLog (Pillar 8), and Chart.js Topology.
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from accounts.decorators import clinical_staff_required
from accounts.models import AuditLog
from accounts.views import get_client_ip
from patients.models import Patient
from clinical.models import BiologicalRecord, AnalysisRecord
from clinical.forms import BiologicalRecordForm
from clinical.engine import TspiClinicalEngine


@clinical_staff_required
def axes_explorer_view(request):
    """
    หน้ารวมและสำรวจทั้ง 39 แกนชีววิทยา (Mechanistic Biological Axes Explorer)
    จัดกลุ่มตาม 12 Domains พร้อมข้อมูล Sub-axes A, B, C และกลไกระดับเซลล์
    """
    patient_id = request.GET.get('patient_id')
    patient = None
    latest_record = None
    form = None
    scores_dict = {}

    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id)
        latest_record = patient.biological_records.first()

        if request.method == 'POST':
            if latest_record:
                form = BiologicalRecordForm(request.POST, instance=latest_record)
            else:
                form = BiologicalRecordForm(request.POST)

            if form.is_valid():
                record = form.save(commit=False)
                record.patient = patient
                record.doctor = request.user
                record.save()

                AuditLog.objects.create(
                    user=request.user,
                    action="BIOLOGICAL_AXES_UPDATED",
                    model="BiologicalRecord",
                    object_id=str(record.pk),
                    changes={"patient_hn": patient.hn, "is_baseline": record.is_baseline},
                    client_ip=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )

                messages.success(request, f"บันทึกคะแนน 39 แกนชีววิทยาของ {patient.full_name} เรียบร้อยแล้ว")
                return redirect(f"{request.path}?patient_id={patient.pk}")
        else:
            if latest_record:
                form = BiologicalRecordForm(instance=latest_record)
                scores_dict = latest_record.to_scores_dict()
            else:
                form = BiologicalRecordForm()
                scores_dict = {i: 50 for i in range(1, 40)}

    domains = TspiClinicalEngine.get_domains_with_axes()
    all_axes = TspiClinicalEngine.get_all_axes()

    # วิเคราะห์แกนที่มีคะแนนวิกฤต (>= 60)
    dysfunctional_axes = []
    recommendations = []
    if scores_dict:
        for ax in all_axes:
            ax_id = ax.get('axis_id')
            score = scores_dict.get(ax_id, 50)
            if score >= 60:
                dysfunctional_axes.append({
                    'axis_id': ax_id,
                    'name': ax.get('name'),
                    'domain_title': ax.get('domain_title'),
                    'score': score
                })
        dysfunctional_axes = sorted(dysfunctional_axes, key=lambda x: x['score'], reverse=True)
        recommendations = TspiClinicalEngine.match_therapeutic_recommendations(dysfunctional_axes, limit=4)

    return render(request, 'clinical/axes_explorer.html', {
        'patient': patient,
        'latest_record': latest_record,
        'form': form,
        'domains': domains,
        'all_axes': all_axes,
        'scores_dict': scores_dict,
        'dysfunctional_axes': dysfunctional_axes,
        'recommendations': recommendations,
    })


@clinical_staff_required
def axis_graph_view(request):
    """
    แผนผังเรดาร์ชีวภาพและโทโพโลยี (Radar & Network Topology Visualizer)
    รองรับการเปรียบเทียบ Baseline vs ค่าตรวจล่าสุด
    """
    patient_id = request.GET.get('patient_id')
    patient = None
    baseline_record = None
    latest_record = None

    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id)
        latest_record = patient.biological_records.first()
        baseline_record = patient.biological_records.filter(is_baseline=True).first()

    all_axes = TspiClinicalEngine.get_all_axes()
    axis_labels = [f"Axis {ax.get('axis_id')}: {ax.get('name')}" for ax in all_axes]

    # ค่าคะแนนสำหรับเรดาร์ชาร์ต (39 แกน)
    if latest_record:
        latest_scores = latest_record.to_radar_list()
    else:
        latest_scores = [None] * 39

    if baseline_record:
        baseline_scores = baseline_record.to_radar_list()
    else:
        baseline_scores = [None] * 39

    # ข้อมูลเรดาร์ 12 โดเมน
    scores_dict = latest_record.to_scores_dict() if latest_record else {i: None for i in range(1, 40)}
    domain_data = TspiClinicalEngine.calculate_domain_scores(scores_dict)
    domain_labels = [d['title'] for d in domain_data]
    domain_scores = [d['average_score'] for d in domain_data]

    # บันทึก AuditLog
    AuditLog.objects.create(
        user=request.user,
        action="AXIS_GRAPH_VIEW",
        model="BiologicalRecord",
        object_id=str(patient.pk) if patient else "GENERAL",
        changes={"view": "RADAR_TOPOLOGY"},
        client_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    return render(request, 'clinical/axis_graph.html', {
        'patient': patient,
        'latest_record': latest_record,
        'baseline_record': baseline_record,
        'axis_labels_json': json.dumps(axis_labels, ensure_ascii=False),
        'latest_scores_json': json.dumps(latest_scores),
        'baseline_scores_json': json.dumps(baseline_scores),
        'domain_labels_json': json.dumps(domain_labels, ensure_ascii=False),
        'domain_scores_json': json.dumps(domain_scores),
        'domain_data': domain_data,
    })


@clinical_staff_required
def axis_timeline_view(request):
    """
    เส้นเวลาสุขภาพ (Timeline Tracking) ติดตามพัฒนาการของคะแนนแต่ละแกนเมื่อเวลาผ่านไป
    """
    patient_id = request.GET.get('patient_id')
    patient = None
    records = []

    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id)
        records = patient.biological_records.all().order_by('record_date')

    timeline_dates = [r.record_date.strftime('%d/%m/%Y') for r in records]
    
    # ดึงค่าของแกนหลัก 4 แกนสำคัญเพื่อพล็อตไทม์ไลน์
    axis_1_trend = [r.axis_1 for r in records]  # Systemic Inflammation
    axis_5_trend = [r.axis_5 for r in records]  # Glucose-Insulin
    axis_8_trend = [r.axis_8 for r in records]  # Mitochondrial
    axis_15_trend = [r.axis_15 for r in records] # Detoxification

    return render(request, 'clinical/axis_timeline.html', {
        'patient': patient,
        'records': records,
        'timeline_dates_json': json.dumps(timeline_dates),
        'axis_1_trend_json': json.dumps(axis_1_trend),
        'axis_5_trend_json': json.dumps(axis_5_trend),
        'axis_8_trend_json': json.dumps(axis_8_trend),
        'axis_15_trend_json': json.dumps(axis_15_trend),
    })


@clinical_staff_required
def therapeutic_matrix_view(request):
    """
    เมทริกซ์การรักษา (Therapeutic Matrix Explorer)
    สำรวจ 200 โมดูลสารอาหารและสารพฤกษเคมีบำบัด พร้อมกลไกการออกฤทธิ์
    """
    search_q = request.GET.get('q', '').strip().lower()
    selected_axis = request.GET.get('axis', '').strip()
    
    modules = TspiClinicalEngine.get_modules_data()

    if search_q:
        modules = [
            m for m in modules
            if search_q in m.get('name', '').lower()
            or search_q in m.get('code', '').lower()
            or search_q in m.get('description', '').lower()
        ]

    if selected_axis and selected_axis.isdigit():
        target_ax = int(selected_axis)
        modules = [
            m for m in modules
            if target_ax in (m.get('axes') or [])
            or any(f"AXIS_{target_ax}" in str(a) for a in (m.get('axes') or []))
        ]

    all_axes = TspiClinicalEngine.get_all_axes()

    return render(request, 'clinical/therapeutic_matrix.html', {
        'modules': modules[:60],  # แสดง 60 โมดูลแรกเพื่อความรวดเร็ว
        'total_modules_count': len(modules),
        'search_q': search_q,
        'selected_axis': selected_axis,
        'all_axes': all_axes,
    })


@clinical_staff_required
@require_http_methods(["POST"])
def update_axis_score_htmx(request, patient_id):
    """
    อัปเดตคะแนนแกนชีวภาพรายแกนแบบทันทีผ่าน HTMX Slider/Input
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    axis_id = request.POST.get('axis_id')
    score = request.POST.get('score')

    if not axis_id or not score or not axis_id.isdigit() or not score.isdigit():
        return render(request, 'clinical/partials/score_badge.html', {'error': 'Invalid parameters'})

    axis_id = int(axis_id)
    score = int(score)
    if not (1 <= axis_id <= 39) or not (0 <= score <= 100):
        return render(request, 'clinical/partials/score_badge.html', {'error': 'Out of range'})

    record = patient.biological_records.first()
    if not record:
        record = BiologicalRecord.objects.create(patient=patient, doctor=request.user)

    setattr(record, f'axis_{axis_id}', score)
    record.save()

    return render(request, 'clinical/partials/score_badge.html', {
        'axis_id': axis_id,
        'score': score
    })
