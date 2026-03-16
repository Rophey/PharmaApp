from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
import re

User = get_user_model()


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите логин',
            'id': 'loginInput',
            'maxlength': '15'
        }),
        help_text='Латинские буквы, цифры, _ (8-15 символов)'
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль',
            'id': 'passwordInput',
            'maxlength': '15'
        }),
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


class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('operator', 'Оператор цеха'),
        ('technologist', 'Технолог'),
        ('chief_technologist', 'Главный технолог'),
        ('qc_specialist', 'Сотрудник ОКК'),
        ('qc_head', 'Начальник ОКК'),
        ('director', 'Директор'),
        ('admin', 'Системный администратор'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Роль'
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Фамилия'
    )
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Имя'
    )
    middle_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Отчество'
    )

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'role', 'last_name', 'first_name', 'middle_name')