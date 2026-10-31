"""
Main URL Configuration for Dr. Patt Clinical EMR.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from patients.views_line import line_webhook_view, line_account_binding_callback_view
from patients.views_liff import (
    liff_binding_page_view,
    liff_request_otp_api,
    liff_verify_otp_api,
    liff_request_staff_assisted_api,
    liff_register_api,
)
from patients.views_line_internal import line_internal_ingest_view
import patients.views_staff as views_staff

urlpatterns = [
    # Django Administration (Hardened with Axes)
    path('admin/', admin.site.urls),

    # Core Public Pages & Landing
    path('', include('core.urls')),

    # Unified Authentication & Session Portal
    path('accounts/', include('accounts.urls')),

    # Doctor Portal (EMR & Patients)
    path('doctor/', include('patients.urls')),

    # 39-Axis Clinical Engine & Reports
    path('clinical/', include('clinical.urls')),

    # AI Physician & Streaming Copilot
    path('ai/', include('intelligence.urls')),

    # Patient Portal & Self-service
    path('patient/', include('portal_patient.urls')),

    # Direct LINE Webhook Routes (Pillar 14)
    path('line/webhook/', line_webhook_view, name='root_line_webhook'),
    path('line/confirm/', line_account_binding_callback_view, name='root_line_confirm'),
    path('link/', line_account_binding_callback_view, name='root_line_link_alias'),
    path('liff/identity/', line_account_binding_callback_view, name='root_liff_identity_alias'),

    # Level 2 LIFF 2-Step Identity & Caregiver Hub
    path('liff/bind/', liff_binding_page_view, name='root_liff_binding_page'),
    path('liff/api/request-otp/', liff_request_otp_api, name='root_liff_request_otp_api'),
    path('liff/api/verify-otp/', liff_verify_otp_api, name='root_liff_verify_otp_api'),
    path('liff/api/request-staff-assisted/', liff_request_staff_assisted_api, name='root_liff_request_staff_assisted_api'),
    path('liff/api/register/', liff_register_api, name='root_liff_register_api'),

    # Internal Microservice Gateway (FastAPI 8088 -> Django 8000)
    path('internal/line/webhook/', line_internal_ingest_view, name='root_internal_line_webhook'),

    # Option C: Staff Portal Root Routes (/staff/)
    path('staff/', views_staff.staff_dashboard_view, name='root_staff_dashboard'),
    path('staff/dashboard/', views_staff.staff_dashboard_view, name='root_staff_dashboard_alias'),
    path('staff/inbox/', views_staff.staff_inbox_view, name='root_staff_inbox'),
    path('staff/review-queue/', views_staff.staff_review_queue_view, name='root_staff_review_queue'),
    path('staff/api/inbox/create-review-item/', views_staff.staff_create_review_from_message_api, name='root_api_create_review_from_message'),
    path('staff/inbox/reply/', views_staff.staff_inbox_reply_action, name='root_staff_inbox_reply'),
    path('staff/api/review-queue/poll/', views_staff.staff_review_queue_poll_api, name='root_api_review_queue_poll'),
    path('staff/api/review-item/<int:item_id>/approve/', views_staff.staff_approve_review_item_api, name='root_api_approve_review_item'),
    path('staff/api/review-item/<int:item_id>/reject/', views_staff.staff_reject_review_item_api, name='root_api_reject_review_item'),
]

# ในโหมด Development สามารถ serve static/media ได้
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
