from django.contrib import admin
from .models import Action, AuditLog, ElectronicSignature


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'action_name')  # используем pk вместо конкретного имени
    search_fields = ('action_name',)
    ordering = ('action_name',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'action', 'document', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__login', 'user__last_name', 'comment')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ElectronicSignature)
class ElectronicSignatureAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'document', 'signature_date')
    list_filter = ('signature_date',)
    search_fields = ('user__login', 'document__document_id')
    date_hierarchy = 'signature_date'
    readonly_fields = ('signature_date', 'signature_hash')

    def has_add_permission(self, request):
        return False