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

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Value
from django.db.models.functions import Replace, Upper
import hashlib
import httpx

from accounts.models import AuditLog
from accounts.views import get_client_ip
from patients.models import (
    Patient,
    PatientLinkingToken,
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
)

logger = logging.getLogger('tspi.security')

OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


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


def resolve_line_user_id(body: dict):
    """
    ระบุตัวผู้ใช้ LINE จาก LIFF ID token ที่ LINE ลงนาม (ไม่เชื่อ line_user_id ที่หน้าเว็บส่งมาเอง)
    ตั้ง LINE_LIFF_ID แล้ว: ต้องมี id_token และ LINE ต้องยืนยันว่าออกให้ channel นี้
    ยังไม่ตั้ง: ยอมรับ line_user_id จากหน้าเว็บเฉพาะตอน DEBUG (โหมดจำลอง) เท่านั้น
    คืน (line_user_id, None) หรือ ('', JsonResponse error)
    """
    liff_id = getattr(settings, 'LINE_LIFF_ID', '')
    if not liff_id:
        if settings.DEBUG:
            return body.get('line_user_id', '').strip(), None
        return '', JsonResponse({'status': 'error', 'message': 'ระบบยังไม่ได้ตั้งค่า LINE LIFF'}, status=503)

    id_token = (body.get('id_token') or '').strip()
    if not id_token:
        return '', JsonResponse({'status': 'error', 'message': 'กรุณาเปิดหน้านี้จากแอป LINE'}, status=401)
    channel_id = liff_id.split('-', 1)[0]
    try:
        resp = httpx.post('https://api.line.me/oauth2/v2.1/verify',
                          data={'id_token': id_token, 'client_id': channel_id}, timeout=5.0)
        claims = resp.json() if resp.status_code == 200 else {}
    except (httpx.HTTPError, ValueError):
        claims = {}
    if not claims.get('sub'):
        logger.warning("[LIFF] ID token verification failed")
        return '', JsonResponse({'status': 'error', 'message': 'ยืนยันตัวตน LINE ไม่สำเร็จ กรุณาเปิดหน้านี้ใหม่จากแอป LINE'}, status=401)
    return claims['sub'], None


def _find_patient(identifier: str):
    """ค้นเวชระเบียนจาก HN (มี/ไม่มีขีด) หรือเลขบัตร ปชช. 13 หลัก"""
    normalized = identifier.replace('-', '').replace(' ', '').upper()
    if not normalized:
        return None
    if normalized.isdigit() and len(normalized) == 13:
        return Patient.objects.alive().filter(id_card_hash=hashlib.sha256(normalized.encode('utf-8')).hexdigest()).first()
    return (
        Patient.objects.alive()
        .annotate(hn_norm=Upper(Replace(Replace('hn', Value('-'), Value('')), Value(' '), Value(''))))
        .filter(hn_norm=normalized)
        .first()
    )


def _mask_email(email: str) -> str:
    local, _, domain = email.partition('@')
    return f"{local[:2]}{'*' * max(len(local) - 2, 3)}@{domain}"


