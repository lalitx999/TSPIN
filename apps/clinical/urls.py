from django.urls import path
from . import views
from . import views_report

app_name = 'clinical'

urlpatterns = [
    # 39 Biological Axes Engine & Visualizer
    path('axes/', views.axes_explorer_view, name='axes_explorer'),
    path('axis-graph/', views.axis_graph_view, name='axis_graph'),
    path('axis-timeline/', views.axis_timeline_view, name='axis_timeline'),
    path('therapeutic-matrix/', views.therapeutic_matrix_view, name='therapeutic_matrix'),
    path('patient/<int:patient_id>/update-score/', views.update_axis_score_htmx, name='update_score_htmx'),

    # Precision Reports & WeasyPrint PDF Generation (EP 6)
    path('reports/', views_report.report_dashboard_view, name='report_dashboard'),
    path('reports/create/<int:patient_id>/', views_report.report_create_view, name='report_create'),
    path('reports/<int:analysis_id>/preview/', views_report.report_preview_html_view, name='report_preview'),
    path('reports/<int:analysis_id>/pdf/', views_report.report_download_pdf_view, name='report_pdf'),
    path('reports/<int:pk>/download-pdf/', views_report.report_download_pdf_view, name='report_download_pdf'),
    path('reports/<int:analysis_id>/signoff/', views_report.report_signoff_action_view, name='report_signoff'),
]

