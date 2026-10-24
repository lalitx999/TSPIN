from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('legal/privacy/', views.privacy_policy, name='privacy'),
    path('legal/terms/', views.terms_of_service, name='terms'),
    path('health/', views.health_check_view, name='health'),
    path('healthz/', views.health_check_view, name='healthz'),
]
