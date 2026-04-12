from django import forms
import re


class LoginForm(forms.Form):
    """Форма входа в систему"""
    login = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'placeholder': 'Введите логин',
            'autocomplete': 'off'
        })
    )
    password = forms.CharField(
        max_length=255,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Введите пароль'
        })
    )

    def clean_login(self):
        login = self.cleaned_data.get('login')
        # Только латиница, цифры и _, 8-15 символов
        if not re.match(r'^[a-zA-Z0-9_]{8,15}$', login):
            raise forms.ValidationError(
                'Логин может содержать только латинские буквы, цифры, технический пробел и быть в длину 8-15 символов'
            )
        return login

    def clean_password(self):
        password = self.cleaned_data.get('password')
        # Латиница, цифры и спецсимволы, 8-15 символов
        if not re.match(r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]{8,15}$', password):
            raise forms.ValidationError(
                'Пароль может содержать только латинские буквы, цифры и специальные символы и быть в длину 8-15 символов'
            )
        return password


class UserCreationForm(forms.Form):
    """Форма создания пользователя"""
    login = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': 'Логин'})
    )
    password = forms.CharField(
        max_length=255,
        widget=forms.PasswordInput(attrs={'placeholder': 'Пароль'})
    )
    role = forms.ChoiceField(
        choices=[
            ('оператор', 'Оператор'),
            ('технолог', 'Технолог'),
            ('главный технолог', 'Главный технолог'),
            ('сотрудник ОКК', 'Сотрудник ОКК'),
            ('начальник ОКК', 'Начальник ОКК'),
            ('директор', 'Директор'),
            ('системный администратор', 'Системный администратор'),
        ],
        widget=forms.Select(attrs={'class': 'role-select'})
    )
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Фамилия'}))
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Имя'}))
    middle_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Отчество'})
    )

    def clean_login(self):
        login = self.cleaned_data.get('login')
        if not re.match(r'^[a-zA-Z0-9_]{8,15}$', login):
            raise forms.ValidationError(
                'Логин может содержать только латинские буквы, цифры, технический пробел и быть в длину 8-15 символов'
            )
        return login

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not re.match(r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]{8,15}$', password):
            raise forms.ValidationError(
                'Пароль может содержать только латинские буквы, цифры и специальные символы и быть в длину 8-15 символов'
            )
        return password
