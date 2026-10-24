"""
Patient Portal Views for TSPI Health (Pillars 1, 8, 14).
Clean Medical UI, Zero 404s, Full Legacy Feature Parity.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from clinical.models import AnalysisRecord
from patients.models import Patient, Appointment


@login_required
def patient_dashboard(request):
    """
    หน้าหลักคนไข้ (Patient Dashboard)
    """
    return render(request, 'portal_patient/dashboard.html', {
        'patient': request.user,
    })


@login_required
def patient_ai_intake(request):
    """
    ซักประวัติอาการกับ AI (AI Anamnesis Intake)
    """
    return render(request, 'portal_patient/ai_intake.html', {
        'patient': request.user,
    })


@login_required
def patient_checkin(request, session_id=None):
    """
    เช็คอินก่อนเข้าตรวจ (Pre-appointment Check-in)
    """
    return render(request, 'portal_patient/checkin.html', {
        'patient': request.user,
        'session_id': session_id,
    })


@login_required
def patient_axes_result(request):
    """
    ผลวิเคราะห์คะแนน 38 แกนชีววิทยาของคนไข้
    """
    # Sample scores for presentation
    axes_data = [
        {"code": "A01", "name": "Systemic Inflammatory Load", "score": 78, "status": "critical", "desc": "ภาระการอักเสบสูงกว่าปกติ ควรลดอาหารแปรรูปและเสริมสารต้านการอักเสบ"},
        {"code": "A05", "name": "Glucose-Insulin Regulation", "score": 64, "status": "warning", "desc": "ระดับความไวต่ออินซูลินเริ่มลดลง ควรควบคุมคาร์โบไฮเดรตเชิงเดี่ยว"},
        {"code": "A08", "name": "Mitochondrial Function", "score": 42, "status": "normal", "desc": "การผลิตพลังงานระดับเซลล์อยู่ในเกณฑ์เสถียร"},
        {"code": "A16", "name": "Hepatic Detoxification", "score": 70, "status": "warning", "desc": "ภาระการขับสารพิษของตับสูง ควรเน้นสารสกัดบำรุงตับ Phase 1/2"},
        {"code": "A19", "name": "Gut Barrier Integrity", "score": 82, "status": "critical", "desc": "พบสัญญาณภาวะเยื่อบุลำไส้รั่ว (Leaky Gut) ควรฟื้นฟูเยื่อบุทางเดินอาหาร"},
    ]
    return render(request, 'portal_patient/axes_result.html', {
        'patient': request.user,
        'axes_data': axes_data,
    })


@login_required
def patient_digital_twin(request):
    """
    แบบจำลองสรีรวิทยา Digital Twin ส่วนบุคคล
    """
    return render(request, 'portal_patient/digital_twin.html', {
        'patient': request.user,
    })


@login_required
def patient_history(request):
    """
    ประวัติการรักษาและไทม์ไลน์สุขภาพ
    """
    return render(request, 'portal_patient/history.html', {
        'patient': request.user,
    })


@login_required
def patient_download(request):
    """
    ดาวน์โหลดรายงานผลตรวจสุขภาพและ Precision Report
    """
    reports = AnalysisRecord.objects.all().order_by('-analysis_date')[:10]
    return render(request, 'portal_patient/download.html', {
        'patient': request.user,
        'reports': reports,
    })


@login_required
def patient_rewards(request):
    """
    คะแนนความสม่ำเสมอในการดูแลสุขภาพ (Adherence Score)
    """
    return render(request, 'portal_patient/rewards.html', {
        'patient': request.user,
    })


@login_required
def patient_settings(request):
    """
    ตั้งค่าข้อมูลส่วนตัวและการยินยอม (Consent)
    """
    return render(request, 'portal_patient/settings.html', {
        'patient': request.user,
    })


@login_required
def patient_consent(request):
    """
    หนังสือยินยอมรับการรักษาและข้อตกลงคุ้มครองข้อมูล PDPA
    """
    return render(request, 'portal_patient/consent.html', {
        'patient': request.user,
    })
