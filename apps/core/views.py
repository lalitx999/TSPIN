from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection

def home(request):
    """
    Public Landing Page:
    - Hero Section with tagline
    - 3-Phase 9-Step Recovery Protocol Overview
    - 38 Biological Axes Living Network
    - Clinical Validation & Stats
    - Doctor & Clinic Credentials
    """
    return render(request, 'core/home.html')

def platform_view(request):
    """
    Platform Deep Dive:
    - 38 Mechanistic Biological Axes (Immune, Metabolic, Cellular, Endocrine, Digestive, etc.)
    - AI Diagnostic Engine & Scoring Logic
    - Digital Twin Physiological Framework
    """
    return render(request, 'core/platform.html')

def protocol_view(request):
    """
    9-Step Clinical Recovery Protocol:
    - Phase 1: Deep Assessment, Detoxification, Gut Restoration
    - Phase 2: Metabolic Reset, Hormonal Balance, Immune Modulation
    - Phase 3: Cellular Repair, Neuroplasticity, Longevity Protocol
    """
    return render(request, 'core/protocol.html')

def research_view(request):
    """
    Research & Clinical Evidence:
    - 200 Botanical & Nutritional Modules
    - Biomarker Correlation Matrix
    - Clinical Outcome Case Studies (e.g. Case Nikom Psoriasis Recovery)
    """
    return render(request, 'core/research.html')

def about(request):
    """About TSPI Clinic & Dr. Patt Systems Biology Precision Medicine"""
    return render(request, 'core/about.html')

def guide_view(request):
    """Patient & User Onboarding Guide (Step 01 - Step 06)"""
    return render(request, 'core/guide.html')

def install_view(request):
    """PWA Mobile & Desktop Web App Installation Guide (iOS, Android, Desktop)"""
    return render(request, 'core/install.html')

def privacy_policy(request):
    """PDPA Privacy Policy & Patient Consent Governance"""
    return render(request, 'core/privacy.html')

def terms_of_service(request):
    """Terms of Service"""
    return render(request, 'core/terms.html')

def health_check_view(request):
    """
    Production Healthcheck Endpoint (/health/ and /healthz/)
    Used by Docker, Kubernetes, and Cloud Load Balancers to verify container health.
    """
    health_status = {
        'status': 'healthy',
        'database': 'unknown',
        'service': 'tspi-clinical-emr',
        'version': '1.0.0',
    }

    try:
        connection.ensure_connection()
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
        return JsonResponse(health_status, status=503)

    return JsonResponse(health_status, status=200)
