from django.urls import path
from . import views

app_name = 'intelligence'

urlpatterns = [
    path('ai-physician/', views.ai_physician_view, name='ai_physician'),
    path('stream/', views.ai_physician_stream_api, name='ai_stream'),
    path('lab-ocr/', views.lab_ocr_view, name='lab_ocr'),
    path('artifact-review/', views.artifact_review_view, name='artifact_review'),
    path('artifact/<int:artifact_id>/action/', views.artifact_action_view, name='artifact_action'),
]
