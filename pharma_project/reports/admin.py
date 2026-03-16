from django.contrib import admin
from .models import ReportTemplate, GeneratedReport, ProductionStats


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'report_type', 'is_active', 'created_at')
    list_filter = ('report_type', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('is_active',)


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'template', 'generated_by', 'generated_at', 'format')
    list_filter = ('template__report_type', 'format', 'generated_at')
    search_fields = ('generated_by__login',)
    date_hierarchy = 'generated_at'
    readonly_fields = ('generated_at', 'data')

    def has_add_permission(self, request):
        return False


@admin.register(ProductionStats)
class ProductionStatsAdmin(admin.ModelAdmin):
    list_display = ('id', 'ebr', 'total_units', 'defect_units', 'defect_percentage', 'raw_material_used')
    list_filter = ('ebr__status',)
    search_fields = ('ebr__batch_number',)