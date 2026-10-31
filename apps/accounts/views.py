"""
Authentication Views for Dr. Patt Clinical EMR.
Enforces Rate Limiting, Session Fixation Rotation, and Full AuditLog (Pillars 1, 7, 8).
"""

import hashlib
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from accounts.models import AuditLog, User
from accounts.forms import DoctorLoginForm, PatientLoginForm, PatientRegistrationForm

def _is_safe_next(request, next_url) -> bool:
    """ต้องเป็น URL ภายในระบบ (startswith('/') อย่างเดียวยอมให้ //evil.com ผ่านได้)"""
    return bool(next_url) and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure())


def get_client_ip(request):
    """
    ดึง Client IP จริง: X-Forwarded-For ตัวแรกผู้เรียกปลอมได้ จึงไม่ใช้
    เชื่อ X-Real-IP เฉพาะเมื่อ TRUST_X_REAL_IP=True (production หลัง nginx ที่เขียนทับ header นี้เสมอ)
    """
    if getattr(settings, 'TRUST_X_REAL_IP', False):
        real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
        if real_ip:
            return real_ip
    return request.META.get('REMOTE_ADDR', '')


@ratelimit(key='ip', rate='5/m', block=True)
@require_http_methods(["GET", "POST"])
def doctor_login_view(request):
    """
    พอร์ทัลเข้าสู่ระบบสำหรับแพทย์และบุคลากรทางการแพทย์
    """
    if request.user.is_authenticated:
        if request.user.is_clinical_staff:
            return redirect('patients:dashboard')
        return redirect('portal_patient:dashboard')

    if request.method == 'POST':
        form = DoctorLoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            
            # ⚠️ ป้องกัน Session Fixation Attack: หมุนเวียน Session Key ทันทีหลังล็อกอินสำเร็จ
            request.session.cycle_key()
            
            # บันทึก IP ลงในโปรไฟล์ผู้ใช้
            client_ip = get_client_ip(request)
            user.last_login_ip = client_ip
            user.save(update_fields=['last_login_ip'])

            # ⚠️ บันทึก AuditLog
            AuditLog.objects.create(
                user=user,
                action="DOCTOR_LOGIN_SUCCESS",
                model="User",
                object_id=str(user.pk),
                client_ip=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )

            messages.success(request, f"ยินดีต้อนรับ นพ./พญ. {user.get_full_name() or user.username}")
            if user.must_change_password:
                # บัญชีที่ผู้ดูแลตั้งรหัสให้ ต้องเปลี่ยนรหัสก่อนใช้งาน (middleware กันไม่ให้ไปหน้าอื่น)
                request.session['force_password_change'] = True
                return redirect('accounts:password_change')
            next_url = request.GET.get('next')
            if _is_safe_next(request, next_url):
                return redirect(next_url)
            return redirect('patients:dashboard')
    else:
        form = DoctorLoginForm(request=request)

    return render(request, 'accounts/doctor_login.html', {'form': form})


@ratelimit(key='ip', rate='5/m', block=True)
@require_http_methods(["GET", "POST"])
def patient_login_view(request):
    """
    พอร์ทัลเข้าสู่ระบบสำหรับคนไข้
    """
    if request.user.is_authenticated:
        if request.user.is_clinical_staff:
            return redirect('patients:dashboard')
        return redirect('portal_patient:dashboard')

    if request.method == 'POST':
        form = PatientLoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            request.session.cycle_key()

            client_ip = get_client_ip(request)
            user.last_login_ip = client_ip
            user.save(update_fields=['last_login_ip'])

            AuditLog.objects.create(
                user=user,
                action="PATIENT_LOGIN_SUCCESS",
                model="User",
                object_id=str(user.pk),
                client_ip=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )

            messages.success(request, f"ยินดีต้อนรับ คุณ{user.get_full_name() or user.username}")
            next_url = request.GET.get('next')
            if _is_safe_next(request, next_url):
                return redirect(next_url)
            return redirect('portal_patient:dashboard')
    else:
        form = PatientLoginForm(request=request)

    return render(request, 'accounts/patient_login.html', {'form': form})


@ratelimit(key='ip', rate='3/h', block=True)
@require_http_methods(["GET", "POST"])
def patient_register_view(request):
    """
    ลงทะเบียนคนไข้ใหม่ พร้อมตรวจสอบ PDPA Consent
    """
    if request.user.is_authenticated:
        return redirect('portal_patient:dashboard')

    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            raw_id = form.cleaned_data['id_card']
            
            # บันทึก User คนไข้ใหม่
            user = form.save(commit=False)
            user.username = raw_id
            user.role = User.Role.PATIENT
            user.set_password(form.cleaned_data['password'])
            user.phone = form.cleaned_data['phone']
            # เข้ารหัส SHA-256 ของเลขบัตรประชาชน
            user.id_card_hash = hashlib.sha256(raw_id.encode('utf-8')).hexdigest()
            user.save()

            client_ip = get_client_ip(request)
            AuditLog.objects.create(
                user=user,
                action="PATIENT_REGISTRATION_SUCCESS",
                model="User",
                object_id=str(user.pk),
                changes={"username": raw_id, "role": user.role},
                client_ip=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )

            messages.success(request, "ลงทะเบียนสำเร็จแล้ว! กรุณาเข้าสู่ระบบด้วยเลขบัตรประชาชนและรหัสผ่านของคุณ")
            return redirect('accounts:patient_login')
    else:
        form = PatientRegistrationForm()

    return render(request, 'accounts/patient_register.html', {'form': form})


@require_http_methods(["POST"])
def user_logout_view(request):
    """
    ออกจากระบบ: ล้างเซสชัน ขจัดคุกกี้ หมุนเวียนคีย์ และบันทึก AuditLog (Pillar 1 & 8)
    """
    if request.user.is_authenticated:
        user = request.user
        AuditLog.objects.create(
            user=user,
            action="USER_LOGOUT_SUCCESS",
            model="User",
            object_id=str(user.pk),
            client_ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
    
    logout(request)
    request.session.flush()
    messages.info(request, "คุณได้ออกจากระบบอย่างปลอดภัยแล้ว")
    return redirect('core:home')


def lockout_view(request, credentials=None):
    """
    หน้าแจ้งเตือนเมื่อระบบล็อกอินถูกระงับชั่วคราวจากการกรอกรหัสผ่านผิดเกิน 5 ครั้ง (django-axes)
    """
    return render(request, 'accounts/lockout.html', {
        'cooloff_minutes': 15,
        'client_ip': get_client_ip(request)
    }, status=429)


@login_required
@require_http_methods(["GET", "POST"])
def password_change_view(request):
    """เปลี่ยนรหัสผ่าน (บังคับครั้งแรกสำหรับบัญชีที่ผู้ดูแลตั้งรหัสให้) ตรวจตามนโยบายรหัสผ่านของระบบ"""
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        update_session_auth_hash(request, user)
        request.session.pop('force_password_change', None)
        AuditLog.objects.create(
            user=user, action="PASSWORD_CHANGED", model="User", object_id=str(user.pk),
            client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        messages.success(request, "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว")
        return redirect('patients:dashboard' if user.is_clinical_staff else 'portal_patient:dashboard')
    return render(request, 'accounts/password_change.html', {
        'form': form,
        'forced': request.session.get('force_password_change', False),
    })
