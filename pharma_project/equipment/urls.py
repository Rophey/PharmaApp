from django.urls import path
from . import views

app_name = 'equipment'

urlpatterns = [
    path('api/machines/', views.get_machines, name='get_machines'),
    path('api/machine/<int:machine_id>/simulate/', views.simulate_reading, name='simulate_reading'),
    path('api/machine/<int:machine_id>/send/', views.send_reading, name='send_reading'),
    path('api/readings/', views.latest_readings, name='latest_readings'),
]
