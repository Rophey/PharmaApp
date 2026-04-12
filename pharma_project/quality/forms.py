from django import forms
import re
from .models import QCTask, QCResult, Deviation


class QCResultForm(forms.Form):
    """Форма отправки результатов контроля"""
    visual_control = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Введите результаты визуального контроля'
        })
    )
    lab_results = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Введите результаты лабораторных испытаний'
        })
    )
    qc_files = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'multiple': True}))

    def clean_visual_control(self):
        visual = self.cleaned_data.get('visual_control')
        if not re.match(r'^[a-zA-Zа-яА-Я0-9\s\-._,;:!?()]+$', visual):
            raise forms.ValidationError('Используются неразрешённые символы')
        return visual

    def clean_lab_results(self):
        lab = self.cleaned_data.get('lab_results')
        if not re.match(r'^[a-zA-Zа-яА-Я0-9\s\-._,;:!?()]+$', lab):
            raise forms.ValidationError('Используются неразрешённые символы')
        return lab


class DeviationResolveForm(forms.Form):
    """Форма решения по отклонению"""
    action = forms.ChoiceField(
        choices=[
            ('block', 'Заблокировать партию'),
            ('rework', 'Переделать'),
            ('accept', 'Принять'),
            ('reject', 'Отклонить партию'),
        ],
        widget=forms.Select
    )
    comment = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Комментарий'})
    )
