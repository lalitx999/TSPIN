"""
Role-Based Authorization Decorators (Pillar 2).
Enforces Strict Access Control without trusting client state.
"""

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import AuditLog

def role_required(*allowed_roles):
    """
    Decorator ตรวจสอบว่าผู้ใช้งานที่ล็อกอินมี Role ตรงตามที่ระบุหรือไม่
    หากไม่มีสิทธิ์ จะปฏิเสธการเข้าถึง (HTTP 403 Forbidden) และบันทึก AuditLog
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "กรุณาเข้าสู่ระบบก่อนเข้าใช้งาน")
                return redirect('accounts:doctor_login')
                
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                # ⚠️ บันทึกความพยายามเข้าถึงทรัพยากรข้ามสิทธิ์ (Privilege Escalation Attempt)
                AuditLog.objects.create(
                    user=request.user,
                    action="UNAUTHORIZED_ROLE_ACCESS_DENIED",
                    model="View",
                    object_id=view_func.__name__,
                    changes={"attempted_role": request.user.role, "required_roles": list(allowed_roles)},
                    client_ip=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
                raise PermissionDenied("คุณไม่มีสิทธิ์ในการเข้าถึงหน้านี้")
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def clinical_staff_required(view_func):
    """
    เฉพาะบุคลากรทางการแพทย์ (Admin, Doctor, Nurse) เท่านั้น
    """
    return role_required('admin', 'doctor', 'nurse')(view_func)


def doctor_only(view_func):
    """
    เฉพาะแพทย์ผู้มีอำนาจลงนามทางการแพทย์ (Doctor Only) เท่านั้น
    """
    return role_required('doctor', 'admin')(view_func)
