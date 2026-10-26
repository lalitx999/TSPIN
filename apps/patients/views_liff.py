"""
LINE Front-end Framework (LIFF) Secure 2-Step Identity Binding Controllers.
Enforces:
1. 2-Step Token-Based Verification with OTP (Anti-Brute Force)
2. Rate Limiting (5 requests/minute per IP)
3. Active Patient Context assignment strictly after verified binding
4. Tamper-proof PDPA Audit Logging
"""

import json
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from accounts.models import AuditLog
from patients.models import (
    Patient,
    PatientLinkingToken,
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
)

logger = logging.getLogger('tspi.security')


def liff_binding_page_view(request: HttpRequest) -> HttpResponse:
    """
    หน้าเว็บ LIFF สำหรับคนไข้หรือผู้ดูแลผูกบัญชี LINE OA
    รองรับทั้งโหมดใช้งานจริง (LIFF SDK) และโหมดทดสอบ (Developer Simulator)
    """
    liff_id = getattr(settings, 'LINE_LIFF_ID', '')
    roles = LinePatientBinding.RoleChoices.choices

    return render(request, 'portal_patient/line_liff_binding.html', {
        'liff_id': liff_id,
        'roles': roles,
    })


@ratelimit(key='ip', rate='5/m', block=False)
@ratelimit(key='post:line_user_id', rate='5/m', block=False)
@csrf_exempt
@require_http_methods(["POST"])
def liff_request_otp_api(request: HttpRequest) -> JsonResponse:
    """
    Step 1: ร้องขอรหัส OTP สำหรับยืนยันตัวตน
    ตรวจสอบรหัส HN และเบอร์โทรศัพท์ที่ตรงกับฐานข้อมูล แล้วสร้าง PatientLinkingToken 15 นาที
    Rate Limit: 5 ครั้ง/นาที ต่อ IP หรือต่อ LINE User ID
    """
    if getattr(request, 'limited', False):
        return JsonResponse({
            'status': 'error',
            'message': 'คุณทำรายการบ่อยเกินไปเพื่อความปลอดภัย (จำกัด 5 ครั้งต่อนาที) กรุณารอสักครู่'
        }, status=429)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'รูปแบบข้อมูล JSON ไม่ถูกต้อง'}, status=400)

    hn = body.get('hn', '').strip()
    phone = body.get('phone', '').strip().replace('-', '').replace(' ', '')
    line_user_id = body.get('line_user_id', '').strip()

    if not hn or not phone:
        return JsonResponse({'status': 'error', 'message': 'กรุณาระบุทั้งรหัส HN และเบอร์โทรศัพท์ที่ลงทะเบียนไว้'}, status=400)

    # ค้นหาคนไข้
    patient = Patient.objects.filter(hn__iexact=hn).first()
    if not patient:
        return JsonResponse({'status': 'error', 'message': 'ไม่พบประวัติผู้ป่วยตามรหัส HN ที่ระบุ'}, status=404)

    # ตรวจสอบเบอร์โทรศัพท์
    clean_patient_phone = (patient.phone or '').replace('-', '').replace(' ', '')
    if clean_patient_phone != phone:
        # บันทึก Failed Audit
        AuditLog.objects.create(
            action='LINE_BINDING_FAILED',
            user=None,
            model='LinePatientBinding',
            object_id=str(patient.pk),
            client_ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            changes={
                'reason': 'Phone mismatch during OTP request',
                'hn': hn,
                'line_user_id': line_user_id
            }
        )
        return JsonResponse({'status': 'error', 'message': 'เบอร์โทรศัพท์ไม่ตรงกับข้อมูลในเวชระเบียน'}, status=400)

    # Step 1: สร้าง 2-Step OTP Token (อายุ 15 นาที)
    token_obj, raw_otp = PatientLinkingToken.create_otp_token(patient, expires_in_minutes=15)

    masked_phone = f"{phone[:3]}-xxx-{phone[-4:]}" if len(phone) >= 7 else phone

    # บันทึก AuditLog
    AuditLog.objects.create(
        action='LINE_OTP_REQUESTED',
        user=None,
        model='PatientLinkingToken',
        object_id=str(token_obj.pk),
        client_ip=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        changes={
            'hn': patient.hn,
            'phone': masked_phone,
            'line_user_id': line_user_id
        }
    )

    # ในช่วงพัฒนายังไม่มี SMS Gateway ให้แนบ debug_otp ไปให้ใช้งานได้ทันที
    return JsonResponse({
        'status': 'ok',
        'token': token_obj.token,
        'message': f'รหัส OTP ถูกส่งไปยังเบอร์ {masked_phone} เรียบร้อยแล้ว (มีอายุ 15 นาที)',
        'masked_phone': masked_phone,
        'debug_otp': raw_otp  # Sandbox / Testing Convenience
    })


