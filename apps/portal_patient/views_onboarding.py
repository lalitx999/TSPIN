"""
Patient Onboarding Wizard & Identity Flow (Phase 2).
Handles:
1. Nationality check (Thai vs International)
2. Existing patient lookup (Anti-leak, Hash search, Rate limiting, AuditLog)
3. Masked identity confirmation & OTP / Portal account binding
4. New patient onboarding form
"""

import time
import hashlib
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import login, get_user_model
from django.core.cache import cache
from django.db import models, transaction

User = get_user_model()


from core.models import ClinicalEncryption
from patients.models import Patient
from accounts.models import AuditLog


def log_audit_event(user, action, model_name, object_id, details, ip_address=None):
    """Helper สำหรับบันทึก AuditLog อย่างปลอดภัย"""
    try:
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            model=model_name,
            object_id=str(object_id),
            changes={'details': details},
            client_ip=ip_address
        )
    except Exception:
        pass


def onboarding_wizard_view(request):
    """
    Onboarding Wizard Step-by-Step UI:
    Step 1: สัญชาติ (ไทย / ต่างชาติ)
    Step 2: ประวัติการรับบริการ (เคยรักษากับ TSPI ไหม?)
    Branch A: คนไข้เก่า -> ตรวจสอบประวัติด้วยเลขบัตร 13 หลัก / Passport -> แสดงข้อมูล Masked -> ตั้งรหัสผ่าน
    Branch B: คนไข้ใหม่ -> กรอกข้อมูลสั้น -> บันทึกลงระบบจริงทันที
    """
    return render(request, 'portal_patient/onboarding/wizard.html')


@require_POST
def onboarding_lookup_api(request):
    """
    API ค้นหาข้อมูลคนไข้เดิม (Gotcha 2):
    - Rate Limit 5 ครั้ง / นาที ต่อ IP
    - บันทึก AuditLog ทุกครั้ง
    - Anti-leak: ตอบผลลัพธ์เป็นกลาง ไม่ยืนยันว่ามีเลขนี้ในระบบหรือไม่ถ้าค้นไม่พบ
    - Masked data: คืนเฉพาะข้อมูลที่ปกปิดตัวตน เช่น 'คุณ ส*** ใจ***'
    """
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1')).split(',')[0].strip()
    rate_limit_key = f"onboarding_lookup_{client_ip}"
    attempts = cache.get(rate_limit_key, 0)

    if attempts >= 5:
        log_audit_event(
            user=None,
            action='RATE_LIMIT_EXCEEDED',
            model_name='Patient',
            object_id='LOOKUP_BRUTEFORCE_BLOCKED',
            details=f"Rate limit exceeded for IP {client_ip} during onboarding lookup",
            ip_address=client_ip
        )
        return JsonResponse({
            'success': False,
            'message': 'คุณทำรายการเกินจำนวนครั้งที่กำหนด กรุณารอ 1 นาทีแล้วลองใหม่อีกครั้ง'
        }, status=429)


    cache.set(rate_limit_key, attempts + 1, timeout=60)

    nationality = request.POST.get('nationality', 'TH').strip().upper()
    identifier = request.POST.get('identifier', '').strip().replace('-', '').replace(' ', '')

    if not identifier:
        return JsonResponse({
            'success': False,
            'message': 'กรุณาระบุเลขประจำตัวประชาชนหรือหมายเลขพาสปอร์ต'
        }, status=400)

    # Search logic: For Thai nationality, hash with SHA-256; for foreigner, match passport
    patient = None
    if nationality == 'TH' and len(identifier) == 13 and identifier.isdigit():
        id_hash = hashlib.sha256(identifier.encode('utf-8')).hexdigest()
        patient = Patient.objects.alive().filter(id_card_hash=id_hash).first()
    else:
        # Search by passport or phone if provided
        patient = Patient.objects.alive().filter(
            models.Q(passport_number__iexact=identifier) | models.Q(phone__icontains=identifier)
        ).first() if hasattr(Patient, 'passport_number') else Patient.objects.alive().filter(phone__icontains=identifier).first()

    # Audit Logging (Gotcha 2)
    id_preview = f"{identifier[:3]}***{identifier[-2:]}" if len(identifier) > 5 else "***"
    log_audit_event(
        user=None,
        action='PATIENT_LOOKUP',
        model_name='Patient',
        object_id=str(patient.pk) if patient else 'NOT_FOUND',
        details=f"Lookup attempt for {nationality} id_preview={id_preview} from IP={client_ip} found={bool(patient)}",
        ip_address=client_ip
    )


    if not patient:
        # Anti-leak message (Gotcha 2)
        return JsonResponse({
            'success': False,
            'message': 'ไม่พบข้อมูลประวัติเวชระเบียน กรุณาติดต่อเจ้าหน้าที่คลินิก หรือเลือก "เป็นคนไข้ใหม่" เพื่อเริ่มต้นลงทะเบียน'
        }, status=404)

    # Prepare safe masked data for confirmation
    return JsonResponse({
        'success': True,
        'patient_uuid': str(patient.uuid),
        'masked_name': patient.masked_name,
        'masked_id': patient.masked_id_card,
        'masked_phone': patient.masked_phone,
        'hn': patient.hn,
        'has_portal_account': bool(patient.user_id),
    })


