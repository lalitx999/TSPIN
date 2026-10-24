from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def patient_dashboard(request):
    """
    หน้าหลักคนไข้ (Patient Dashboard)
    """
    return render(request, 'portal_patient/dashboard.html', {
        'patient': request.user,
    })
