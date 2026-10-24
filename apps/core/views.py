from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection

def home(request):
    """Public Landing Page (Hero section, Services, Overview)"""
    return render(request, 'core/home.html')

def about(request):
    """About TSPI Clinic & Mechanistic Medicine"""
    return render(request, 'core/about.html')

def privacy_policy(request):
    """PDPA Privacy Policy"""
    return render(request, 'core/privacy.html')

def terms_of_service(request):
    """Terms of Service"""
    return render(request, 'core/terms.html')

def health_check_view(request):
    """
    Production Healthcheck Endpoint (/health/)
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

