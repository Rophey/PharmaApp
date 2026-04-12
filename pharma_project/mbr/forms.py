from django import forms
import re
from .models import MBR, Product, RawMaterial, Parameter


class MBRForm(forms.Form):
    """Форма создания/редактирования MBR"""
    product_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Наименование продукта'})
    )
    product_code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Код продукта'})
    )
    operations = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'placeholder': 'Описание технологических операций'})
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Комментарий к версии'})
    )
    raw_materials = forms.ModelMultipleChoiceField(
        queryset=RawMaterial.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    def clean_product_name(self):
        product_name = self.cleaned_data.get('product_name')
        # Латиница + кириллица + цифры, не пустое
        if not product_name or not re.match(r'^[a-zA-Zа-яА-Я0-9]+$', product_name):
            raise forms.ValidationError(
                'Поле «Наименование продукта» может содержать только латинские буквы, русские буквы и цифры и не может быть пустым'
            )
        return product_name

    def clean_product_code(self):
        product_code = self.cleaned_data.get('product_code')
        # Латиница + цифры + минус, не пустое
        if not product_code or not re.match(r'^[a-zA-Z0-9-]+$', product_code):
            raise forms.ValidationError(
                'Поле «Код продукта» может содержать только латинские буквы, цифры, минус (-) и не может быть пустым'
            )
        return product_code

    def clean_operations(self):
        operations = self.cleaned_data.get('operations')
        # Латиница + кириллица + цифры + спецсимволы
        if operations and not re.match(r'^[a-zA-Zа-яА-Я0-9\s\-._,;:!?()]+$', operations):
            raise forms.ValidationError('Используются неразрешённые символы')
        return operations

    def clean_comments(self):
        comments = self.cleaned_data.get('comments')
        if comments and not re.match(r'^[a-zA-Zа-яА-Я0-9\s\-._,;:!?()]+$', comments):
            raise forms.ValidationError('Используются неразрешённые символы')
        return comments


class ParameterForm(forms.Form):
    """Форма для параметров MBR"""
    value = forms.DecimalField(
        min_value=0.01,
        widget=forms.NumberInput(attrs={'placeholder': '> 0', 'step': '0.01'})
    )
    tolerance = forms.DecimalField(
        min_value=0.01,
        widget=forms.NumberInput(attrs={'placeholder': '%', 'step': '0.01'})
    )
    critical_deviation = forms.DecimalField(
        min_value=0.01,
        widget=forms.NumberInput(attrs={'placeholder': '%', 'step': '0.01'})
    )
