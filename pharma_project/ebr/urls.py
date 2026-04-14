from django.urls import path
from . import views

app_name = 'ebr'

urlpatterns = [
    path('', views.ebr_list, name='ebr_list'),
    path('create/<int:mbr_id>/', views.ebr_create, name='ebr_create'),
    path('<int:pk>/', views.ebr_detail, name='ebr_detail'),
    path('<int:pk>/start/', views.ebr_start, name='ebr_start'),
    path('<int:pk>/start-pressing/', views.ebr_start_pressing, name='ebr_start_pressing'),
    path('<int:pk>/sign/', views.ebr_sign, name='ebr_sign'),
    path('<int:pk>/complete-operation/', views.complete_operation, name='complete_operation'),
    path('<int:pk>/add-data/', views.ebr_add_data, name='ebr_add_data'),
    # API endpoints
    path('api/create/<int:mbr_id>/', views.ebr_create, name='ebr_create'),
]