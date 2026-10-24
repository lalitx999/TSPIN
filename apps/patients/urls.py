from django.urls import path
from . import views
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
    path('patients/<int:patient_id>/', views.patient_detail_view, name='patient_detail'),
    path('patients/<int:patient_id>/edit/', views.patient_edit_view, name='patient_edit'),
    path('patients/<int:patient_id>/add-soap/', views.patient_add_soap_view, name='patient_add_soap'),

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
]