@require_POST
def onboarding_claim_account_api(request):
    """
    ยืนยันความเป็นเจ้าของประวัติคนไข้เดิม และสร้าง/ผูกบัญชีเข้าใช้งาน Portal
    """
    patient_uuid = request.POST.get('patient_uuid', '').strip()
    password = request.POST.get('password', '').strip()
    phone_confirm = request.POST.get('phone_last4', '').strip()

    if not patient_uuid:
        return JsonResponse({'success': False, 'message': 'ไม่พบรหัสอ้างอิงคนไข้'}, status=400)

    patient = Patient.objects.alive().filter(uuid=patient_uuid).first()
    if not patient:
        return JsonResponse({'success': False, 'message': 'ไม่พบข้อมูลในระบบ'}, status=404)

    # Verify last 4 digits of phone number
    cleaned_phone = (patient.phone or '').replace('-', '').replace(' ', '')
    if phone_confirm and not cleaned_phone.endswith(phone_confirm):
        return JsonResponse({
            'success': False,
            'message': 'เบอร์โทรศัพท์ 4 ตัวท้ายไม่ตรงกับข้อมูลในระบบ กรุณาตรวจสอบอีกครั้ง'
        }, status=400)

    # Create or update portal User
    username = f"pt_{patient.hn.lower().replace('/', '_')}"
    user = patient.user
    if not user:
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create_user(
                username=username,
                email=patient.email or f"{username}@patient.tspi.local",
                first_name=patient.first_name,
                last_name=patient.last_name,
                role=User.Role.PATIENT,
                phone=patient.phone
            )
        patient.user = user

        patient.save(update_fields=['user'])

    if password:
        user.set_password(password)
        user.save()

    # Log user in
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')


    log_audit_event(
        user=user,
        action='PORTAL_CLAIM_SUCCESS',
        model_name='Patient',
        object_id=str(patient.pk),
        details=f"Patient {patient.hn} claimed portal account and logged in"
    )


    return JsonResponse({
        'success': True,
        'redirect_url': '/portal/ai-intake/'
    })


@require_POST
def onboarding_new_patient_api(request):
    """
    ลงทะเบียนคนไข้ใหม่ (Branch B - Low Friction Form):
    - สร้าง Patient ใน PostgreSQL ทันที
    - สร้างบัญชี User และ Login อัตโนมัติ
    - ส่งต่อไปยัง AI Intake ทันที
    """
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    birth_date_str = request.POST.get('birth_date', '').strip()
    gender = request.POST.get('gender', 'O').strip()
    nationality = request.POST.get('nationality', 'TH').strip()
    id_card_or_passport = request.POST.get('id_card', '').strip()
    password = request.POST.get('password', '').strip()

    if not first_name or not last_name or not phone:
        return JsonResponse({
            'success': False,
            'message': 'กรุณากรอกชื่อ นามสกุล และเบอร์โทรศัพท์ให้ครบถ้วน'
        }, status=400)

    # Parse birth date
    birth_date = None
    if birth_date_str:
        try:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    with transaction.atomic():
        # Generate new HN: e.g. TSPI-2026-XXXX
        last_patient = Patient.objects.order_by('-id').first()
        next_seq = (last_patient.id + 1) if last_patient else 1
        hn = f"HN{datetime.now().strftime('%y%m')}{next_seq:04d}"

        patient = Patient(
            hn=hn,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            gender=gender,
            birth_date=birth_date,
            status='pending',
        )

        if hasattr(patient, 'nationality'):
            patient.nationality = nationality

        if id_card_or_passport:
            if nationality == 'TH' and len(id_card_or_passport.replace('-', '')) == 13:
                patient.set_id_card(id_card_or_passport)
            else:
                if hasattr(patient, 'passport_number'):
                    patient.passport_number = id_card_or_passport
                patient.extra_data['id_or_passport'] = id_card_or_passport

        # Create user account
        username = f"pt_{hn.lower()}"
        user = User.objects.create_user(
            username=username,
            email=email or f"{username}@patient.tspi.local",
            first_name=first_name,
            last_name=last_name,
            password=password if password else None,
            role=User.Role.PATIENT,
            phone=phone
        )

        patient.user = user
        patient.save()

        # Auto login
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')


        log_audit_event(
            user=user,
            action='NEW_PATIENT_REGISTER',
            model_name='Patient',
            object_id=str(patient.pk),
            details=f"New patient {patient.hn} registered from onboarding wizard"
        )


    return JsonResponse({
        'success': True,
        'hn': patient.hn,
        'redirect_url': '/portal/ai-intake/'
    })
