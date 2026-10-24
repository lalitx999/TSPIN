from django.shortcuts import render

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
