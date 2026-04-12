from django.urls import path
from . import views

app_name = 'mbr'

urlpatterns = [
    path('', views.mbr_list, name='mbr_list'),
    path('create/', views.mbr_create, name='mbr_create'),
    path('<int:pk>/', views.mbr_detail, name='mbr_detail'),
    path('<int:pk>/edit/', views.mbr_edit, name='mbr_edit'),
    path('<int:pk>/approve/', views.mbr_approve, name='mbr_approve'),
    path('<int:pk>/new-version/', views.mbr_new_version, name='mbr_new_version'),
    path('<int:pk>/delete/', views.mbr_delete, name='mbr_delete'),
]