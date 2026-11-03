"""
เชื่อมบัญชี LINE แบบง่าย: ชื่อ เบอร์โทร ยินยอม ส่งแล้วใช้บอทได้ทันที ไม่ต้องรออนุมัติ ไม่ต้องใช้ LIFF
รู้ว่าเป็น LINE คนไหนจากลิงก์ที่ลงนามซึ่งบอทส่งให้ในแชท ส่วนเบอร์ที่กรอกพิสูจน์ตัวตนไม่ได้
จึงเปิดเวชระเบียนใหม่เสมอ ถ้าเบอร์ตรงกับคนไข้เดิมให้เจ้าหน้าที่ตรวจทีหลัง ไม่งั้นใครรู้เบอร์ก็เห็นผลตรวจของคนอื่นได้
"""

import uuid

from django import forms
from django.db import transaction
from django.db.models import Value
from django.db.models.functions import Replace
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from accounts.models import AuditLog
from accounts.views import get_client_ip
from patients.line_service import LineMessagingService, read_line_register_token
from patients.models import ClinicalReviewItem, CommunicationRecord, LinePatientBinding, LineUser, Patient
from patients.views_line import _resolve_patient, _set_bot_enabled, welcome_card
from patients.views_liff import _next_hn


class LineRegisterForm(forms.Form):
    full_name = forms.CharField(max_length=150, error_messages={'required': 'กรุณากรอกชื่อ-นามสกุล'})
    phone = forms.CharField(max_length=20, error_messages={'required': 'กรุณากรอกเบอร์โทรศัพท์'})
    consent = forms.BooleanField(error_messages={'required': 'กรุณากดยอมรับก่อนส่งข้อมูล'})

    def clean_phone(self):
        phone = self.cleaned_data['phone'].replace('-', '').replace(' ', '')
        if not (phone.isdigit() and phone.startswith('0') and 9 <= len(phone) <= 10):
            raise forms.ValidationError('เบอร์โทรศัพท์ไม่ถูกต้อง')
        return phone


def _find_by_phone(phone: str):
    return (
        Patient.objects.alive()
        .annotate(phone_norm=Replace(Replace('phone', Value('-'), Value('')), Value(' '), Value('')))
        .filter(phone_norm=phone)
        .first()
    )


def _create_and_bind(request: HttpRequest, line_user: LineUser, full_name: str, phone: str, duplicate_of) -> Patient:
    first_name, _, last_name = full_name.partition(' ')
    extra_data = {'registered_via': 'line_form', 'needs_staff_verification': True,
                  'pdpa_consent_at': timezone.now().isoformat()}
    if duplicate_of:
        extra_data['possible_duplicate_of_hn'] = duplicate_of.hn
    patient = Patient.objects.create(
        hn=_next_hn(), first_name=first_name[:100], last_name=last_name[:100], phone=phone, status='pending',
        line_user_id=line_user.line_user_id, extra_data=extra_data,
    )
    LinePatientBinding.objects.create(
        line_user=line_user, patient=patient, role=LinePatientBinding.RoleChoices.SELF,
        status=LinePatientBinding.StatusChoices.ACTIVE, verified_method='SELF_FORM', verified_at=timezone.now(),
    )
    line_user.active_patient = patient
    line_user.save(update_fields=['active_patient', 'last_seen_at'])
    AuditLog.objects.create(user=None, action='PATIENT_SELF_REGISTERED_LINE', model='Patient', object_id=str(patient.pk),
                            changes={'hn': patient.hn, 'line_user_id': line_user.line_user_id},
                            client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500])
    return patient


def _flag_possible_duplicate(request: HttpRequest, line_user: LineUser, existing: Patient, new: Patient) -> None:
    """รูปแบบข้อความเดียวกับคำขอ Staff-Assisted: ปุ่มอนุมัติใน Django Admin จะย้าย LINE นี้ไปเวชระเบียนเดิม"""
    note = (f"เบอร์จากฟอร์มลงทะเบียน LINE ตรงกับเวชระเบียนเดิม:\nLINE User: {new.full_name} ({line_user.line_user_id})\n"
            f"Role: {LinePatientBinding.RoleChoices.SELF}\nเบอร์ที่กรอก: {new.phone}\nเปิดเวชระเบียนใหม่ {new.hn} ให้แล้ว\n"
            f"ถ้าตรวจแล้วเป็นคนเดียวกับ {existing.hn} ให้กดอนุมัติ LINE นี้จะเห็นข้อมูลของ {existing.hn}")
    record = CommunicationRecord.objects.create(
        line_message_id=f"staff_req_{uuid.uuid4().hex[:16]}", line_user=line_user, patient=existing,
        direction=CommunicationRecord.DirectionChoices.INCOMING,
        message_type=CommunicationRecord.MessageTypeChoices.TEXT,
        content=note, is_clinical_candidate=True,
        raw_payload={'typed_name': new.full_name, 'typed_phone': new.phone, 'new_hn': new.hn},
    )
    item = ClinicalReviewItem.objects.create(
        patient=existing, source_message=record, review_type=ClinicalReviewItem.ReviewTypeChoices.LEVEL_1_INTAKE,
        status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW, review_notes=note,
    )
    AuditLog.objects.create(user=None, action='LINE_STAFF_ASSISTED_REQUESTED', model='ClinicalReviewItem',
                            object_id=str(item.pk),
                            changes={'hn': existing.hn, 'new_hn': new.hn, 'line_user_id': line_user.line_user_id,
                                     'via': 'line_form'},
                            client_ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:500])


@ratelimit(key='ip', rate='10/m', method='POST', block=False)
@require_http_methods(['GET', 'POST'])
def line_register_view(request: HttpRequest) -> HttpResponse:
    template = 'patients/line_register.html'
    line_user_id = read_line_register_token(request.GET.get('t', ''))
    if not line_user_id:
        return render(request, template, {'state': 'invalid'}, status=400)

    line_user, _ = LineUser.objects.get_or_create(line_user_id=line_user_id, defaults={'display_name': 'LINE User'})
    if _resolve_patient(line_user_id):
        return render(request, template, {'state': 'bound'})

    form = LineRegisterForm(request.POST or None)
    if request.method != 'POST':
        return render(request, template, {'state': 'form', 'form': form})
    if getattr(request, 'limited', False):
        form.add_error(None, 'ส่งข้อมูลบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่')
        return render(request, template, {'state': 'form', 'form': form}, status=429)
    if not form.is_valid():
        return render(request, template, {'state': 'form', 'form': form})

    full_name = ' '.join(form.cleaned_data['full_name'].split())
    phone = form.cleaned_data['phone']
    with transaction.atomic():
        # ล็อกแถวนี้ไว้ กดส่งซ้ำพร้อมกันจะได้ไม่เปิดเวชระเบียนสองใบ
        line_user = LineUser.objects.select_for_update().get(pk=line_user.pk)
        if _resolve_patient(line_user_id):
            return redirect(request.get_full_path())
        existing = _find_by_phone(phone)
        patient = _create_and_bind(request, line_user, full_name, phone, existing)
        if existing:
            _flag_possible_duplicate(request, line_user, existing, patient)
        _set_bot_enabled(request, line_user, True, patient)

    LineMessagingService.push_message(line_user_id, [welcome_card(patient)])
    return redirect(request.get_full_path())
