from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),  # это должно быть
    path('mbr/', include('mbr.urls')),
    path('ebr/', include('ebr.urls')),
    path('quality/', include('quality.urls')),
    path('audit/', include('audit.urls')),
    path('reports/', include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)