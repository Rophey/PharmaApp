from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User
from audit.models import Action, AuditLog, Document
from mbr.models import DocumentType
import re


def login_view(request):
    # Если пользователь уже авторизован - сразу редиректим на дашборд
    if 'user_id' in request.session:
        user = User.objects.get(user_id=request.session['user_id'])
        if user.role == 'системный администратор':
            return redirect('users:admin_dashboard')
        elif user.role == 'оператор':
            return redirect('users:operator_dashboard')
        elif user.role == 'технолог':
            return redirect('users:technologist_dashboard')
        elif user.role == 'главный технолог':
            return redirect('users:chief_technologist_dashboard')
        elif user.role == 'сотрудник ОКК':
            return redirect('users:qc_specialist_dashboard')
        elif user.role == 'начальник ОКК':
            return redirect('users:qc_chief_dashboard')
        elif user.role == 'директор':
            return redirect('users:director_dashboard')

    if request.method == 'POST':
        login = request.POST.get('login')
        password = request.POST.get('password')

        # Валидация
        latin_login = r'^[a-zA-Z0-9_]+$'
        latin_pass = r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]+$'

        import re
        login_valid = len(login) >= 8 and len(login) <= 15 and re.match(latin_login, login)
        pass_valid = len(password) >= 8 and len(password) <= 15 and re.match(latin_pass, password)

        if not login_valid or not pass_valid:
            messages.error(request, 'Неверный логин или пароль')
            return render(request, 'users/login.html')

        try:
            user = User.objects.get(login=login, is_active=True)
            if user.check_password(password):
                # Сохраняем в сессии
                request.session['user_id'] = user.user_id
                request.session['user_role'] = user.role
                request.session['user_name'] = f"{user.last_name} {user.first_name}"

                # Логируем вход (БЕЗ ДОКУМЕНТА)
                try:
                    action = Action.objects.get(action_name='Вход в систему')
                    AuditLog.objects.create(
                        user=user,
                        action=action,
                        document=None,  # Явно указываем None для входа/выхода
                        ip_address=request.META.get('REMOTE_ADDR'),
                        comment=f"Вход в систему"
                    )
                except Exception as e:
                    print(f"Ошибка логирования: {e}")

                messages.success(request, f"Добро пожаловать, {user.last_name} {user.first_name}!")

                # Перенаправление по роли
                if user.role == 'системный администратор':
                    return redirect('users:admin_dashboard')
                elif user.role == 'оператор':
                    return redirect('users:operator_dashboard')
                elif user.role == 'технолог':
                    return redirect('users:technologist_dashboard')
                elif user.role == 'главный технолог':
                    return redirect('users:chief_technologist_dashboard')
                elif user.role == 'сотрудник ОКК':
                    return redirect('users:qc_specialist_dashboard')
                elif user.role == 'начальник ОКК':
                    return redirect('users:qc_chief_dashboard')
                elif user.role == 'директор':
                    return redirect('users:director_dashboard')
            else:
                messages.error(request, 'Неверный логин или пароль')
        except User.DoesNotExist:
            messages.error(request, 'Неверный логин или пароль')

    return render(request, 'users/login.html')


def logout_view(request):
    if 'user_id' in request.session:
        try:
            user = User.objects.get(user_id=request.session['user_id'])
            action = Action.objects.get(action_name='Выход из системы')
            # Логируем выход БЕЗ ДОКУМЕНТА
            AuditLog.objects.create(
                user=user,
                action=action,
                document=None,  # Явно указываем None для входа/выхода
                ip_address=request.META.get('REMOTE_ADDR'),
                comment="Выход из системы"
            )
        except Exception as e:
            print(f"Ошибка логирования: {e}")

    request.session.flush()
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('users:login')


# def dashboard(request):
#     if 'user_id' not in request.session:
#         return redirect('login')
#
#     user = User.objects.get(user_id=request.session['user_id'])
#
#     context = {
#         'user': user,
#     }
#     return render(request, 'users/dashboard.html', context)


