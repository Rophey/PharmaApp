from django.contrib import admin
from .models import EBRStatus, EBR, EBRParameter, BatchOperation


@admin.register(EBRStatus)
class EBRStatusAdmin(admin.ModelAdmin):
    list_display = ('pk', 'status_name')
    list_filter = ('status_name',)


@admin.register(EBR)
class EBRAdmin(admin.ModelAdmin):
    list_display = ('pk', 'batch_number', 'status', 'mbr', 'operator', 'start_date', 'completion_date')
    list_filter = ('status', 'mbr__product')
    search_fields = ('batch_number', 'mbr__product__product_code')
    date_hierarchy = 'start_date'

    fieldsets = (
        ('Основная информация', {
            'fields': ('batch_number', 'status', 'mbr', 'operator')
        }),
        ('Данные контроля', {
            'fields': ('inspection_notes', 'comments', 'signed_by')
        }),
        ('Даты', {
            'fields': ('start_date', 'completion_date')
        }),
    )


@admin.register(EBRParameter)
class EBRParameterAdmin(admin.ModelAdmin):
    list_display = ('pk', 'ebr', 'parameter', 'actual_value')
    list_filter = ('ebr__status',)


@admin.register(BatchOperation)
class BatchOperationAdmin(admin.ModelAdmin):
    list_display = ('pk', 'ebr', 'operation_name', 'status', 'started_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('operation_name',)