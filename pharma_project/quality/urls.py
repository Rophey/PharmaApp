from django.urls import path
from . import views

app_name = 'quality'

urlpatterns = [
    path('tasks/', views.qc_tasks, name='qc_tasks'),
    path('task/<int:pk>/', views.qc_task_detail, name='qc_task_detail'),
    path('task/<int:pk>/submit/', views.qc_submit_results, name='qc_submit_results'),
    path('deviations/', views.deviation_list, name='deviation_list'),
    path('deviation/<int:pk>/resolve/', views.deviation_resolve, name='deviation_resolve'),
]
