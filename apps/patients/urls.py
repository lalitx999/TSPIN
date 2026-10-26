from django.urls import path
from . import views
from . import views_staff
import clinical.views as clinical_views
import clinical.views_report as report_views
import intelligence.views as intel_views

app_name = 'patients'

urlpatterns = [
    # Dashboard & EMR Patient Roster
    path('', views.doctor_dashboard, name='dashboard'),
    path('dashboard/', views.doctor_dashboard, name='dashboard'),
    path('patients/', views.patient_list_view, name='patient_list'),
    path('patients/new/', views.patient_create_view, name='patient_create'),
    path('patients/create/', views.patient_create_view, name='patient_create_alias'),
    path('patients/<int:patient_id>/', views.patient_detail_view, name='patient_detail'),
    path('patients/<int:patient_id>/edit/', views.patient_edit_view, name='patient_edit'),
    path('patients/<int:patient_id>/add-soap/', views.patient_add_soap_view, name='patient_add_soap'),
    path('api/search/', views.api_patient_search, name='api_patient_search'),
    path('patients/api/search/', views.api_patient_search, name='api_patient_search_alias'),

    # Clinical Visits & Operations (Fix 404s)
    path('pre-visit/', views.doctor_pre_visit, name='doctor_pre_visit'),
    path('appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('clinical-review/', views.doctor_clinical_review, name='doctor_clinical_review'),
    path('outcomes/', views.doctor_outcomes, name='doctor_outcomes'),
    path('voice-form/', views.doctor_voice_form, name='doctor_voice_form'),

    # 38 Biological Axes & Formulations
    path('axes/', clinical_views.axes_explorer_view, name='doctor_axes'),
    path('axes-mapping/', views.doctor_axes_mapping, name='doctor_axes_mapping'),
    path('axis-graph/', clinical_views.axis_graph_view, name='doctor_axis_graph'),
    path('axis-timeline/', clinical_views.axis_timeline_view, name='doctor_axis_timeline'),
    path('modules/', views.doctor_modules, name='doctor_modules'),
    path('therapeutic-matrix/', clinical_views.therapeutic_matrix_view, name='doctor_therapeutic_matrix'),
    path('digital-twin/', views.doctor_digital_twin, name='doctor_digital_twin'),

    # AI Intelligence, Lab OCR & Clinical RAG
    path('ai-physician/', intel_views.ai_physician_view, name='doctor_ai_physician'),
    path('lab-ocr/', intel_views.lab_ocr_view, name='doctor_lab_ocr'),
    path('lab-review/', views.doctor_lab_review, name='doctor_lab_review'),
    path('knowledge-rag/', views.doctor_knowledge_rag, name='doctor_knowledge_rag'),
    path('tspi-brain/', views.doctor_tspi_brain, name='doctor_tspi_brain'),
    path('artifact-review/', intel_views.artifact_review_view, name='doctor_artifact_review'),
    path('chats/', views.doctor_chats, name='doctor_chats'),

    # Reports, PDPA Audit & Settings
    path('precision-report/', report_views.report_dashboard_view, name='doctor_precision_report'),
    path('audit/', views.doctor_audit, name='doctor_audit'),
    path('settings/', views.doctor_settings, name='doctor_settings'),

    # Option C: Staff UI (Unified Inbox & Clinical Review Queue)
    path('staff/', views_staff.staff_dashboard_view, name='staff_dashboard'),
    path('inbox/', views_staff.staff_inbox_view, name='staff_inbox'),
    path('review-queue/', views_staff.staff_review_queue_view, name='staff_review_queue'),
    path('api/inbox/create-review-item/', views_staff.staff_create_review_from_message_api, name='api_create_review_from_message'),
    path('api/review-queue/poll/', views_staff.staff_review_queue_poll_api, name='api_review_queue_poll'),
    path('api/review-item/<int:item_id>/approve/', views_staff.staff_approve_review_item_api, name='api_approve_review_item'),
    path('api/review-item/<int:item_id>/reject/', views_staff.staff_reject_review_item_api, name='api_reject_review_item'),
]