def admin_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'системный администратор':
        return redirect('login')

    user = User.objects.get(user_id=request.session['user_id'])

    if request.method == 'POST':
        login = request.POST.get('login')
        password = request.POST.get('password')
        last_name = request.POST.get('last_name')
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name', '')
        role = request.POST.get('role')

        # Проверка логина
        if not re.match(r'^[a-zA-Z0-9_]{8,15}$', login):
            messages.error(request, 'Логин должен быть 8-15 символов, только латиница, цифры, _')
            return redirect('users:admin_dashboard')

        # Проверка пароля
        if not re.match(r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]{8,15}$', password):
            messages.error(request, 'Пароль должен быть 8-15 символов, только латиница, цифры, спецсимволы')
            return redirect('users:admin_dashboard')

        # Проверка уникальности
        if User.objects.filter(login=login).exists():
            messages.error(request, 'Пользователь с таким логином уже существует')
            return redirect('users:admin_dashboard')

        # Создаём пользователя
        new_user = User(
            login=login,
            role=role,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            is_active=True
        )
        new_user.set_password(password)
        new_user.save()

        # Логируем создание
        try:
            action = Action.objects.get(action_name='Создание пользователя')
            doc_type = DocumentType.objects.get(type_name='MBR')
            doc = Document.objects.create(type=doc_type)
            AuditLog.objects.create(
                user=user,
                action=action,
                document=doc,
                comment=f"Создан пользователь {login}"
            )
        except:
            pass

        messages.success(request, f'Пользователь {login} создан')
        return redirect('users:admin_dashboard')

    users = User.objects.all().order_by('-created_at')

    context = {
        'user': user,
        'users': users,
    }
    return render(request, 'users/admin_dashboard.html', context)


def operator_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'оператор':
        return redirect('login')

    from ebr.models import EBR, BatchOperation

    user = User.objects.get(user_id=request.session['user_id'])

    active_tasks = BatchOperation.objects.filter(
        status__in=['pending', 'in_progress'],
        ebr__operator=user
    ).select_related('ebr')

    context = {
        'user': user,
        'active_tasks': active_tasks,
    }
    return render(request, 'users/operator_dashboard.html', context)


def technologist_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'технолог':
        return redirect('login')

    from mbr.models import MBR, Product
    from ebr.models import EBR

    user = User.objects.get(user_id=request.session['user_id'])

    approved_mbrs = MBR.objects.filter(status__status_name='Утверждён')
    products = Product.objects.all()
    ebrs = EBR.objects.all().select_related('status', 'mbr__product').order_by('-start_date')[:10]

    context = {
        'user': user,
        'approved_mbrs': approved_mbrs,
        'products': products,
        'ebrs': ebrs,
    }
    return render(request, 'users/technologist_dashboard.html', context)


