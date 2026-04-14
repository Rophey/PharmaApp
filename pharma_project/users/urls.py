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
    path('api/ebr/<int:ebr_id>/monitoring/', views.ebr_monitoring_api, name='api_ebr_monitoring'),
    path('api/technologist/monitoring/', views.technologist_monitoring_api, name='api_technologist_monitoring'),
    path('api/operator/waiting-list/', views.operator_waiting_list_api, name='api_operator_waiting_list'),
    path('api/technologist/approved-mbrs/', views.technologist_approved_mbrs_api, name='api_technologist_approved_mbrs'),
    path('api/qc/tasks/', views.qc_tasks_api, name='api_qc_tasks'),
    path('api/qc/submit/<int:task_id>/', views.qc_submit_results, name='api_qc_submit'),
    path('api/qc-chief/archive/', views.qc_chief_archive_api, name='api_qc_chief_archive'),
    path('api/qc-chief/pending/', views.qc_chief_pending_api, name='api_qc_chief_pending'),
    path('ebr/<int:pk>/reject/', views.ebr_reject, name='ebr_reject'),

    # API для панели директора
    path('api/director-stats/', views.director_stats_api, name='director_stats_api'),

    # API для администратора (справочники)
    path('api/admin/raw-materials/', views.api_admin_raw_materials, name='api_admin_raw_materials'),
    path('api/admin/products/', views.api_admin_products, name='api_admin_products'),
]