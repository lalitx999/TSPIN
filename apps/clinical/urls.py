from django.urls import path
from . import views
from . import views_report
from . import views_copilot
from . import views_box

app_name = 'clinical'

urlpatterns = [
    # 39 Biological Axes Engine & Visualizer
    path('', views.axes_explorer_view, name='index'),
    path('axes/', views.axes_explorer_view, name='axes_explorer'),
    path('axis-graph/', views.axis_graph_view, name='axis_graph'),
    path('graph/', views.axis_graph_view, name='axis_graph_alias'),
    path('axis-timeline/', views.axis_timeline_view, name='axis_timeline'),
    path('timeline/', views.axis_timeline_view, name='axis_timeline_alias'),
    path('therapeutic-matrix/', views.therapeutic_matrix_view, name='therapeutic_matrix'),
    path('patient/<int:patient_id>/update-score/', views.update_axis_score_htmx, name='update_score_htmx'),

    # Doctor Box Portal & Break-Glass (Phase 5)
    path('boxes/', views_box.box_dashboard_view, name='box_dashboard'),
    path('boxes/<uuid:box_id>/', views_box.box_detail_view, name='box_detail'),
    path('boxes/<uuid:box_id>/unlock/', views_box.box_unlock_action, name='box_unlock'),
    path('boxes/<uuid:box_id>/decision/', views_box.box_decision_action, name='box_decision'),
    path('boxes/<uuid:box_id>/break-glass/', views_box.box_break_glass_action, name='box_break_glass'),

    # Precision Reports & WeasyPrint PDF Generation (EP 6)
    path('reports/', views_report.report_dashboard_view, name='report_dashboard'),
    path('reports/create/<int:patient_id>/', views_report.report_create_view, name='report_create'),
    path('reports/<int:analysis_id>/preview/', views_report.report_preview_html_view, name='report_preview'),
    path('reports/<int:analysis_id>/pdf/', views_report.report_download_pdf_view, name='report_pdf'),
    path('reports/<int:pk>/download-pdf/', views_report.report_download_pdf_view, name='report_download_pdf'),
    path('reports/<int:analysis_id>/signoff/', views_report.report_signoff_action_view, name='report_signoff'),

    # AI Copilot Streaming (Option 4)
    path('api/copilot/stream/', views_copilot.copilot_stream_chat_view, name='copilot_stream'),
]

