from django import forms
from .models import MBR, Product, Parameter, RawMaterial
import re


class MBRForm(forms.ModelForm):
    product_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Наименование продукта'
    )
    product_code = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Код продукта'
    )
    operations = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        required=True,
        label='Описание технологических операций'
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=False,
        label='Комментарий к версии'
    )
    attachments = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'multiple': True}),
        label='Прикрепленные файлы'
    )

    # Параметры процесса
    pressure_value = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Усилие прессования'
    )
    pressure_tolerance = forms.DecimalField(
        max_digits=5, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Допустимое отклонение (%)'
    )
    pressure_critical = forms.DecimalField(
        max_digits=5, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Критическое отклонение (%)'
    )

    class Meta:
        model = MBR
        fields = []

    def clean_product_name(self):
        """ТЗ 4.2.2.1.1 п.2.a"""
        value = self.cleaned_data.get('product_name')
        pattern = r'^[а-яА-Яa-zA-Z0-9]+$'
        if not re.match(pattern, value):
            raise forms.ValidationError(
                'Поле «Наименование продукта» может содержать только латинские буквы, русские буквы и цифры и не может быть пустым'
            )
        return value

    def clean_product_code(self):
        """ТЗ 4.2.2.1.1 п.2.b"""
        value = self.cleaned_data.get('product_code')
        pattern = r'^[a-zA-Z0-9\-]+$'
        if not re.match(pattern, value):
            raise forms.ValidationError(
                'Поле «Код продукта» может содержать только латинские буквы, цифры, минус (-) и не может быть пустым'
            )
        return value

    def clean_operations(self):
        """ТЗ 4.2.2.1.1 п.2.g"""
        value = self.cleaned_data.get('operations')
        pattern = r'^[а-яА-Яa-zA-Z0-9\s\.,;:\-\(\)]+$'
        if not re.match(pattern, value):
            raise forms.ValidationError('Используются неразрешённые символы')
        return value

    def clean_comments(self):
        """ТЗ 4.2.2.1.1 п.2.j"""
        value = self.cleaned_data.get('comments')
        if value:
            pattern = r'^[а-яА-Яa-zA-Z0-9\s\.,;:\-\(\)]+$'
            if not re.match(pattern, value):
                raise forms.ValidationError('Используются неразрешённые символы')
        return value

    def is_complete(self):
        """ТЗ 4.2.2.1.1 п.2.l - проверка полноты данных"""
        required_fields = ['product_name', 'product_code', 'operations',
                           'pressure_value', 'pressure_tolerance', 'pressure_critical']
        for field in required_fields:
            if not self.cleaned_data.get(field):
                return False
        return True

    def save(self, commit=True):
        """Сохранение MBR с созданием связанных объектов"""
        mbr = super().save(commit=False)

        # Создание или получение продукта
        product, _ = Product.objects.get_or_create(
            product_code=self.cleaned_data['product_code'],
            defaults={'product_name': self.cleaned_data['product_name']}
        )
        mbr.product = product

        if commit:
            mbr.save()

            # Создание параметров
            Parameter.objects.create(
                parameter_name='Усилие прессования (кН)',
                unit='кН',
                value=self.cleaned_data['pressure_value'],
                tolerance=self.cleaned_data['pressure_tolerance'],
                critical_deviation=self.cleaned_data['pressure_critical']
            )

        return mbr