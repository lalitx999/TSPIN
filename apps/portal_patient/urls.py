"""
Patient Portal & LINE OA URL Configuration.
"""

from django.urls import path
from . import views
from patients.views_portal import (
    portal_login_view,
    portal_logout_view,
    portal_dashboard_view,
    portal_report_detail_view,
    portal_appointments_view,
    portal_create_line_token_view
)
from patients.views_line import (
    line_webhook_view,
    line_account_binding_callback_view
)
from patients.views_liff import (
    liff_binding_page_view,
    liff_request_otp_api,
    liff_verify_otp_api,
    liff_request_staff_assisted_api,
)

app_name = 'portal_patient'

urlpatterns = [
    # Primary Patient Dashboard
    path('', views.patient_dashboard, name='dashboard'),
    path('dashboard/', views.patient_dashboard, name='dashboard'),

    # Patient Experience & AI Intake Routes (Prevent 404s)
    path('ai-intake/', views.patient_ai_intake, name='patient_ai_intake'),
    path('checkin/', views.patient_checkin, name='patient_checkin'),
    path('checkin/<str:session_id>/', views.patient_checkin, name='patient_checkin_session'),
    path('axes-result/', views.patient_axes_result, name='patient_axes_result'),
    path('digital-twin/', views.patient_digital_twin, name='patient_digital_twin'),
    path('history/', views.patient_history, name='patient_history'),
    path('download/', views.patient_download, name='patient_download'),
    path('rewards/', views.patient_rewards, name='patient_rewards'),
    path('settings/', views.patient_settings, name='patient_settings'),
    path('consent/', views.patient_consent, name='patient_consent'),

    # Mobile-First Wellness Portal Views
    path('portal/', portal_dashboard_view, name='portal_dashboard'),
    path('login/', portal_login_view, name='portal_login'),
    path('logout/', portal_logout_view, name='portal_logout'),

    # Clinical Reports & Appointments
    path('reports/<int:pk>/', portal_report_detail_view, name='portal_report_detail'),
    path('appointments/', portal_appointments_view, name='portal_appointments'),

    # LINE Integration & Webhook (Pillars 8, 14)
    path('webhook/', line_webhook_view, name='line_webhook'),
    path('line/webhook/', line_webhook_view, name='line_webhook_alias'),
    path('line/bind/', portal_create_line_token_view, name='portal_line_binding'),
    path('line/confirm/', line_account_binding_callback_view, name='line_binding_confirm'),

    # Level 2 LIFF 2-Step Identity & Caregiver Hub (Pillars 1, 14)
    path('line/liff/', liff_binding_page_view, name='liff_binding_page'),
    path('line/liff/request-otp/', liff_request_otp_api, name='liff_request_otp_api'),
    path('line/liff/verify-otp/', liff_verify_otp_api, name='liff_verify_otp_api'),
    path('line/liff/request-staff-assisted/', liff_request_staff_assisted_api, name='liff_request_staff_assisted_api'),
]
