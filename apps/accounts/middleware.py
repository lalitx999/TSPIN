"""
Session Timeout & Security Middleware (Pillar 1).
Enforces 30-minute idle timeout and 12-hour absolute ceiling.
"""

import time
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from accounts.models import AuditLog

class IdleSessionTimeoutMiddleware:
    """
    มิดเดิลแวร์บังคับใช้กฎ Session Timeout:
    1. Idle Timeout: หากไม่มีการใช้งานเกิน 30 นาที (1,800 วินาที) จะตัดการเชื่อมต่ออัตโนมัติ
    2. Absolute Ceiling: บังคับให้ออกจากระบบเมื่อเซสชันมีอายุเกิน 12 ชั่วโมง (43,200 วินาที)
    """
    IDLE_TIMEOUT_SECONDS = 1800     # 30 นาที
    ABSOLUTE_TIMEOUT_SECONDS = 43200 # 12 ชั่วโมง

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = time.time()
            last_activity = request.session.get('last_activity')
            session_start = request.session.get('session_start')

            # 1. ตรวจสอบ Absolute Session Ceiling (12 ชั่วโมง)
            if session_start and (current_time - session_start > self.ABSOLUTE_TIMEOUT_SECONDS):
                AuditLog.objects.create(
                    user=request.user,
                    action="SESSION_ABSOLUTE_TIMEOUT",
                    client_ip=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
                logout(request)
                request.session.flush()
                messages.info(request, "เซสชันของคุณหมดอายุการใช้งานสูงสุด (12 ชั่วโมง) กรุณาเข้าสู่ระบบใหม่")
                return redirect('accounts:doctor_login')

            # 2. ตรวจสอบ Idle Timeout (30 นาที)
            if last_activity and (current_time - last_activity > self.IDLE_TIMEOUT_SECONDS):
                AuditLog.objects.create(
                    user=request.user,
                    action="SESSION_IDLE_TIMEOUT",
                    client_ip=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
                logout(request)
                request.session.flush()
                messages.warning(request, "คุณไม่มีการใช้งานเกิน 30 นาที ระบบได้ทำการออกจากระบบโดยอัตโนมัติเพื่อความปลอดภัย")
                return redirect('accounts:doctor_login')

            # อัปเดตเวลาการใช้งานล่าสุด
            request.session['last_activity'] = current_time
            if not session_start:
                request.session['session_start'] = current_time

        response = self.get_response(request)
        return response


class ForcePasswordChangeMiddleware:
    """
    ถ้าล็อกอินด้วยรหัสที่ผู้ดูแลตั้งให้ (must_change_password) จะเข้าได้แค่หน้าเปลี่ยนรหัส/ออกจากระบบ
    ธงอยู่ใน session ที่ตั้งตอนล็อกอิน
    """
    ALLOWED_PREFIXES = ('/accounts/password/change/', '/accounts/logout/', '/static/', '/health')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.session.get('force_password_change')
            and not request.path.startswith(self.ALLOWED_PREFIXES)
        ):
            return redirect('accounts:password_change')
        return self.get_response(request)


class DevTunnelGuardMiddleware:
    """
    ตอนพัฒนาที่เปิด tunnel (cloudflared/ngrok) ให้ LINE ส่ง webhook เข้าเครื่อง:
    request ที่มาทาง host ของ tunnel ใช้ได้เฉพาะ path ของ LINE webhook และหน้า LIFF เท่านั้น
    หน้าอื่น (เวชระเบียน, admin, ฯลฯ) ตอบ 404 เพื่อไม่ให้ข้อมูลผู้ป่วยในเครื่อง dev หลุดออกอินเทอร์เน็ต
    ทำงานเฉพาะเมื่อตั้ง DEV_TUNNEL_HOSTS
    """
    PUBLIC_PREFIXES = ('/line/webhook/', '/liff/', '/patient/line/liff/', '/static/', '/health/')

    def __init__(self, get_response):
        from django.conf import settings
        self.get_response = get_response
        self.tunnel_hosts = tuple(getattr(settings, 'DEV_TUNNEL_HOSTS', ()))

    def __call__(self, request):
        if self.tunnel_hosts:
            host = request.META.get('HTTP_HOST', '').split(':')[0].lower()
            if host.endswith(self.tunnel_hosts) and not request.path.startswith(self.PUBLIC_PREFIXES):
                from django.http import HttpResponseNotFound
                return HttpResponseNotFound('Not Found')
        return self.get_response(request)
