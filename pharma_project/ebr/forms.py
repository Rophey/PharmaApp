from django import forms
import re


class EBRDataForm(forms.Form):
    """Форма внесения данных в EBR"""
    inspection_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Введите результаты визуального контроля и лабораторных испытаний'
        })
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Введите комментарий'})
    )

    def clean_inspection_notes(self):
        notes = self.cleaned_data.get('inspection_notes')
        if notes and not re.match(r'^[a-zA-Zа-яА-Я0-9\s\-._,;:!?()]*$', notes):
            raise forms.ValidationError('Используются неразрешённые символы')
        return notes

    def clean_comments(self):
        comments = self.cleaned_data.get('comments')
        if comments and not re.match(r'^[a-zA-Zа-яА-Я0-9\s\-._,;:!?()]*$', comments):
            raise forms.ValidationError('Используются неразрешённые символы')
        return comments


class ParameterActualForm(forms.Form):
    """Форма для фактических значений параметров"""
    actual_value = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'placeholder': 'Фактическое значение', 'step': '0.01'})
    )
