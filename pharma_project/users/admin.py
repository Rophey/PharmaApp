from django.contrib import admin
from django.contrib.auth.hashers import make_password
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('login', 'last_name', 'first_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('login', 'last_name', 'first_name')
    ordering = ('-created_at',)

    fieldsets = (
        ('Учетные данные', {
            'fields': ('login', 'password', 'role')
        }),
        ('Персональная информация', {
            'fields': ('last_name', 'first_name', 'middle_name')
        }),
        ('Статус', {
            'fields': ('is_active', 'is_superuser')
        }),
    )

    def save_model(self, request, obj, form, change):
        if 'password' in form.changed_data:
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)