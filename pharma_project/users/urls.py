from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Дашборды для каждой роли
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('operator-dashboard/', views.operator_dashboard, name='operator_dashboard'),
    path('technologist-dashboard/', views.technologist_dashboard, name='technologist_dashboard'),
    path('chief-technologist-dashboard/', views.chief_technologist_dashboard, name='chief_technologist_dashboard'),
    path('qc-specialist-dashboard/', views.qc_specialist_dashboard, name='qc_specialist_dashboard'),
    path('qc-chief-dashboard/', views.qc_chief_dashboard, name='qc_chief_dashboard'),
    path('director-dashboard/', views.director_dashboard, name='director_dashboard'),

    # Администрирование
    path('admin/deactivate-user/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('admin/batch-rules/', views.batch_number_rules, name='batch_rules'),

    # Для API
    path('api/mbr/<int:mbr_id>/', views.get_mbr_parameters, name='api_mbr_detail'),
    path('api/mbr/<int:mbr_id>/edit/', views.get_mbr_for_edit, name='api_mbr_edit'),
    path('api/mbr/<int:mbr_id>/update/', views.update_mbr, name='api_mbr_update'),
    path('api/mbr/<int:mbr_id>/approve/', views.approve_mbr_api, name='api_mbr_approve'),
]