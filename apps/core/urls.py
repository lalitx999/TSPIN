from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('articles/', views.article_list_view, name='article_list'),
    path('articles/<slug:slug>/', views.article_detail_view, name='article_detail'),
    path('news/', views.article_list_view, name='news_alias'),
    path('platform/', views.platform_view, name='platform'),

    path('protocol/', views.protocol_view, name='protocol'),
    path('research/', views.research_view, name='research'),
    path('about/', views.about, name='about'),
    path('guide/', views.guide_view, name='guide'),
    path('install/', views.install_view, name='install'),
    path('legal/privacy/', views.privacy_policy, name='privacy'),
    path('privacy/', views.privacy_policy, name='privacy_alias'),
    path('legal/terms/', views.terms_of_service, name='terms'),
    path('terms/', views.terms_of_service, name='terms_alias'),
    path('health/', views.health_check_view, name='health'),
    path('healthz/', views.health_check_view, name='healthz'),
]
