"""Link authenticated clinic accounts using server-verified LINE access tokens."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from .models import AuditLog, Patient, VerifiedLineBinding


class LineVerificationUnavailable(Exception):
    pass


def _line_json(request):
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError('Oversized response')
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError('Invalid response')
        return result
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 401, 403):
            raise ValidationError('LINE_TOKEN_INVALID') from None
        raise LineVerificationUnavailable() from None
    except (OSError, ValueError):
        raise LineVerificationUnavailable() from None


def verify_line_access_token(token):
    channel_id = os.environ.get('LINE_LOGIN_CHANNEL_ID', '').strip()
    if not channel_id:
        raise LineVerificationUnavailable()
    if not isinstance(token, str) or not token or len(token) > 4096 or any(c.isspace() for c in token):
        raise ValidationError('LINE_TOKEN_INVALID')
    verified = _line_json(urllib.request.Request(
        'https://api.line.me/oauth2/v2.1/verify?' + urllib.parse.urlencode({'access_token': token})))
    if (verified.get('client_id') != channel_id or type(verified.get('expires_in')) is not int
            or verified['expires_in'] <= 0 or not isinstance(verified.get('scope'), str)
            or 'profile' not in verified['scope'].split()):
        raise ValidationError('LINE_TOKEN_INVALID')
    profile = _line_json(urllib.request.Request('https://api.line.me/v2/profile',
        headers={'Authorization': 'Bearer ' + token}))
    user_id = profile.get('userId')
    if not isinstance(user_id, str) or len(user_id) != 33 or user_id[0] != 'U' or any(
            c not in '0123456789abcdefABCDEF' for c in user_id[1:]):
        raise ValidationError('LINE_PROFILE_INVALID')
    return user_id


def link_verified_line(*, actor, password, access_token):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied('Clinic authentication is required.')
    if not isinstance(password, str) or not password:
        raise PermissionDenied('Password confirmation is required.')
    confirmed = authenticate(username=actor.username, password=password)
    if confirmed is None or confirmed.pk != actor.pk:
        raise PermissionDenied('Password confirmation failed.')
    line_id = verify_line_access_token(access_token)
    try:
        with transaction.atomic():
            patients = list(Patient.objects.select_for_update().filter(id_card=actor.username).order_by('pk')[:2])
            if len(patients) != 1:
                raise ValidationError('CLINIC_PATIENT_IDENTITY_AMBIGUOUS')
            patient = patients[0]
            if patient.line_user_id and patient.line_user_id != line_id:
                raise ValidationError('LINE_LINK_CONFLICT')
            if Patient.objects.filter(line_user_id=line_id).exclude(pk=patient.pk).exists():
                raise ValidationError('LINE_LINK_CONFLICT')
            binding = VerifiedLineBinding.objects.filter(patient=patient).first()
            if binding and binding.line_user_id != line_id:
                raise ValidationError('LINE_LINK_CONFLICT')
            if not binding:
                VerifiedLineBinding.objects.create(patient=patient, line_user_id=line_id, linked_by=actor)
            patient.line_user_id = line_id
            patient.save(update_fields=['line_user_id', 'updated_at'])
            if not binding:
                AuditLog.objects.create(actor_id=str(actor.pk), target_id=str(patient.pk),
                    action='LINE_VERIFIED_LINKED', layer='AUTH', client_ip='', governance_status='VERIFIED_ACCOUNT_LINK')
            return {'success': True, 'status': 'ALREADY_LINKED' if binding else 'LINKED', 'patientId': patient.pk}
    except IntegrityError:
        raise ValidationError('LINE_LINK_CONFLICT') from None
