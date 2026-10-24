from django.urls import path
from . import views

app_name = 'portal_patient'

urlpatterns = [
    path('dashboard/', views.patient_dashboard, name='dashboard'),
]
