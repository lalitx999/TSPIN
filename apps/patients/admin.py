"""
Django Admin Configuration for Patients & LINE OA Caregiver Hub (Level 2).
Provides staff interface for Unified Inbox, Caregiver Bindings, and Clinical Review Queue.
"""

from django.contrib import admin
from .models import (
    Patient,
    PatientHistory,
    Appointment,
    PatientLinkingToken,
    LineUser,
    LinePatientBinding,
    CommunicationRecord,
    ClinicalReviewItem,
)


@admin.register(LineUser)
class LineUserAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'line_user_id', 'user', 'active_patient', 'last_seen_at')
    search_fields = ('display_name', 'line_user_id', 'user__username')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'last_seen_at')


@admin.register(LinePatientBinding)
class LinePatientBindingAdmin(admin.ModelAdmin):
    list_display = ('line_user', 'patient', 'role', 'status', 'verified_method', 'verified_at')
    search_fields = ('line_user__display_name', 'patient__hn', 'patient__first_name', 'patient__last_name')
    list_filter = ('status', 'role', 'verified_method')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CommunicationRecord)
class CommunicationRecordAdmin(admin.ModelAdmin):
    """Unified Inbox Admin View"""
    list_display = ('line_message_id', 'line_user', 'patient', 'direction', 'message_type', 'is_clinical_candidate', 'retention_status', 'created_at')
    search_fields = ('line_message_id', 'line_user__display_name', 'patient__hn', 'content')
    list_filter = ('direction', 'message_type', 'is_clinical_candidate', 'retention_status', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(ClinicalReviewItem)
class ClinicalReviewItemAdmin(admin.ModelAdmin):
    """Clinical Review Queue Admin View"""
    list_display = ('id', 'patient', 'review_type', 'status', 'reviewer', 'reviewer_role', 'reviewed_at', 'created_at')
    search_fields = ('patient__hn', 'patient__first_name', 'patient__last_name', 'source_message__content', 'review_notes')
    list_filter = ('status', 'review_type', 'reviewer_role', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    actions = ['approve_staff_assisted_binding']

    @admin.action(description="อนุมัติคำขอเชื่อมต่อ LINE (Staff-Assisted Fallback)")
    def approve_staff_assisted_binding(self, request, queryset):
        """เจ้าหน้าที่/พยาบาล อนุมัติการเชื่อมต่อ LINE ให้ผู้ป่วยที่เคาน์เตอร์"""
        from django.utils import timezone
        from accounts.models import AuditLog
        import re

        count = 0
        for item in queryset.filter(status=ClinicalReviewItem.StatusChoices.PENDING_REVIEW):
            text_to_search = f"{item.review_notes or ''} {item.source_message.content if item.source_message else ''}"
            # ตรวจสอบว่ามี Line User ID หรือไม่
            uid_match = re.search(r'LINE User:\s*(?:.*?)\s*\((U[0-9a-fA-F]+)\)', text_to_search)
            role_match = re.search(r'Role:\s*([A-Za-z_]+)', text_to_search)
            if uid_match:
                line_uid = uid_match.group(1)
                role = role_match.group(1) if role_match else LinePatientBinding.RoleChoices.SELF
                line_user = LineUser.objects.filter(line_user_id=line_uid).first()
                if line_user:
                    # 1. สร้าง/อัปเดต LinePatientBinding
                    binding, _ = LinePatientBinding.objects.get_or_create(
                        line_user=line_user,
                        patient=item.patient,
                        defaults={
                            'role': role,
                            'status': LinePatientBinding.StatusChoices.ACTIVE,
                            'verified_method': 'STAFF_ASSISTED',
                            'verified_at': timezone.now()
                        }
                    )
                    binding.status = LinePatientBinding.StatusChoices.ACTIVE
                    binding.verified_method = 'STAFF_ASSISTED'
                    binding.verified_at = timezone.now()
                    binding.save()

                    # 2. ล็อกข้อ 3: LineUser.active_patient ต้อง Set หลัง Bind สำเร็จเท่านั้น
                    line_user.active_patient = item.patient
                    line_user.save()

                    # 3. อัปเดต ClinicalReviewItem
                    item.status = ClinicalReviewItem.StatusChoices.APPROVED
                    item.reviewer = request.user
                    item.reviewer_role = getattr(request.user, 'role', 'STAFF')
                    item.reviewed_at = timezone.now()
                    item.save()

                    # 4. ล็อกข้อ 4: PDPA AuditLog
                    AuditLog.objects.create(
                        action='LINE_BINDING_SUCCESS',
                        user=request.user,
                        model='LinePatientBinding',
                        object_id=str(item.patient.pk),
                        client_ip=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        changes={
                            'hn': item.patient.hn,
                            'line_user_id': line_uid,
                            'approver': request.user.username,
                            'role': role,
                            'verified_method': 'STAFF_ASSISTED',
                            'review_item_id': item.pk
                        }
                    )
                    count += 1

        self.message_user(request, f"อนุมัติคำขอเชื่อมต่อ LINE สำหรับผู้ป่วย {count} รายการเรียบร้อยแล้ว")


@admin.register(PatientLinkingToken)
class PatientLinkingTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'patient', 'action_type', 'is_used', 'expires_at', 'created_at')
    search_fields = ('token', 'patient__hn', 'patient__first_name')
    list_filter = ('is_used', 'action_type', 'expires_at')
    readonly_fields = ('created_at',)
