from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('operator-dashboard/', views.operator_dashboard, name='operator_dashboard'),
    path('technologist-dashboard/', views.technologist_dashboard, name='technologist_dashboard'),
    path('chief-technologist-dashboard/', views.chief_technologist_dashboard, name='chief_technologist_dashboard'),
    path('qc-specialist-dashboard/', views.qc_specialist_dashboard, name='qc_specialist_dashboard'),
    path('qc-chief-dashboard/', views.qc_chief_dashboard, name='qc_chief_dashboard'),
    path('director-dashboard/', views.director_dashboard, name='director_dashboard'),
]