from django.contrib import admin
from .models import PressMachine, EquipmentReading


@admin.register(PressMachine)
class PressMachineAdmin(admin.ModelAdmin):
    list_display = ('machine_code', 'name', 'is_active', 'last_maintenance')
    list_filter = ('is_active',)
    search_fields = ('machine_code', 'name')


@admin.register(EquipmentReading)
class EquipmentReadingAdmin(admin.ModelAdmin):
    list_display = ('machine', 'timestamp', 'pressure_force', 'tablet_thickness', 'tablet_weight')
    list_filter = ('machine',)
    search_fields = ('machine__machine_code',)
    date_hierarchy = 'timestamp'
