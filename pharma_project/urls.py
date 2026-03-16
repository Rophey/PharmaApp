"""
URL configuration for pharma_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Аутентификация
    path('', accounts_views.login_view, name='login'),
    path('logout/', accounts_views.logout_view, name='logout'),

    # Дашборды по ролям
    path('operator/', include('operator.urls', namespace='operator')),
    path('technologist/', include('technologist.urls', namespace='technologist')),
    path('chief-technologist/', include('chief_technologist.urls', namespace='chief_technologist')),
    path('qc-specialist/', include('qc_specialist.urls', namespace='qc_specialist')),
    path('qc-head/', include('qc_head.urls', namespace='qc_head')),
    path('director/', include('director.urls', namespace='director')),
    path('admin-panel/', include('admin_panel.urls', namespace='admin_panel')),
]