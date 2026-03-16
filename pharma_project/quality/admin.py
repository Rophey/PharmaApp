from django.contrib import admin
from .models import QCTask, QCResult, Deviation


@admin.register(QCTask)
class QCTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'ebr', 'task_type', 'status', 'assigned_to', 'due_date')
    list_filter = ('task_type', 'status')
    search_fields = ('ebr__batch_number',)
    date_hierarchy = 'due_date'

    fieldsets = (
        ('Основная информация', {
            'fields': ('ebr', 'task_type', 'status', 'assigned_to', 'created_by')
        }),
        ('Сроки', {
            'fields': ('due_date', 'completed_at')
        }),
    )


@admin.register(QCResult)
class QCResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'submitted_by', 'submitted_at')
    list_filter = ('submitted_at',)
    search_fields = ('task__ebr__batch_number',)


@admin.register(Deviation)
class DeviationAdmin(admin.ModelAdmin):
    list_display = ('id', 'ebr', 'deviation_type', 'parameter_name', 'detected_at', 'resolved_by')
    list_filter = ('deviation_type',)
    search_fields = ('ebr__batch_number', 'parameter_name')
    date_hierarchy = 'detected_at'

    fieldsets = (
        ('Информация об отклонении', {
            'fields': ('ebr', 'deviation_type', 'parameter_name', 'description')
        }),
        ('Значения', {
            'fields': ('expected_value', 'actual_value', 'tolerance')
        }),
        ('Кто обнаружил', {
            'fields': ('detected_by', 'detected_at')
        }),
        ('Решение', {
            'fields': ('action_taken', 'action_comment', 'resolved_by', 'resolved_at')
        }),
    )