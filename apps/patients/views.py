from django.shortcuts import render
from accounts.decorators import clinical_staff_required

@clinical_staff_required
def doctor_dashboard(request):
    """
    หน้าหลักคลินิกสำหรับแพทย์และเจ้าหน้าที่ (Doctor Dashboard)
    """
    return render(request, 'patients/dashboard.html', {
        'doctor': request.user,
    })
