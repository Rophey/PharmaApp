from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomLoginForm, CustomUserCreationForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.first_name}!')
            return redirect_by_role(user)
        else:
            messages.error(request, 'Неверный логин или пароль')
    else:
        form = CustomLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('login')


def redirect_by_role(user):
    role_redirects = {
        'operator': 'operator_dashboard',
        'technologist': 'technologist_dashboard',
        'chief_technologist': 'chief_technologist_dashboard',
        'qc_specialist': 'qc_specialist_dashboard',
        'qc_head': 'qc_head_dashboard',
        'director': 'director_dashboard',
        'admin': 'admin_dashboard',
    }
    return redirect(role_redirects.get(user.role, 'login'))