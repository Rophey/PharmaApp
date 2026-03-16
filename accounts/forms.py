from django import forms
from django.contrib.auth.forms import AuthenticationForm
import re


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
        help_text='Латинские буквы, цифры, _ (8-15 символов)'
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}),
        help_text='Латинские буквы, цифры, спецсимволы (8-15 символов)'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        pattern = r'^[a-zA-Z0-9_]{8,15}$'
        if not re.match(pattern, username):
            raise forms.ValidationError(
                'Логин может содержать только латинские буквы, цифры, технический пробел и быть в длину 8-15 символов'
            )
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        pattern = r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]{8,15}$'
        if not re.match(pattern, password):
            raise forms.ValidationError(
                'Пароль может содержать только латинские буквы, цифры и специальные символы и быть в длину 8-15 символов'
            )
        return password