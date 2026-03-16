from django.contrib import admin
from .models import Product, RawMaterial, Parameter, DocumentType, Document, MBRStatus, MBR, MBRRawMaterial, \
    MBRParameter


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('pk', 'product_code', 'product_name')
    search_fields = ('product_code', 'product_name')
    ordering = ('product_code',)


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ('pk', 'material_name')
    search_fields = ('material_name',)
    ordering = ('material_name',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('pk', 'parameter_name', 'unit', 'value', 'tolerance', 'critical_deviation')
    list_filter = ('unit',)
    search_fields = ('parameter_name',)
    ordering = ('parameter_name',)


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('pk', 'type_name')
    list_filter = ('type_name',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'type')
    list_filter = ('type',)
    search_fields = ('pk',)


@admin.register(MBRStatus)
class MBRStatusAdmin(admin.ModelAdmin):
    list_display = ('pk', 'status_name')
    list_filter = ('status_name',)


class MBRRawMaterialInline(admin.TabularInline):
    model = MBRRawMaterial
    extra = 1


class MBRParameterInline(admin.TabularInline):
    model = MBRParameter
    extra = 1


@admin.register(MBR)
class MBRAdmin(admin.ModelAdmin):
    list_display = ('pk', 'product', 'version', 'status', 'approval_date', 'signed_by')
    list_filter = ('status', 'product')
    search_fields = ('product__product_code', 'product__product_name', 'version')
    date_hierarchy = 'approval_date'
    inlines = [MBRRawMaterialInline, MBRParameterInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'version', 'status', 'signed_by')
        }),
        ('Технологические данные', {
            'fields': ('operations',)
        }),
        ('Даты и комментарии', {
            'fields': ('approval_date', 'comments')
        }),
    )


@admin.register(MBRRawMaterial)
class MBRRawMaterialAdmin(admin.ModelAdmin):
    list_display = ('pk', 'mbr', 'raw_material')
    list_filter = ('mbr__product',)


@admin.register(MBRParameter)
class MBRParameterAdmin(admin.ModelAdmin):
    list_display = ('pk', 'mbr', 'parameter')
    list_filter = ('mbr__product',)