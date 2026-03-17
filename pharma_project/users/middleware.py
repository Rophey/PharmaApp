from django.shortcuts import redirect
from django.urls import reverse
from .models import User


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Список URL, не требующих авторизации
        public_urls = [
            reverse('users:login'),
            '/admin/login/',
        ]

        # Добавляем текущего пользователя в request, если он авторизован
        request.current_user = None

        if 'user_id' in request.session:
            try:
                request.current_user = User.objects.get(
                    user_id=request.session['user_id'],
                    is_active=True
                )
                # Если пользователь авторизован и пытается зайти на login,
                # редиректим на дашборд
                if request.path == reverse('users:login'):
                    if request.current_user.role == 'системный администратор':
                        return redirect('users:admin_dashboard')
                    elif request.current_user.role == 'оператор':
                        return redirect('users:operator_dashboard')
                    elif request.current_user.role == 'директор':
                        return redirect('users:director_dashboard')
                    elif request.current_user.role == 'технолог':
                        return redirect('users:technologist_dashboard')
                    elif request.current_user.role == 'главный технолог':
                        return redirect('users:chief_technologist_dashboard')
                    elif request.current_user.role == 'сотрудник ОКК':
                        return redirect('users:qc_specialist_dashboard')
                    elif request.current_user.role == 'начальник ОКК':
                        return redirect('users:qc_chief_dashboard')
                    # ... остальные роли
            except User.DoesNotExist:
                request.session.flush()

        # Проверка авторизации для защищенных URL
        if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            path = request.path
            if path not in public_urls and not path.startswith('/admin/'):
                if 'user_id' not in request.session:
                    return redirect('users:login')

        response = self.get_response(request)
        return response