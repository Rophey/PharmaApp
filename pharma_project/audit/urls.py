from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.audit_log, name='audit_log'),
    path('signatures/', views.signature_list, name='signature_list'),
    path('sign/<int:doc_id>/', views.sign_document, name='sign_document'),
]
