from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_list, name='report_list'),
    path('generate/<str:report_type>/', views.generate_report, name='generate_report'),
    path('download/<int:report_id>/', views.download_report, name='download_report'),
]