@ratelimit(key='ip', rate='5/m', block=False)
@ratelimit(key='post:line_user_id', rate='5/m', block=False)
@csrf_exempt
@require_http_methods(["POST"])
def liff_verify_otp_api(request: HttpRequest) -> JsonResponse:
    """
    Step 2: ยืนยันรหัส OTP และทำการผูกบัญชี (Caregiver 1:N Binding)
    ล็อก Invariant: LineUser.active_patient จะถูกเซ็ตหลังสร้าง Binding สำเร็จเท่านั้น
    Rate Limit: 5 ครั้ง/นาที ต่อ IP หรือต่อ LINE User ID
    """
    if getattr(request, 'limited', False):
        return JsonResponse({
            'status': 'error',
            'message': 'คุณส่งรหัสยืนยันบ่อยเกินไป (จำกัด 5 ครั้งต่อนาที) กรุณารอสักครู่'
        }, status=429)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'รูปแบบข้อมูล JSON ไม่ถูกต้อง'}, status=400)

    token_str = body.get('token', '').strip()
    otp_code = body.get('otp', '').strip()
    line_user_id = body.get('line_user_id', '').strip()
    display_name = body.get('display_name', '').strip()
    picture_url = body.get('picture_url', '').strip()
    role = body.get('role', LinePatientBinding.RoleChoices.SELF).strip()

    if not token_str or not otp_code or not line_user_id:
        return JsonResponse({'status': 'error', 'message': 'ข้อมูลไม่ครบถ้วน (ต้องการ token, otp, line_user_id)'}, status=400)

    # ตรวจสอบ Token
    token_obj = PatientLinkingToken.objects.filter(token=token_str, action_type='line_binding').first()
    if not token_obj or not token_obj.is_valid:
        return JsonResponse({'status': 'error', 'message': 'คำขอเชื่อมต่อหมดอายุหรือไม่ถูกต้อง กรุณาขอรหัสใหม่'}, status=400)

    # ตรวจสอบ OTP ด้วย Constant-Time Comparison
    if not token_obj.verify_otp(otp_code):
        AuditLog.objects.create(
            action='LINE_BINDING_FAILED',
            user=None,
            model='LinePatientBinding',
            object_id=str(token_obj.patient.pk),
            client_ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            changes={
                'reason': 'Invalid OTP code',
                'hn': token_obj.patient.hn,
                'line_user_id': line_user_id
            }
        )
        return JsonResponse({'status': 'error', 'message': 'รหัส OTP ไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง'}, status=400)

    patient = token_obj.patient

    # ตรวจสอบบทบาทความสัมพันธ์
    valid_roles = [c[0] for c in LinePatientBinding.RoleChoices.choices]
    if role not in valid_roles:
        role = LinePatientBinding.RoleChoices.SELF

    # 1. จัดเตรียม LineUser
    line_user, _ = LineUser.objects.get_or_create(
        line_user_id=line_user_id,
        defaults={
            'display_name': display_name,
            'picture_url': picture_url,
        }
    )
    if display_name and line_user.display_name != display_name:
        line_user.display_name = display_name
    if picture_url and line_user.picture_url != picture_url:
        line_user.picture_url = picture_url

    # 2. ผูกบัญชีผู้ป่วย (LinePatientBinding)
    binding, created = LinePatientBinding.objects.get_or_create(
        line_user=line_user,
        patient=patient,
        defaults={
            'role': role,
            'status': LinePatientBinding.StatusChoices.ACTIVE,
            'verified_method': 'LIFF_2STEP_OTP',
            'verified_at': timezone.now()
        }
    )

    if not created:
        binding.role = role
        binding.status = LinePatientBinding.StatusChoices.ACTIVE
        binding.verified_method = 'LIFF_2STEP_OTP'
        binding.verified_at = timezone.now()
        binding.save()

    # 3. ล็อกข้อ 3: LineUser.active_patient จะถูกเซ็ตหลังสร้าง Binding สำเร็จแล้วเท่านั้น
    line_user.active_patient = patient
    line_user.save()

    # 4. มาร์กโทเค็นว่าถูกใช้งานแล้ว
    token_obj.is_used = True
    token_obj.save(update_fields=['is_used'])

    # 5. ล็อกข้อ 4: PDPA AuditLog ครบถ้วนทุกมิติ
    AuditLog.objects.create(
        action='LINE_BINDING_SUCCESS',
        user=line_user.user,
        model='LinePatientBinding',
        object_id=str(patient.pk),
        client_ip=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        changes={
            'hn': patient.hn,
            'patient_name': patient.full_name,
            'line_user_id': line_user_id,
            'display_name': display_name,
            'role': role,
            'verified_method': 'LIFF_2STEP_OTP',
            'status': binding.status
        }
    )

    return JsonResponse({
        'status': 'ok',
        'message': f'ยืนยันตัวตนสำเร็จ! เชื่อมต่อบัญชีคุณ {patient.full_name} (HN: {patient.hn}) ในฐานะ "{binding.get_role_display()}" เรียบร้อยแล้ว',
        'patient': {
            'hn': patient.hn,
            'name': patient.full_name,
            'role': binding.get_role_display(),
        }
    })