def chief_technologist_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('users:login')

    from mbr.models import MBR, Parameter, RawMaterial, Product, Document, DocumentType, MBRStatus
    from audit.models import Action, AuditLog
    from datetime import datetime

    user = User.objects.get(user_id=request.session['user_id'])

    # Обработка POST запросов
    if request.method == 'POST':
        action = request.POST.get('action')
        print(f"POST received: {request.POST}")  # Отладка

        if action == 'create_mbr':
            try:
                # Получаем или создаём продукт
                product_code = request.POST.get('product_code')
                product_name = request.POST.get('product_name')

                print(f"Creating MBR for product: {product_code} - {product_name}")

                product, created = Product.objects.get_or_create(
                    product_code=product_code,
                    defaults={'product_name': product_name}
                )

                if created:
                    print(f"Created new product: {product_code}")

                # Создаём документ
                doc_type = DocumentType.objects.get(type_name='MBR')
                document = Document.objects.create(type=doc_type)
                print(f"Created document: {document.document_id}")

                # Получаем статус "Черновик"
                draft_status = MBRStatus.objects.get(status_name='Черновик')

                # Создаём MBR
                mbr = MBR.objects.create(
                    document=document,
                    product=product,
                    version=request.POST.get('version', 'v1'),
                    status=draft_status,
                    operations=request.POST.get('operations', ''),
                    comments=request.POST.get('comments', '')
                )
                print(f"Created MBR: {mbr.document_id}")

                # Добавляем сырьё
                raw_material_ids = request.POST.getlist('raw_materials')
                print(f"Raw materials: {raw_material_ids}")

                for rm_id in raw_material_ids:
                    if rm_id and rm_id.isdigit():
                        try:
                            material = RawMaterial.objects.get(pk=int(rm_id))
                            mbr.raw_materials.add(material)
                            print(f"Added raw material: {material.material_name}")
                        except RawMaterial.DoesNotExist:
                            print(f"Raw material {rm_id} not found")

                # Добавляем параметры
                for key, value in request.POST.items():
                    if key.startswith('param_value_'):
                        param_id = key.replace('param_value_', '')
                        print(f"Processing parameter {param_id}")

                        try:
                            parameter = Parameter.objects.get(pk=param_id)
                            mbr.parameters.add(parameter)

                            # Обновляем значения параметров
                            param_value = request.POST.get(f'param_value_{param_id}')
                            param_tolerance = request.POST.get(f'param_tolerance_{param_id}')
                            param_critical = request.POST.get(f'param_critical_{param_id}')

                            print(f"Parameter values - value: {param_value}, tolerance: {param_tolerance}, critical: {param_critical}")

                            if param_value:
                                parameter.value = float(param_value)
                            if param_tolerance:
                                parameter.tolerance = float(param_tolerance)
                            if param_critical:
                                parameter.critical_deviation = float(param_critical)
                            parameter.save()

                        except Parameter.DoesNotExist:
                            print(f"Parameter {param_id} not found")
                        except ValueError as e:
                            print(f"Invalid number format: {e}")

                # Проверяем, была ли нажата кнопка утверждения
                if request.POST.get('approve'):
                    approved_status = MBRStatus.objects.get(status_name='Утверждён')
                    mbr.status = approved_status
                    mbr.approval_date = datetime.now().date()
                    mbr.signed_by = user
                    mbr.save()

                    messages.success(request, f'MBR {product_code} утверждён')
                else:
                    messages.success(request, f'MBR {product_code} сохранён как черновик')

                # Логируем действие
                try:
                    action_obj = Action.objects.get(action_name='Создание MBR')
                    AuditLog.objects.create(
                        user=user,
                        action=action_obj,
                        document=document,
                        comment=f"Создан MBR для {product_code}"
                    )
                except Exception as e:
                    print(f"Logging error: {e}")

                # Перенаправляем на ту же страницу, чтобы избежать повторной отправки формы
                return redirect('users:chief_technologist_dashboard')

            except Exception as e:
                print(f"Error creating MBR: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Ошибка при создании MBR: {str(e)}')

    # Получаем данные для отображения
    mbrs = MBR.objects.all().select_related('product', 'status', 'signed_by').order_by('-created_at')
    parameters = Parameter.objects.all().order_by('parameter_name')
    raw_materials = RawMaterial.objects.all().order_by('material_name')
    products = Product.objects.all().order_by('product_code')

    print(f"Loaded {parameters.count()} parameters")  # Отладка

    context = {
        'user': user,
        'mbrs': mbrs,
        'parameters': parameters,
        'raw_materials': raw_materials,
        'products': products,
    }
    return render(request, 'users/chief_technologist_dashboard.html', context)


def qc_specialist_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'сотрудник ОКК':
        return redirect('login')

    from quality.models import QCTask

    user = User.objects.get(user_id=request.session['user_id'])

    tasks = QCTask.objects.filter(
        assigned_to=user,
        status__in=['new', 'in_progress']
    ).select_related('ebr')

    context = {
        'user': user,
        'tasks': tasks,
    }
    return render(request, 'users/qc_specialist_dashboard.html', context)


def qc_chief_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'начальник ОКК':
        return redirect('login')

    from quality.models import Deviation
    from ebr.models import EBR

    user = User.objects.get(user_id=request.session['user_id'])

    pending_review = EBR.objects.filter(status__status_name='В работе').select_related('mbr__product')[:20]
    deviations = Deviation.objects.filter(action_taken__isnull=True).select_related('ebr', 'detected_by')[:20]

    context = {
        'user': user,
        'pending_review': pending_review,
        'deviations': deviations,
    }
    return render(request, 'users/qc_chief_dashboard.html', context)


def director_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'директор':
        return redirect('login')

    from reports.models import GeneratedReport
    from ebr.models import EBR
    from quality.models import Deviation
    from django.db.models import Count, Sum
    from datetime import datetime, timedelta

    user = User.objects.get(user_id=request.session['user_id'])

    # Статистика за месяц
    month_ago = datetime.now() - timedelta(days=30)

    total_batches = EBR.objects.filter(start_date__gte=month_ago).count()
    completed_batches = EBR.objects.filter(start_date__gte=month_ago, status__status_name='Завершена').count()
    total_deviations = Deviation.objects.filter(detected_at__gte=month_ago).count()

    recent_reports = GeneratedReport.objects.filter(
        generated_by=user
    ).order_by('-generated_at')[:10]

    context = {
        'user': user,
        'total_batches': total_batches,
        'completed_batches': completed_batches,
        'total_deviations': total_deviations,
        'recent_reports': recent_reports,
    }
    return render(request, 'users/director_dashboard.html', context)


from django.http import JsonResponse
from mbr.models import MBR, Parameter


def get_mbr_parameters(request, mbr_id):
    """API для получения параметров MBR"""
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        mbr = MBR.objects.get(document_id=mbr_id)
        data = {
            'id': mbr.document_id,
            'product_code': mbr.product.product_code,
            'product_name': mbr.product.product_name,
            'version': mbr.version,
            'status': mbr.status.status_name,
            'operations': mbr.operations,
            'comments': mbr.comments,
            'parameters': [
                {
                    'id': p.parameter_id,
                    'name': p.parameter_name,
                    'value': float(p.value),
                    'unit': p.unit,
                    'tolerance': float(p.tolerance),
                    'critical': float(p.critical_deviation)
                } for p in mbr.parameters.all()
            ],
            'raw_materials': [
                {
                    'id': rm.raw_material_id,
                    'name': rm.material_name
                } for rm in mbr.raw_materials.all()
            ]
        }
        return JsonResponse(data)
    except MBR.DoesNotExist:
        return JsonResponse({'error': 'MBR not found'}, status=404)