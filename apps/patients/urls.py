from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('dashboard/', views.doctor_dashboard, name='dashboard'),
    path('patients/', views.patient_list_view, name='patient_list'),
    path('patients/new/', views.patient_create_view, name='patient_create'),
    path('patients/<int:patient_id>/', views.patient_detail_view, name='patient_detail'),
    path('patients/<int:patient_id>/edit/', views.patient_edit_view, name='patient_edit'),
    path('patients/<int:patient_id>/add-soap/', views.patient_add_soap_view, name='patient_add_soap'),
]