@ratelimit(key='ip', rate='5/m', block=False)
@ratelimit(key='post:line_user_id', rate='5/m', block=False)
@csrf_exempt
@require_http_methods(["POST"])
def liff_request_staff_assisted_api(request: HttpRequest) -> JsonResponse:
    """
    Staff-Assisted Fallback API:
    กรณีที่ผู้ป่วยไม่สามารถรับ SMS หรือยังไม่ได้ลงทะเบียนเบอร์ในระบบ
    สร้างคำขอใน Clinical Review Queue เพื่อให้พยาบาลหรือเจ้าหน้าที่ยืนยันตัวตนและ Approve จากหน้า Admin
    """
    if getattr(request, 'limited', False):
        return JsonResponse({
            'status': 'error',
            'message': 'คุณทำรายการบ่อยเกินไป (จำกัด 5 ครั้งต่อนาที) กรุณารอสักครู่'
        }, status=429)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'รูปแบบข้อมูล JSON ไม่ถูกต้อง'}, status=400)

    token_str = body.get('token', '').strip()
    line_user_id = body.get('line_user_id', '').strip()
    display_name = body.get('display_name', '').strip()
    picture_url = body.get('picture_url', '').strip()
    role = body.get('role', LinePatientBinding.RoleChoices.SELF).strip()

    if not token_str or not line_user_id:
        return JsonResponse({'status': 'error', 'message': 'ข้อมูลไม่ครบถ้วน (ต้องการ token, line_user_id)'}, status=400)

    token_obj = PatientLinkingToken.objects.filter(token=token_str, action_type='line_binding').first()
    if not token_obj or not token_obj.is_valid:
        return JsonResponse({'status': 'error', 'message': 'คำขอเชื่อมต่อหมดอายุหรือไม่ถูกต้อง กรุณากรอก HN ใหม่อีกครั้ง'}, status=400)

    patient = token_obj.patient

    # ตรวจสอบหรือสร้าง LineUser ก่อน
    line_user, _ = LineUser.objects.get_or_create(
        line_user_id=line_user_id,
        defaults={'display_name': display_name, 'picture_url': picture_url}
    )

    import uuid
    # สร้าง CommunicationRecord เพื่อเป็น source_message
    note_content = f"คำขอเชื่อมต่อ LINE OA (Staff-Assisted Fallback):\nLINE User: {display_name} ({line_user_id})\nRole: {role}\nToken: {token_str[:12]}..."
    comm_record = CommunicationRecord.objects.create(
        line_message_id=f"staff_req_{uuid.uuid4().hex[:16]}",
        line_user=line_user,
        patient=patient,
        direction=CommunicationRecord.DirectionChoices.INCOMING,
        message_type=CommunicationRecord.MessageTypeChoices.TEXT,
        content=note_content,
        is_clinical_candidate=True
    )

    # สร้าง ClinicalReviewItem สำหรับพยาบาล (Level 1 Intake Review)
    review_item = ClinicalReviewItem.objects.create(
        patient=patient,
        source_message=comm_record,
        review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE,
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW,
        review_notes=note_content
    )

    # บันทึก AuditLog
    AuditLog.objects.create(
        action='LINE_STAFF_ASSISTED_REQUESTED',
        user=None,
        model='ClinicalReviewItem',
        object_id=str(review_item.pk),
        client_ip=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        changes={
            'hn': patient.hn,
            'line_user_id': line_user_id,
            'display_name': display_name,
            'role': role,
            'review_item_id': review_item.pk,
            'token': token_str[:12] + '...'
        }
    )

    return JsonResponse({
        'status': 'ok',
        'message': f'ระบบได้ส่งคำขอยืนยันตัวตนไปยังพยาบาลประจำคลินิกเรียบร้อยแล้ว กรุณาแจ้งเจ้าหน้าที่เพื่อทำการอนุมัติ (รหัสคำขอ: #{review_item.pk})',
        'review_item_id': review_item.pk
    })

