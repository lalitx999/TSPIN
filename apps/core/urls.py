from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('platform/', views.platform_view, name='platform'),
    path('protocol/', views.protocol_view, name='protocol'),
    path('research/', views.research_view, name='research'),
    path('about/', views.about, name='about'),
    path('guide/', views.guide_view, name='guide'),
    path('install/', views.install_view, name='install'),
    path('legal/privacy/', views.privacy_policy, name='privacy'),
    path('legal/terms/', views.terms_of_service, name='terms'),
    path('health/', views.health_check_view, name='health'),
    path('healthz/', views.health_check_view, name='healthz'),
]
