from django.urls import path
from . import views

app_name = 'clinical'

urlpatterns = [
    path('axes/', views.axes_explorer_view, name='axes_explorer'),
    path('axis-graph/', views.axis_graph_view, name='axis_graph'),
    path('axis-timeline/', views.axis_timeline_view, name='axis_timeline'),
    path('therapeutic-matrix/', views.therapeutic_matrix_view, name='therapeutic_matrix'),
    path('patient/<int:patient_id>/update-score/', views.update_axis_score_htmx, name='update_score_htmx'),
]