def _issue_email_otp(request: HttpRequest, patient: Patient, line_user_id: str) -> JsonResponse:
    """สร้าง token + OTP แล้วส่ง OTP ไปที่อีเมลในเวชระเบียนเท่านั้น (ห้ามส่งไปอีเมลที่ผู้ใช้กรอกมาใหม่)"""
    token_obj, raw_otp = PatientLinkingToken.create_otp_token(patient, expires_in_minutes=OTP_EXPIRY_MINUTES)
    common_audit = dict(user=None, object_id=str(token_obj.pk), client_ip=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500])

    if not patient.email:
        # ไม่มีอีเมลในระบบ: ให้ยืนยันกับเจ้าหน้าที่ (token นี้ใช้ได้กับ Staff-Assisted เท่านั้น เพราะไม่มีใครได้ OTP)
        AuditLog.objects.create(action='LINE_OTP_STAFF_REQUIRED', model='PatientLinkingToken',
                                changes={'hn': patient.hn, 'line_user_id': line_user_id}, **common_audit)
        return JsonResponse({
            'status': 'staff_required',
            'token': token_obj.token,
            'message': 'เวชระเบียนนี้ยังไม่มีอีเมล กรุณากดขอให้เจ้าหน้าที่ยืนยันตัวตน หรือแจ้งที่เคาน์เตอร์คลินิก',
        }, status=200)

    try:
        send_mail(
            subject='รหัสยืนยันการเชื่อมต่อ LINE — TSPI Clinic',
            message=(
                f"รหัส OTP สำหรับเชื่อมต่อบัญชี LINE กับเวชระเบียนของคุณคือ {raw_otp}\n"
                f"รหัสมีอายุ {OTP_EXPIRY_MINUTES} นาที ห้ามบอกรหัสนี้กับผู้อื่น\n"
                "หากคุณไม่ได้ทำรายการนี้ กรุณาติดต่อคลินิก"
            ),
            from_email=None,
            recipient_list=[patient.email],
        )
    except Exception as exc:
        logger.error(f"[LIFF OTP] Email delivery failed for patient {patient.pk}: {type(exc).__name__}")
        token_obj.is_used = True
        token_obj.save(update_fields=['is_used'])
        return JsonResponse({'status': 'error', 'message': 'ส่งอีเมลไม่สำเร็จ กรุณาลองใหม่ หรือติดต่อเจ้าหน้าที่'}, status=503)

    masked = _mask_email(patient.email)
    AuditLog.objects.create(action='LINE_OTP_REQUESTED', model='PatientLinkingToken',
                            changes={'hn': patient.hn, 'channel': 'email', 'to': masked, 'line_user_id': line_user_id},
                            **common_audit)
    return JsonResponse({
        'status': 'ok',
        'token': token_obj.token,
        'masked_email': masked,
        'message': f'ส่งรหัส OTP ไปที่อีเมล {masked} แล้ว (มีอายุ {OTP_EXPIRY_MINUTES} นาที)',
    })


