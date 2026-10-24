import logging
import os
import re
import secrets
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from .throttles import StaffLoginThrottle, StaffLoginAccountThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from patients.models import Patient, PatientBiologicalRecord, AuditLog
from patients.serializers import PatientSerializer

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Capture proxy-forwarded client IP without recording request credentials/body."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", ""))[:100]

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def linked_patient_for_user(user):
    """Never infer clinical ownership from a shared/empty email or ambiguous ID."""
    matches = list(Patient.objects.filter(id_card=user.username).order_by('pk')[:2])
    return matches[0] if len(matches) == 1 else None

@api_view(['POST'])
@permission_classes([AllowAny])
def patient_activate(request):
    """Phone/name matching is not sufficient proof to disclose a clinical profile."""
    return Response({'error': 'กรุณาติดต่อคลินิกเพื่อยืนยันเจ้าของเวชระเบียนเดิม',
                     'code': 'VERIFIED_ACTIVATION_REQUIRED'}, status=403)


@api_view(['POST'])
@permission_classes([AllowAny])
def patient_register(request):
    """Register a patient without leaving a partial account on failure."""
    try:
        return _patient_register(request)
    except Exception:
        # The traceback is written only to the server log.  Do not expose
        # database details or patient information in a public API response.
        logger.exception("Patient registration failed")
        return Response(
            {"error": "ระบบลงทะเบียนขัดข้องชั่วคราว กรุณาลองใหม่ภายหลังหรือติดต่อคลินิก"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@transaction.atomic
def _patient_register(request):
    """
    Step 2: Proceed with Wizard Registration. Create Django user and link to Patient EMR record in PostgreSQL
    """
    id_card = request.data.get("IDcard", "").strip().replace(" ", "")
    password = request.data.get("password", "")
    email = request.data.get("email", "").strip()
    birth_date_raw = (request.data.get("bd_date") or "").strip()
    birth_date = parse_date(birth_date_raw) if birth_date_raw else None
    
    is_activation_mode = request.data.get("is_activation_mode", False)
    existing_doc_id = request.data.get("existing_doc_id")

    if is_activation_mode or existing_doc_id is not None:
        return Response({'error': 'กรุณาติดต่อคลินิกเพื่อยืนยันเจ้าของเวชระเบียนเดิม',
                         'code': 'VERIFIED_ACTIVATION_REQUIRED'}, status=403)

    if not id_card or len(id_card) != 13:
        return Response({"error": "กรุณากรอกเลขบัตรประชาชนให้ครบ 13 หลัก"}, status=status.HTTP_400_BAD_REQUEST)
    
    if not password:
        return Response({"error": "กรุณากำหนดรหัสผ่าน"}, status=status.HTTP_400_BAD_REQUEST)

    if birth_date_raw and birth_date is None:
        return Response({"error": "รูปแบบวันเกิดไม่ถูกต้อง"}, status=status.HTTP_400_BAD_REQUEST)

    # A registration URL parameter does not prove control of the LINE account.
    if request.data.get('line_user_id') or request.data.get('lineUserId'):
        return Response({'error': 'กรุณายืนยันการเชื่อมบัญชี LINE กับคลินิกก่อน ไม่สามารถผูกข้ามบัญชีได้',
                         'code': 'VERIFIED_ACCOUNT_LINK_REQUIRED'}, status=400)

    # Check for existing login account vs missing EMR profile
    user = User.objects.filter(username=id_card).first()
    if user:
        has_patient = Patient.objects.filter(id_card=id_card).exists()
        if has_patient:
            return Response({"error": "เลขบัตรประชาชนนี้เคยทำการลงทะเบียนแล้ว กรุณาใช้หน้าล็อกอิน"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Repair must prove control of the original account, never reset credentials.
        authenticated = authenticate(username=id_card, password=password)
        if authenticated is None or authenticated.pk != user.pk:
            return Response({'error': 'กรุณายืนยันรหัสผ่านเดิมหรือติดต่อคลินิกเพื่อกู้บัญชี',
                             'code': 'ACCOUNT_REPAIR_AUTHENTICATION_REQUIRED'}, status=401)
        user_email = user.email
    else:
        # Create new Django User
        try:
            user_email = email if email else f"{id_card}@tspi-patient.com"
            user = User.objects.create_user(username=id_card, email=user_email, password=password)
        except Exception:
            logger.exception("Unable to create patient login account")
            return Response({"error": "ไม่สามารถสร้างบัญชีผู้ใช้ได้ กรุณาลองใหม่ภายหลัง"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Link/Create Patient profile
    patient = None
    
    if not patient:
        # Create a new patient profile
        hn = request.data.get("hn") or f"HN{secrets.token_hex(4).upper()}"
        patient = Patient.objects.create(
            legacy_id=id_card,
            hn=hn,
            id_card=id_card,
            first_name=request.data.get("fname", ""),
            last_name=request.data.get("lname", ""),
            nickname=request.data.get("nickname", ""),
            phone=request.data.get("phone", ""),
            email=user_email,
            gender=request.data.get("sex", "O"),
            birth_date=birth_date,
            address=request.data.get("address", ""),
            province=request.data.get("province", ""),
            district=request.data.get("district", ""),
            subdistrict=request.data.get("subdistrict", ""),
            postcode=request.data.get("zipcode", ""),
            status="pending"
        )
        # Store extra wizard questionnaire details
        extra_data = {}
        for field in [
            'nationality', 'ethnicity', 'marry_status', 'weight', 'height', 'smoking', 'drink',
            'time_sleep', 'time_wakeup', 'sleep_score', 'vaccinated', 'symptoms', 'disease', 
            'disease_other', 'cure_disease', 'cure_other', 'score_disease', 'score_pain', 
            'drug_current', 'drug_allergy', 'detail_disease', 'where_cure', 'long_cure', 
            'long_cure_type', 'his_medicine', 'his_antibiotic', 'quantity_medicine', 
            'purpose_medicine', 'reason', 'reason_other', 'who_regis'
        ]:
            if field in request.data:
                extra_data[field] = request.data[field]
        patient.extra_data = extra_data
        patient.save()

    # Generate JWT Tokens for Next.js login state
    tokens = get_tokens_for_user(user)

    AuditLog.objects.create(
        actor_id=id_card,
        target_id=str(patient.id),
        action="USER_REGISTRATION_SUCCESS",
        layer="AUTH",
        client_ip=get_client_ip(request),
        governance_status="PATIENT_ACCESSIBLE"
    )

    serializer = PatientSerializer(patient)
    return Response({
        "success": True,
        "tokens": tokens,
        "patient": serializer.data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def patient_login(request):
    """
    Authenticate Patient via Citizen ID or Email using Django credentials and issue JWT
    """
    auth_method = request.data.get("auth_method", "idcard") # "idcard" or "email"
    password = request.data.get("password")
    
    username = ""
    if auth_method == "idcard":
        citizen_id = request.data.get("citizenId", "").strip().replace(" ", "")
        username = citizen_id
    else:
        email = request.data.get("email", "").strip()
        # Find Django user by email
        email_users = list(User.objects.filter(email=email).order_by('pk')[:2]) if email else []
        if len(email_users) == 1:
            username = email_users[0].username
        else:
            return Response({"error": "ไม่พบบัญชีผู้ใช้งานที่ใช้อีเมลนี้"}, status=status.HTTP_400_BAD_REQUEST)

    if not username or not password:
        return Response({"error": "กรุณากรอกข้อมูลเพื่อเข้าสู่ระบบให้ครบถ้วน"}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({"error": "เลขบัตรประชาชนหรือรหัสผ่านไม่ถูกต้อง หรือคุณยังไม่ได้ทำการลงทะเบียนเปิดใช้งานบัญชีครั้งแรก"}, status=status.HTTP_401_UNAUTHORIZED)

    # Find the linked Patient profile
    patient = linked_patient_for_user(user)

    if not patient:
        return Response({"error": "พบบัญชีล็อกอินแต่ไม่มีฐานข้อมูลสุขภาพในประวัติคลินิก กรุณาติดต่อเจ้าหน้าที่"}, status=status.HTTP_404_NOT_FOUND)

    tokens = get_tokens_for_user(user)

    AuditLog.objects.create(
        actor_id=user.username,
        target_id=str(patient.id),
        action="USER_LOGIN_SUCCESS",
        layer="AUTH",
        client_ip=get_client_ip(request),
        governance_status="PATIENT_ACCESSIBLE"
    )

    serializer = PatientSerializer(patient)
    return Response({
        "success": True,
        "tokens": tokens,
        "patient": serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_me(request):
    """
    Get current logged in patient profile based on JWT Token header
    """
    user = request.user
    
    # Lookup profile
    patient = linked_patient_for_user(user)

    if not patient:
        return Response({"error": "ไม่พบโปรไฟล์แพทย์หรือคนไข้ของคุณในฐานข้อมูล"}, status=status.HTTP_404_NOT_FOUND)

    serializer = PatientSerializer(patient)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([StaffLoginThrottle, StaffLoginAccountThrottle])
def doctor_login(request):
    """Only pre-provisioned active Django staff accounts can authenticate here."""
    data = request.data
    if (not isinstance(data, dict) or set(data) != {'email', 'password'} or
            not isinstance(data.get('email'), str) or not isinstance(data.get('password'), str) or
            not data['email'].strip() or not data['password'] or
            len(data['email']) > 254 or len(data['password']) > 4096):
        return Response({'error': 'กรุณากรอกอีเมลและรหัสผ่านให้ถูกต้อง'}, status=400)
    matches = list(User.objects.filter(email__iexact=data['email'].strip()).order_by('pk')[:2])
    user = matches[0] if len(matches) == 1 else None
    authenticated_user = authenticate(username=user.username, password=data['password']) if user else None
    if not authenticated_user or not authenticated_user.is_active or not authenticated_user.is_staff:
        return Response({'error': 'อีเมล รหัสผ่าน หรือสิทธิ์บัญชีเจ้าหน้าที่ไม่ถูกต้อง'}, status=401)
    # Never read legacy plaintext/fast hashes, create users, change passwords or promote roles.
    with transaction.atomic():
        AuditLog.objects.create(
            actor_id=authenticated_user.username, target_id=str(authenticated_user.pk),
            action='DOCTOR_LOGIN_SUCCESS', layer='AUTH',
            client_ip=get_client_ip(request), governance_status='SYSTEM')
        tokens = get_tokens_for_user(authenticated_user)
    response = Response({'success': True, 'tokens': tokens, 'user': {
        'id': authenticated_user.pk, 'username': authenticated_user.username,
        'email': authenticated_user.email, 'first_name': authenticated_user.first_name,
        'last_name': authenticated_user.last_name,
        'name': f'{authenticated_user.first_name} {authenticated_user.last_name}'.strip() or authenticated_user.username,
    }})
    response['Cache-Control'] = 'no-store'
    return response


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def doctor_me(request):
    """
    Get or update current logged in doctor profile details based on JWT Token
    """
    user = request.user
    if not user.is_active or not user.is_staff:
        return Response({"error": "คุณไม่มีสิทธิ์เข้าถึงในฐานะแพทย์หรือเจ้าหน้าที่ของระบบ"}, status=status.HTTP_403_FORBIDDEN)

    if request.method in ['PUT', 'PATCH']:
        if (not isinstance(request.data, dict) or not request.data or
                not set(request.data) <= {'first_name', 'last_name'} or
                any(not isinstance(value, str) or len(value) > 150 for value in request.data.values())):
            return Response({'error': 'แก้ไขได้เฉพาะชื่อและนามสกุล การเปลี่ยนอีเมลหรือสิทธิ์ต้องติดต่อผู้ดูแล'}, status=400)
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
            
        user.save()

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "role": "doctor"
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def doctor_register(request):
    """Public self-registration must never grant staff access or clinical authority."""
    return Response({
        'error': 'กรุณาติดต่อผู้ดูแลคลินิกเพื่อจัดทำและตรวจสอบบัญชีเจ้าหน้าที่',
        'code': 'STAFF_PROVISIONING_REQUIRED',
    }, status=403)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_fcm_token(request):
    """
    Register or update the FCM token for the currently authenticated patient.
    Saves the token inside the patient's extra_data JSON field.
    """
    user = request.user
    if not user.is_active:
        return Response({'error': 'Inactive account.'}, status=403)
    if not isinstance(request.data, dict) or set(request.data) != {'fcm_token'}:
        return Response({'error': 'Invalid notification registration fields.'}, status=400)
    token = request.data.get("fcm_token")
    if not isinstance(token, str) or not token.strip() or len(token) > 4096:
        return Response({"error": "กรุณาระบุ fcm_token ในคำขอ"}, status=status.HTTP_400_BAD_REQUEST)

    patient = linked_patient_for_user(user)

    if not patient:
        return Response({"error": "ไม่พบข้อมูลโปรไฟล์คนไข้ในระบบ"}, status=status.HTTP_404_NOT_FOUND)

    if not patient.extra_data:
        patient.extra_data = {}

    patient.extra_data["fcm_token"] = token
    patient.save()

    return Response({
        "success": True,
        "message": "ลงทะเบียน FCM Token เข้าสู่ระบบ EMR สำเร็จ"
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change password for the authenticated patient/user.
    """
    user = request.user
    old_password = request.data.get("old_password")
    new_password = request.data.get("new_password")
    
    if not old_password or not new_password:
        return Response({"error": "กรุณาระบุรหัสผ่านเดิมและรหัสผ่านใหม่"}, status=status.HTTP_400_BAD_REQUEST)
        
    if not user.check_password(old_password):
        return Response({"error": "รหัสผ่านเดิมไม่ถูกต้อง"}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        user.set_password(new_password)
        user.save()
        
        # Log this event
        AuditLog.objects.create(
            actor_id=user.username,
            target_id=str(user.id),
            action="USER_PASSWORD_CHANGE_SUCCESS",
            layer="AUTH",
            client_ip=get_client_ip(request),
            governance_status="PATIENT_ACCESSIBLE"
        )
        
        return Response({
            "success": True,
            "message": "เปลี่ยนรหัสผ่านสำเร็จแล้ว"
        })
    except Exception as e:
        return Response({"error": f"ไม่สามารถเปลี่ยนรหัสผ่านได้: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

