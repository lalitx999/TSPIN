from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.doctor_login_view, name='login'),
    path('doctor/login/', views.doctor_login_view, name='doctor_login'),
    path('patient/login/', views.patient_login_view, name='patient_login'),
    path('patient/register/', views.patient_register_view, name='patient_register'),
    path('logout/', views.user_logout_view, name='logout'),
    path('password/change/', views.password_change_view, name='password_change'),
    path('lockout/', views.lockout_view, name='lockout'),
]