@ratelimit(key='ip', rate='5/m', block=False)
@ratelimit(key='post:line_user_id', rate='5/m', block=False)
@csrf_exempt
@require_http_methods(["POST"])
def liff_request_otp_api(request: HttpRequest) -> JsonResponse:
    """
    Step 1: กรอก HN หรือเลขบัตร ปชช. แล้วส่ง OTP ไปที่อีเมลที่อยู่ในเวชระเบียน
    ไม่พบเวชระเบียน -> status 'not_found' ให้หน้าเว็บแสดงฟอร์มลงทะเบียน
    ไม่มีอีเมล -> status 'staff_required' ให้ยืนยันกับเจ้าหน้าที่
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

    identifier = (body.get('identifier') or body.get('hn') or '').strip()
    line_user_id, identity_error = resolve_line_user_id(body)
    if identity_error:
        return identity_error
    if not identifier:
        return JsonResponse({'status': 'error', 'message': 'กรุณาระบุ HN หรือเลขบัตรประชาชน 13 หลัก'}, status=400)

    patient = _find_patient(identifier)
    if not patient:
        return JsonResponse({
            'status': 'not_found',
            'message': 'ไม่พบเวชระเบียน หากเป็นผู้รับบริการใหม่ กรุณาลงทะเบียนด้านล่าง',
        }, status=404)
    return _issue_email_otp(request, patient, line_user_id)


@ratelimit(key='ip', rate='3/m', block=False)
@ratelimit(key='post:line_user_id', rate='3/m', block=False)
@csrf_exempt
@require_http_methods(["POST"])
def liff_register_api(request: HttpRequest) -> JsonResponse:
    """
    ลงทะเบียนผู้รับบริการใหม่จากฟอร์มใน LINE แล้วส่ง OTP ไปยืนยันอีเมล
    เวชระเบียนที่สร้างมีสถานะ pending และติดธงให้เจ้าหน้าที่ตรวจสอบตัวตนตอนมาคลินิก
    """
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'ทำรายการบ่อยเกินไป กรุณารอสักครู่'}, status=429)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'รูปแบบข้อมูล JSON ไม่ถูกต้อง'}, status=400)

    first_name = body.get('first_name', '').strip()
    last_name = body.get('last_name', '').strip()
    national_id = body.get('national_id', '').replace('-', '').replace(' ', '')
    phone = body.get('phone', '').replace('-', '').replace(' ', '')
    email = body.get('email', '').strip().lower()
    line_user_id, identity_error = resolve_line_user_id(body)
    if identity_error:
        return identity_error

    if not (first_name and last_name and phone and email):
        return JsonResponse({'status': 'error', 'message': 'กรุณากรอกชื่อ นามสกุล เบอร์โทร และอีเมลให้ครบ'}, status=400)
    if not body.get('pdpa_consent'):
        return JsonResponse({'status': 'error', 'message': 'กรุณายอมรับการเก็บและใช้ข้อมูลสุขภาพตาม PDPA'}, status=400)
    if not is_valid_thai_id(national_id):
        return JsonResponse({'status': 'error', 'message': 'เลขบัตรประชาชนไม่ถูกต้อง'}, status=400)
    if not (phone.isdigit() and 9 <= len(phone) <= 10):
        return JsonResponse({'status': 'error', 'message': 'เบอร์โทรศัพท์ไม่ถูกต้อง'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'status': 'error', 'message': 'อีเมลไม่ถูกต้อง'}, status=400)

    if _find_patient(national_id):
        return JsonResponse({
            'status': 'exists',
            'message': 'เลขบัตรนี้มีเวชระเบียนอยู่แล้ว กรุณายืนยันตัวตนด้วยเลขบัตรแทนการลงทะเบียนใหม่',
        }, status=409)

    with transaction.atomic():
        patient = Patient(
            hn=_next_hn(), first_name=first_name, last_name=last_name, phone=phone, email=email, status='pending',
            extra_data={'registered_via': 'line_liff', 'needs_staff_verification': True,
                        'pdpa_consent_at': timezone.now().isoformat()},
        )
        patient.set_id_card(national_id)
        patient.save()
        AuditLog.objects.create(user=None, action='PATIENT_SELF_REGISTERED_LINE', model='Patient', object_id=str(patient.pk),
                                changes={'hn': patient.hn, 'line_user_id': line_user_id},
                                client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500])
    return _issue_email_otp(request, patient, line_user_id)


def is_valid_thai_id(value: str) -> bool:
    """ตรวจเลขบัตรประชาชนไทย 13 หลักด้วยหลักตรวจสอบ (check digit)"""
    if not (value.isdigit() and len(value) == 13):
        return False
    total = sum(int(value[i]) * (13 - i) for i in range(12))
    return (11 - total % 11) % 10 == int(value[12])


def _next_hn() -> str:
    """HN รูปแบบเดียวกับการลงทะเบียนบนเว็บ: HN{ปีเดือน}{ลำดับ}"""
    prefix = f"HN{timezone.localtime():%y%m}"
    seq = Patient.all_objects.filter(hn__startswith=prefix).count() + 1
    while Patient.all_objects.filter(hn=f"{prefix}{seq:04d}").exists():
        seq += 1
    return f"{prefix}{seq:04d}"


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
    line_user_id, identity_error = resolve_line_user_id(body)
    if identity_error:
        return identity_error
    display_name = body.get('display_name', '').strip()
    picture_url = body.get('picture_url', '').strip()
    role = body.get('role', LinePatientBinding.RoleChoices.SELF).strip()

    if not token_str or not otp_code or not line_user_id:
        return JsonResponse({'status': 'error', 'message': 'ข้อมูลไม่ครบถ้วน (ต้องการ token, otp, line_user_id)'}, status=400)

    # ตรวจสอบ Token
    token_obj = PatientLinkingToken.objects.filter(token=token_str, action_type='line_binding').first()
    if not token_obj or not token_obj.is_valid:
        return JsonResponse({'status': 'error', 'message': 'คำขอเชื่อมต่อหมดอายุหรือไม่ถูกต้อง กรุณาขอรหัสใหม่'}, status=400)

    # ตรวจสอบ OTP ด้วย Constant-Time Comparison (ผิดเกิน OTP_MAX_ATTEMPTS ครั้ง token นี้ใช้ไม่ได้อีก)
    attempts_key = f"liff_otp_attempts_{token_obj.pk}"
    if not token_obj.verify_otp(otp_code):
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, timeout=OTP_EXPIRY_MINUTES * 60)
        if attempts >= OTP_MAX_ATTEMPTS:
            token_obj.is_used = True
            token_obj.save(update_fields=['is_used'])
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
    line_user_id, identity_error = resolve_line_user_id(body)
    if identity_error:
        return identity_error
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

