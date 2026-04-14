from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import User
from audit.models import Action, AuditLog
from mbr.models import DocumentType, Document
import json
import re
import datetime
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


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
                    action, _ = Action.objects.get_or_create(action_name='Вход в систему')
                    AuditLog.objects.create(
                        user=user,
                        action=action,
                        document=None,  # Явно указываем None для входа/выхода
                        ip_address=request.META.get('REMOTE_ADDR'),
                        comment=f"Вход в систему. IP: {request.META.get('REMOTE_ADDR', 'неизвестно')}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка логирования входа: {e}")

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
            action, _ = Action.objects.get_or_create(action_name='Выход из системы')
            # Логируем выход БЕЗ ДОКУМЕНТА
            AuditLog.objects.create(
                user=user,
                action=action,
                document=None,  # Явно указываем None для входа/выхода
                ip_address=request.META.get('REMOTE_ADDR'),
                comment=f"Выход из системы. IP: {request.META.get('REMOTE_ADDR', 'неизвестно')}"
            )
        except Exception as e:
            logger.error(f"Ошибка логирования выхода: {e}")

    request.session.flush()
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('users:login')


def admin_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'системный администратор':
        return redirect('users:login')

    user = User.objects.get(user_id=request.session['user_id'])

    if request.method == 'POST':
        action = request.POST.get('action', 'create_user')

        if action == 'toggle_user':
            # Деактивация / Активация пользователя
            user_id = request.POST.get('user_id')
            if user_id:
                target = get_object_or_404(User, user_id=int(user_id))
                if target.user_id == user.user_id:
                    messages.error(request, 'Нельзя изменить статус своей учетной записи')
                else:
                    target.is_active = not target.is_active
                    target.save()
                    status = 'Активирован' if target.is_active else 'Деактивирован'
                    try:
                        act = Action.objects.get(action_name=status + ' пользователя')
                        AuditLog.objects.create(user=user, action=act, comment=f"{status} пользователь {target.login}")
                    except:
                        pass
                    messages.success(request, f'{status} пользователь {target.login}')
            return redirect('users:admin_dashboard')

        if action == 'delete_user':
            # Удаление пользователя
            user_id = request.POST.get('user_id')
            if user_id:
                target = get_object_or_404(User, user_id=int(user_id))
                if target.user_id == user.user_id:
                    messages.error(request, 'Нельзя удалить свою учетную запись')
                else:
                    target.delete()
                    try:
                        act = Action.objects.get(action_name='Удаление пользователя')
                        AuditLog.objects.create(user=user, action=act, comment=f"Удалён пользователь {target.login}")
                    except:
                        pass
                    messages.success(request, f'Пользователь {target.login} удалён')
            return redirect('users:admin_dashboard')

        # create_user — создание пользователя
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

        # Проверка ФИО
        fio_re = re.compile(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$')
        for fname, label in [(last_name, 'Фамилия'), (first_name, 'Имя')]:
            if not fname or not fio_re.match(fname) or not fname.strip():
                messages.error(request, f'{label}: только буквы, пробелы и дефис')
                return redirect('users:admin_dashboard')
        if middle_name and not fio_re.match(middle_name):
            messages.error(request, 'Отчество: только буквы, пробелы и дефис')
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
            action_obj = Action.objects.get(action_name='Создание пользователя')
            doc_type = DocumentType.objects.get(type_name='MBR')
            doc = Document.objects.create(type=doc_type)
            AuditLog.objects.create(
                user=user,
                action=action_obj,
                document=doc,
                comment=f"Создан пользователь {login}"
            )
        except:
            pass

        messages.success(request, f'Пользователь {login} создан')
        return redirect('users:admin_dashboard')

    users = User.objects.all().order_by('-created_at')
    from mbr.models import RawMaterial, Product
    context = {
        'user': user,
        'users': users,
        'raw_materials': RawMaterial.objects.all().order_by('material_name'),
        'products': Product.objects.all().order_by('product_code'),
    }
    return render(request, 'users/admin_dashboard.html', context)


def operator_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'оператор':
        return redirect('users:login')

    from ebr.models import EBR, BatchOperation, EBRNominalParameter, EBRActualParameter
    from equipment.models import EquipmentReading

    user = User.objects.get(user_id=request.session['user_id'])

    # Партии «В ожидании» — где оператор ЕЩЁ НЕ назначен
    waiting_ebrs = EBR.objects.filter(
        status__status_name='В ожидании',
        operator__isnull=True
    ).select_related('status', 'mbr__product').order_by('-start_date')

    # Активные задачи текущего оператора (исключаем завершённые/заблокированные EBR)
    active_tasks_qs = BatchOperation.objects.filter(
        status__in=['pending', 'in_progress', 'completed'],
        ebr__operator=user,
        ebr__status__status_name__in=['В работе']
    ).select_related('ebr', 'ebr__mbr__product', 'ebr__operator', 'ebr__status'
    ).prefetch_related(
        'ebr__mbr__raw_materials'
    ).order_by('id')

    # Собираем активные партии — для каждой EBR берём первую in_progress задачу,
    # если нет — последнюю pending
    active_parties = {}
    for task in active_tasks_qs:
        ebr_id = task.ebr_id
        if ebr_id not in active_parties:
            active_parties[ebr_id] = task
        else:
            # Приоритет: in_progress > pending > completed
            current = active_parties[ebr_id]
            if task.status == 'in_progress' and current.status != 'in_progress':
                active_parties[ebr_id] = task

    # Для каждой активной партии — параметры
    for ebr_id, task in active_parties.items():
        ebr = task.ebr
        ebr.params = []
        nominal_params = EBRNominalParameter.objects.filter(ebr=ebr).select_related('parameter')
        actual_params = EBRActualParameter.objects.filter(ebr=ebr).select_related('parameter')

        for np in nominal_params:
            ap = actual_params.filter(parameter_id=np.parameter_id).first()
            status = 'pending'
            value = ap.max_value if ap and ap.max_value else (ap.actual_value if ap else None)
            if value is not None and float(np.nominal_value) > 0:
                diff = abs(float(value) - float(np.nominal_value))
                if diff > float(np.critical_value):
                    status = 'critical'
                elif diff > float(np.tolerance_value):
                    status = 'deviation'
                elif diff > float(np.tolerance_value) * 0.9:
                    status = 'warning'
                else:
                    status = 'ok'
            ebr.params.append({
                'name': np.parameter.parameter_name,
                'unit': np.parameter.unit,
                'nominal': float(np.nominal_value),
                'actual': float(ap.actual_value) if ap and ap.actual_value else None,
                'max_value': float(ap.max_value) if ap and ap.max_value else None,
                'status': status,
            })

        ebr.latest_readings = EquipmentReading.objects.filter(
            batch=ebr
        ).order_by('-timestamp')[:5]

        ebr.current_task = task  # последняя (или единственная) задача
        ebr.pressing_started = ebr.pressing_start_time is not None and ebr.pressing_duration is not None
        # Проверяем, работает ли ещё пресс
        if ebr.pressing_start_time and ebr.pressing_duration:
            now = timezone.now()
            elapsed = (now - ebr.pressing_start_time).total_seconds()
            ebr.press_still_running = elapsed < ebr.pressing_duration
            ebr.press_remaining = max(0, int(ebr.pressing_duration - elapsed))
        else:
            ebr.press_still_running = False
            ebr.press_remaining = 0

    # Сортируем: активные (пресс работает) сверху, затем завершённые/ОКК.
    # Внутри групп — чем позже оператор взял партию, тем выше.
    sorted_parties = sorted(
        active_parties.values(),
        key=lambda t: (
            0 if (t.ebr.press_still_running) else 1,
            -(t.started_at.timestamp() if t.started_at else 0)
        )
    )

    context = {
        'user': user,
        'waiting_ebrs': waiting_ebrs,
        'active_parties': sorted_parties,
    }
    return render(request, 'users/operator_dashboard.html', context)


def technologist_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'технолог':
        return redirect('users:login')

    from mbr.models import MBR, Product
    from ebr.models import EBR, EBRNominalParameter, EBRActualParameter, BatchOperation
    from django.db.models import Max

    user = User.objects.get(user_id=request.session['user_id'])

    # Только последняя утверждённая версия каждого продукта
    latest_mbr_ids = MBR.objects.filter(
        status__status_name='Утверждён'
    ).values('product_id').annotate(
        max_doc_id=Max('document_id')
    ).values_list('max_doc_id', flat=True)

    approved_mbrs = MBR.objects.filter(
        document_id__in=latest_mbr_ids
    ).select_related('product', 'status', 'signed_by')

    products = Product.objects.all()
    ebrs = EBR.objects.all().select_related('status', 'mbr__product').order_by('-start_date')[:10]

    # Активные партии (В работе + В ожидании) с параметрами для мониторинга
    active_ebrs = EBR.objects.filter(
        status__status_name__in=['В работе', 'В ожидании']
    ).select_related('status', 'mbr__product').order_by('-start_date')

    # Для каждой активной партии — параметры с статусом
    for ebr in active_ebrs:
        ebr.param_status = []
        nominal_params = EBRNominalParameter.objects.filter(ebr=ebr).select_related('parameter')
        actual_params = EBRActualParameter.objects.filter(ebr=ebr).select_related('parameter')
        worst_status = 'ok'

        for np in nominal_params:
            ap = actual_params.filter(parameter_id=np.parameter_id).first()
            status = 'pending'

            if ap and ap.actual_value is not None:
                diff = abs(float(ap.actual_value) - float(np.nominal_value))
                if diff > float(np.critical_value):
                    status = 'critical'
                    worst_status = 'critical'
                elif diff > float(np.tolerance_value):
                    status = 'deviation'
                    if worst_status not in ('critical',):
                        worst_status = 'deviation'
                elif diff > float(np.tolerance_value) * 0.9:
                    status = 'warning'
                    if worst_status not in ('critical', 'deviation'):
                        worst_status = 'warning'
                else:
                    status = 'ok'

            ebr.param_status.append({
                'name': np.parameter.parameter_name,
                'unit': np.parameter.unit,
                'nominal': float(np.nominal_value),
                'actual': float(ap.actual_value) if ap and ap.actual_value else None,
                'max_value': float(ap.max_value) if ap and ap.max_value else None,
                'tolerance': float(np.tolerance_value),
                'critical': float(np.critical_value),
                'status': status,
            })
        ebr.worst_status = worst_status

        # Информация о прессе для уведомления
        ebr.pressing_started = ebr.pressing_start_time is not None and ebr.pressing_duration is not None
        if ebr.pressing_start_time and ebr.pressing_duration:
            now = timezone.now()
            elapsed = (now - ebr.pressing_start_time).total_seconds()
            ebr.press_still_running = elapsed < ebr.pressing_duration
            ebr.press_remaining = max(0, int(ebr.pressing_duration - elapsed))
            # Проверяем, только что ли закончил (в пределах 5 сек) — для уведомления
            ebr.just_finished = 0 <= elapsed - ebr.pressing_duration < 5
        else:
            ebr.press_still_running = False
            ebr.press_remaining = 0
            ebr.just_finished = False

    context = {
        'user': user,
        'approved_mbrs': approved_mbrs,
        'products': products,
        'ebrs': ebrs,
        'active_ebrs': active_ebrs,
    }
    return render(request, 'users/technologist_dashboard.html', context)


def _calc_param_status_nominal_actual(np, ap):
    """Рассчитать статус параметра: ok / warning / deviation / critical"""
    if ap is None or ap.actual_value is None:
        return 'pending'
    value = ap.max_value if ap.max_value else ap.actual_value
    if np.nominal_value and float(np.nominal_value) > 0:
        diff = abs(float(value) - float(np.nominal_value))
        if diff > float(np.critical_value):
            return 'critical'
        elif diff > float(np.tolerance_value):
            return 'deviation'
        elif diff > float(np.tolerance_value) * 0.9:
            return 'warning'
    return 'ok'


def ebr_monitoring_api(request, ebr_id):
    """AJAX endpoint: получить данные мониторинга для партии в реальном времени"""
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        from ebr.models import EBR, EBRNominalParameter, EBRActualParameter
        ebr = EBR.objects.select_related('status', 'mbr__product').get(document_id=ebr_id)

        nominal_params = EBRNominalParameter.objects.filter(ebr=ebr).select_related('parameter')
        actual_params = EBRActualParameter.objects.filter(ebr=ebr).select_related('parameter')
        param_data = []
        worst_status = 'ok'

        for np in nominal_params:
            ap = actual_params.filter(parameter_id=np.parameter_id).first()
            status = _calc_param_status_nominal_actual(np, ap)
            if status == 'critical':
                worst_status = 'critical'
            elif status == 'deviation' and worst_status not in ('critical',):
                worst_status = 'deviation'
            elif status == 'warning' and worst_status not in ('critical', 'deviation'):
                worst_status = 'warning'

            param_data.append({
                'name': np.parameter.parameter_name,
                'unit': np.parameter.unit,
                'nominal': float(np.nominal_value),
                'actual': float(ap.actual_value) if ap and ap.actual_value else None,
                'max_value': float(ap.max_value) if ap and ap.max_value else None,
                'tolerance': float(np.tolerance_value),
                'critical': float(np.critical_value),
                'status': status,
            })

        return JsonResponse({
            'success': True,
            'batch_number': ebr.batch_number,
            'product': ebr.mbr.product.product_name,
            'status': ebr.status.status_name,
            'worst_status': worst_status,
            'parameters': param_data,
            'pressing_started': ebr.pressing_start_time is not None and ebr.pressing_duration is not None,
            'press_still_running': ebr.pressing_start_time is not None and ebr.pressing_duration is not None and
                ((timezone.now() - ebr.pressing_start_time).total_seconds() < ebr.pressing_duration),
        })
    except EBR.DoesNotExist:
        return JsonResponse({'error': 'EBR not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def technologist_monitoring_api(request):
    """AJAX endpoint: получить список всех активных EBR для панели технолога"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'технолог':
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    from ebr.models import EBR, EBRNominalParameter, EBRActualParameter

    try:
        active_ebrs = EBR.objects.filter(
            status__status_name__in=['В работе', 'В ожидании']
        ).select_related('status', 'mbr__product').order_by('-start_date')

        result = []
        for ebr in active_ebrs:
            # Параметры
            nominal_params = EBRNominalParameter.objects.filter(ebr=ebr).select_related('parameter')
            actual_params = EBRActualParameter.objects.filter(ebr=ebr).select_related('parameter')
            param_data = []
            worst_status = 'ok'

            for np in nominal_params:
                ap = actual_params.filter(parameter_id=np.parameter_id).first()
                status = 'pending'
                if ap and ap.actual_value is not None:
                    diff = abs(float(ap.actual_value) - float(np.nominal_value))
                    if diff > float(np.critical_value):
                        status = 'critical'
                        worst_status = 'critical'
                    elif diff > float(np.tolerance_value):
                        status = 'deviation'
                        if worst_status not in ('critical',):
                            worst_status = 'deviation'
                    elif diff > float(np.tolerance_value) * 0.9:
                        status = 'warning'
                        if worst_status not in ('critical', 'deviation'):
                            worst_status = 'warning'
                    else:
                        status = 'ok'

                param_data.append({
                    'name': np.parameter.parameter_name,
                    'unit': np.parameter.unit,
                    'nominal': float(np.nominal_value),
                    'actual': float(ap.actual_value) if ap and ap.actual_value else None,
                    'max_value': float(ap.max_value) if ap and ap.max_value else None,
                    'tolerance': float(np.tolerance_value),
                    'critical': float(np.critical_value),
                    'status': status,
                })

            # Пресс
            pressing_started = ebr.pressing_start_time is not None and ebr.pressing_duration is not None
            press_still_running = False
            press_remaining = 0
            just_finished = False
            if ebr.pressing_start_time and ebr.pressing_duration:
                now = timezone.now()
                elapsed = (now - ebr.pressing_start_time).total_seconds()
                press_still_running = elapsed < ebr.pressing_duration
                press_remaining = max(0, int(ebr.pressing_duration - elapsed))
                just_finished = 0 <= elapsed - ebr.pressing_duration < 5

            result.append({
                'document_id': ebr.document_id,
                'batch_number': ebr.batch_number,
                'product': ebr.mbr.product.product_name,
                'status': ebr.status.status_name,
                'operation_label': ebr.current_operation_label,
                'worst_status': worst_status,
                'pressing_started': pressing_started,
                'press_still_running': press_still_running,
                'press_remaining': press_remaining,
                'just_finished': just_finished,
                'operator': ebr.operator.first_name + ' ' + ebr.operator.last_name if ebr.operator else None,
                'parameters': param_data,
            })

        return JsonResponse({'success': True, 'ebrs': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def operator_waiting_list_api(request):
    """AJAX endpoint: список партий, ожидающих оператора"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'оператор':
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    from ebr.models import EBR

    try:
        waiting_ebrs = EBR.objects.filter(
            status__status_name='В ожидании',
            operator__isnull=True
        ).select_related('mbr__product').order_by('-start_date')

        result = [{
            'document_id': ebr.document_id,
            'batch_number': ebr.batch_number,
            'product': ebr.mbr.product.product_name,
            'start_date': ebr.start_date.isoformat() if ebr.start_date else None,
        } for ebr in waiting_ebrs]

        return JsonResponse({'success': True, 'waiting_ebrs': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def technologist_approved_mbrs_api(request):
    """AJAX endpoint: список утверждённых MBR для технолога"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'технолог':
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    from mbr.models import MBR
    from django.db.models import Max

    try:
        latest_mbr_ids = MBR.objects.filter(
            status__status_name='Утверждён'
        ).values('product_id').annotate(
            max_doc_id=Max('document_id')
        ).values_list('max_doc_id', flat=True)

        approved_mbrs = MBR.objects.filter(
            document_id__in=latest_mbr_ids
        ).select_related('product', 'status', 'signed_by').order_by('-created_at')

        result = [{
            'document_id': mbr.document_id,
            'product_code': mbr.product.product_code,
            'product_name': mbr.product.product_name,
            'version': mbr.version,
        } for mbr in approved_mbrs]

        return JsonResponse({'success': True, 'approved_mbrs': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def is_ajax(request):
    """Проверка на AJAX-запрос"""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def ajax_redirect(request, viewname, *args, **kwargs):
    """Если AJAX — возвращаем JSON, иначе redirect"""
    if is_ajax(request):
        return JsonResponse({'success': True, 'redirect': str(viewname)})
    return redirect(viewname, *args, **kwargs)


def ajax_redirect_with_error(request, error_msg):
    """Ошибка для AJAX или redirect с сообщением"""
    if is_ajax(request):
        return JsonResponse({'success': False, 'error': error_msg}, status=400)
    messages.error(request, error_msg)
    return redirect('users:chief_technologist_dashboard')


def chief_technologist_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('users:login')

    from mbr.models import MBR, Parameter, RawMaterial, Product, Document, DocumentType, MBRStatus
    from audit.models import Action, AuditLog
    from datetime import datetime
    import logging
    import traceback

    logger = logging.getLogger(__name__)
    user = User.objects.get(user_id=request.session['user_id'])

    if request.method == 'POST':
        action = request.POST.get('form_action')
        logger.info(f"=== POST received, action: {action} ===")

        if action == 'create_mbr':
            try:
                # 1. Получаем ID продукта (используем id)
                product_id = request.POST.get('product_id')
                logger.info(f"Product ID: {product_id}")

                if not product_id:
                    return ajax_redirect_with_error(request, 'Не выбран продукт')

                try:
                    product = Product.objects.get(id=product_id)
                    logger.info(f"Found product: {product.product_code}")
                except Product.DoesNotExist:
                    return ajax_redirect_with_error(request, 'Выбранный продукт не существует')

                # 2. Создаём документ
                try:
                    doc_type = DocumentType.objects.get(type_name='MBR')
                except DocumentType.DoesNotExist:
                    return ajax_redirect_with_error(request, 'Ошибка конфигурации: тип документа MBR не найден')

                document = Document.objects.create(type=doc_type)
                logger.info(f"Created document with ID: {document.id}")  # исправлено: id вместо document_id

                # 3. Получаем статус
                try:
                    draft_status = MBRStatus.objects.get(status_name='Черновик')
                except MBRStatus.DoesNotExist:
                    return ajax_redirect_with_error(request, 'Ошибка конфигурации: статус "Черновик" не найден')

                # 4. Определяем версию (автоинкремент если уже есть MBR для этого продукта)
                existing_mbrs = MBR.objects.filter(product=product).order_by('-document_id')
                if existing_mbrs.exists():
                    max_version = 0
                    for existing_mbr in existing_mbrs:
                        import re as re_mod
                        match = re_mod.search(r'v(\d+)', existing_mbr.version)
                        if match:
                            version_num = int(match.group(1))
                            if version_num > max_version:
                                max_version = version_num
                    version = f'v{max_version + 1}'
                    logger.info(f"Auto-generated version: {version}")
                else:
                    version = request.POST.get('version', 'v1')

                operations = request.POST.get('operations', '')
                comments = request.POST.get('comments', '')

                mbr = MBR.objects.create(
                    document=document,
                    product=product,
                    version=version,
                    status=draft_status,
                    operations=operations,
                    comments=comments
                )
                logger.info(f"Created MBR with document_id: {mbr.document_id}, version: {version}")

                # 5. Добавляем сырьё
                raw_material_ids = request.POST.getlist('raw_materials')
                logger.info(f"Raw materials to add: {raw_material_ids}")

                for rm_id in raw_material_ids:
                    if rm_id and rm_id.isdigit():
                        try:
                            material = RawMaterial.objects.get(id=int(rm_id))
                            mbr.raw_materials.add(material)
                            logger.info(f"Added raw material: {material.material_name}")
                        except RawMaterial.DoesNotExist:
                            logger.warning(f"Raw material {rm_id} not found")

                # 6. Создаём MBRParameter с собственными значениями (НЕ меняем глобальные Parameter!)
                from mbr.models import MBRParameter
                logger.info("=== Creating MBRParameter instances ===")

                for key, value in request.POST.items():
                    if key.startswith('param_value_'):
                        param_id = key.replace('param_value_', '')

                        if not param_id or not param_id.isdigit():
                            logger.warning(f"Invalid param_id: '{param_id}'")
                            continue

                        try:
                            parameter = Parameter.objects.get(id=int(param_id))
                            logger.info(f"Found parameter template: {parameter.parameter_name}")

                            # Получаем значения из формы
                            param_value_str = request.POST.get(f'param_value_{param_id}', '0')
                            param_tolerance_str = request.POST.get(f'param_tolerance_{param_id}', '0')
                            param_critical_str = request.POST.get(f'param_critical_{param_id}', '0')

                            # Конвертируем в float
                            try:
                                param_value = float(param_value_str.replace(',', '.'))
                            except (ValueError, AttributeError):
                                param_value = 0

                            try:
                                param_tolerance = float(param_tolerance_str.replace(',', '.'))
                            except (ValueError, AttributeError):
                                param_tolerance = 0

                            try:
                                param_critical = float(param_critical_str.replace(',', '.'))
                            except (ValueError, AttributeError):
                                param_critical = 0

                            # Создаём MBRParameter с СОБСТВЕННЫМИ значениями для ЭТОГО MBR
                            mbr_param = MBRParameter.objects.create(
                                mbr=mbr,
                                parameter=parameter,
                                value=param_value,
                                tolerance=param_tolerance,
                                critical_deviation=param_critical
                            )
                            logger.info(f"Created MBRParameter: {parameter.parameter_name} = {param_value}")

                        except Parameter.DoesNotExist:
                            logger.warning(f"Parameter {param_id} not found")
                        except Exception as e:
                            logger.error(f"Error creating MBRParameter {param_id}: {str(e)}")
                            import traceback
                            logger.error(traceback.format_exc())

                # Проверяем, сколько параметров создалось
                params_count = MBRParameter.objects.filter(mbr=mbr).count()
                logger.info(f"=== Total MBRParameter created: {params_count} ===")

                # 7. Проверяем утверждение
                if request.POST.get('approve'):
                    # ВАЛИДАЦИЯ перед утверждением
                    validation_errors = []
                    
                    if not mbr.operations or not mbr.operations.strip():
                        validation_errors.append('Не заполнены технологические операции')
                    
                    params_count = MBRParameter.objects.filter(mbr=mbr).count()
                    if params_count == 0:
                        validation_errors.append('Не добавлены параметры')
                    else:
                        empty_params = MBRParameter.objects.filter(mbr=mbr, value=0)
                        if empty_params.exists():
                            param_names = ', '.join([p.parameter.parameter_name for p in empty_params[:3]])
                            validation_errors.append(f'Не заполнены параметры: {param_names}')
                    
                    if mbr.raw_materials.count() == 0:
                        validation_errors.append('Не добавлено сырьё')
                    
                    if validation_errors:
                        error_msg = 'Внесённая информация не является полной: ' + '; '.join(validation_errors)
                        if is_ajax(request):
                            return JsonResponse({'success': False, 'error': error_msg}, status=400)
                        messages.error(request, error_msg)
                        return redirect('users:chief_technologist_dashboard')
                    
                    # Всё заполнено — утверждаем
                    try:
                        approved_status = MBRStatus.objects.get(status_name='Утверждён')
                        mbr.status = approved_status
                        mbr.approval_date = timezone.now().date()
                        mbr.signed_by = user
                        mbr.save()
                        messages.success(request, f'MBR для {product.product_code} утверждён')
                    except MBRStatus.DoesNotExist:
                        messages.warning(request, 'MBR сохранён как черновик')
                else:
                    messages.success(request, f'MBR для {product.product_code} сохранён как черновик')

                # 8. Логируем
                try:
                    action_obj = Action.objects.get(action_name='Создание MBR')
                    AuditLog.objects.create(
                        user=user,
                        action=action_obj,
                        document=document,
                        comment=f"Создан MBR {product.product_code} v1 "
                                f"({product.product_name}). "
                                f"Создал: {user.last_name} {user.first_name}"
                    )
                except Exception as e:
                    logger.error(f"Logging error: {e}")

                # Если AJAX-запрос — возвращаем JSON, иначе редирект
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'MBR для {product.product_code} сохранён',
                        'mbr_id': mbr.document_id
                    })
                return redirect('users:chief_technologist_dashboard')

            except Exception as e:
                logger.error(f"Error creating MBR: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Если AJAX-запрос — возвращаем JSON ошибки
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)}, status=500)
                
                messages.error(request, f'Ошибка при создании MBR: {str(e)}')
                return redirect('users:chief_technologist_dashboard')

    # Получаем данные для отображения
    mbrs = MBR.objects.all().select_related('product', 'status', 'signed_by').order_by('-created_at')
    parameters = Parameter.objects.all().order_by('parameter_name')
    raw_materials = RawMaterial.objects.all().order_by('material_name')
    products = Product.objects.all().order_by('product_code')

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
        return redirect('users:login')

    from quality.models import QCTask

    user = User.objects.get(user_id=request.session['user_id'])

    tasks = QCTask.objects.filter(
        assigned_to=user,
        status__in=['new', 'in_progress']
    ).select_related('ebr__mbr__product').order_by('-created_at')

    context = {
        'user': user,
        'tasks': tasks,
    }
    return render(request, 'users/qc_specialist_dashboard.html', context)


def qc_tasks_api(request):
    """AJAX endpoint: список заданий ОКК"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'сотрудник ОКК':
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    from quality.models import QCTask

    user = User.objects.get(user_id=request.session['user_id'])
    tasks = QCTask.objects.filter(
        assigned_to=user,
        status__in=['new', 'in_progress']
    ).select_related('ebr__mbr__product').order_by('-created_at')

    result = [{
        'id': t.id,
        'batch_number': t.ebr.batch_number,
        'product': t.ebr.mbr.product.product_name,
        'task_type': t.get_task_type_display(),
        'task_type_raw': t.task_type,
        'status': t.get_status_display(),
        'status_raw': t.status,
        'due_date': t.due_date.isoformat() if t.due_date else None,
        'ebr_id': t.ebr.document_id,
    } for t in tasks]

    return JsonResponse({'success': True, 'tasks': result})


def qc_submit_results(request, task_id):
    """AJAX endpoint: сохранить результаты ОКК"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'сотрудник ОКК':
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    from quality.models import QCTask, QCResult
    from ebr.models import EBRStatus, EBRActualParameter, Parameter
    from django.utils import timezone
    from decimal import Decimal, InvalidOperation

    user = User.objects.get(user_id=request.session['user_id'])
    task = QCTask.objects.filter(id=task_id, assigned_to=user).select_related('ebr').first()

    if not task:
        return JsonResponse({'error': 'Task not found'}, status=404)

    if request.method == 'POST':
        visual_control = request.POST.get('visual_control', '').strip()
        lab_results = request.POST.get('lab_results', '').strip()
        comments = request.POST.get('comments', '').strip()

        if not visual_control:
            return JsonResponse({'error': 'Заполните визуальный контроль'}, status=400)
        if not lab_results:
            return JsonResponse({'error': 'Заполните время распадаемости'}, status=400)

        # Сохраняем время распадаемости в EBRActualParameter
        try:
            disintegration_value = Decimal(lab_results.replace(',', '.'))
            disintegration_param = Parameter.objects.filter(
                parameter_name__icontains='распадаем'
            ).first()
            if disintegration_param:
                ap, _ = EBRActualParameter.objects.get_or_create(
                    ebr=task.ebr,
                    parameter=disintegration_param,
                    defaults={'actual_value': disintegration_value, 'source': 'manual'}
                )
                if not _:
                    ap.actual_value = disintegration_value
                    ap.source = 'manual'
                    ap.save(update_fields=['actual_value', 'source'])
        except (InvalidOperation, ValueError):
            return JsonResponse({'error': 'Некорректное значение времени распадаемости'}, status=400)

        # Сохраняем результаты
        QCResult.objects.create(
            task=task,
            visual_control=visual_control,
            lab_results=lab_results,
            comments=comments,
            submitted_by=user,
        )

        # Обновляем задание
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at'])

        # Пересчитываем статус EBR
        ebr = task.ebr
        ebr.recalculate_status()

        # Если после пересчёта всё ОК — отправляем на подписание
        if ebr.status.status_name != 'Заблокирована':
            try:
                completed_status = EBRStatus.objects.get(status_name='Завершена')
                ebr.status = completed_status
                ebr.save(update_fields=['status'])
            except EBRStatus.DoesNotExist:
                pass

        return JsonResponse({'success': True, 'message': 'Результаты сохранены, партия завершена'})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def _count_current_deviations(ebr):
    """Считает текущие отклонения по последним значениям параметров."""
    from ebr.models import EBRActualParameter, EBRNominalParameter
    count = 0
    actual_params = EBRActualParameter.objects.filter(ebr=ebr)
    nominal_params = EBRNominalParameter.objects.filter(ebr=ebr)
    for ap in actual_params:
        np = nominal_params.filter(parameter=ap.parameter).first()
        if np and ap.actual_value is not None:
            diff = abs(float(ap.actual_value) - float(np.nominal_value))
            if diff > float(np.critical_value):
                count += 1
            elif diff > float(np.tolerance_value):
                count += 1
    return count


def _has_critical_deviation(ebr):
    """Проверяет наличие критического отклонения по текущим значениям."""
    from ebr.models import EBRActualParameter, EBRNominalParameter
    nominal_params = EBRNominalParameter.objects.filter(ebr=ebr)
    for np in nominal_params:
        ap = EBRActualParameter.objects.filter(ebr=ebr, parameter=np.parameter).first()
        if ap and ap.actual_value is not None:
            diff = abs(float(ap.actual_value) - float(np.nominal_value))
            if diff > float(np.critical_value):
                return True
    return False


def qc_chief_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'начальник ОКК':
        return redirect('users:login')

    from quality.models import Deviation, QCResult
    from ebr.models import EBR, EBRStatus
    from audit.models import AuditLog

    user = User.objects.get(user_id=request.session['user_id'])

    # Вкладка 1: Проверка EBR — партии «Завершена» (без подписи) и «Заблокирована» (критические отклонения)
    pending_review = EBR.objects.filter(
        status__status_name__in=['Завершена', 'Заблокирована'],
        signed_by__isnull=True
    ).select_related('mbr__product', 'status').order_by('-start_date')[:30]

    # Подтягиваем отклонения и QC результаты для каждой партии
    for ebr in pending_review:
        ebr.deviation_count = _count_current_deviations(ebr)
        ebr.has_critical = _has_critical_deviation(ebr)
        ebr.has_deviation = ebr.deviation_count > 0
        # QCResult
        qc_result = QCResult.objects.filter(task__ebr=ebr).first()
        ebr.qc_visual = qc_result.visual_control if qc_result else None
        ebr.qc_lab = qc_result.lab_results if qc_result else None
        ebr.qc_comments = qc_result.comments if qc_result else None

    # Вкладка 2: Архив — партии со статусом «Завершена» или «Заблокирована» где есть решение (подписаны)
    archived = EBR.objects.filter(
        status__status_name__in=['Завершена', 'Заблокирована'],
        signed_by__isnull=False
    ).select_related('mbr__product', 'signed_by').order_by('-completion_date')[:30]

    for ebr in archived:
        ebr.qc_result = QCResult.objects.filter(task__ebr=ebr).first()
        ebr.deviation_count = Deviation.objects.filter(ebr=ebr).count()
        ebr.has_critical = Deviation.objects.filter(ebr=ebr, deviation_type='critical').exists()

    # Вкладка 3: Аудит
    audit_logs = AuditLog.objects.all().select_related('user', 'action', 'document').order_by('-timestamp')[:50]

    context = {
        'user': user,
        'pending_review': pending_review,
        'archived': archived,
        'audit_logs': audit_logs,
    }
    return render(request, 'users/qc_chief_dashboard.html', context)


def qc_chief_pending_api(request):
    """AJAX endpoint: список партий на проверке у начальника ОКК"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'начальник ОКК':
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    from quality.models import Deviation, QCResult
    from ebr.models import EBR

    try:
        pending = EBR.objects.filter(
            status__status_name__in=['Завершена', 'Заблокирована'],
            signed_by__isnull=True
        ).select_related('mbr__product', 'status').order_by('-start_date')[:30]

        result = []
        for ebr in pending:
            qc = QCResult.objects.filter(task__ebr=ebr).first()
            dev_count = _count_current_deviations(ebr)
            result.append({
                'document_id': ebr.document_id,
                'batch_number': ebr.batch_number,
                'product': ebr.mbr.product.product_name,
                'status': ebr.status.status_name,
                'deviation_count': dev_count,
                'qc_visual': qc.visual_control if qc else None,
                'qc_comments': qc.comments if qc else None,
            })

        return JsonResponse({'success': True, 'pending': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def qc_chief_archive_api(request):
    """AJAX endpoint: архив партий начальника ОКК"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'начальник ОКК':
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    from quality.models import QCResult, Deviation
    from ebr.models import EBR

    try:
        archived = EBR.objects.filter(
            status__status_name__in=['Завершена', 'Заблокирована'],
            signed_by__isnull=False
        ).select_related('mbr__product', 'signed_by').order_by('-completion_date')[:30]

        result = []
        for ebr in archived:
            qc = QCResult.objects.filter(task__ebr=ebr).first()
            dev_count = Deviation.objects.filter(ebr=ebr).count()
            has_critical = Deviation.objects.filter(ebr=ebr, deviation_type='critical').exists()
            result.append({
                'document_id': ebr.document_id,
                'batch_number': ebr.batch_number,
                'product': ebr.mbr.product.product_name,
                'status': ebr.status.status_name,
                'completion_date': ebr.completion_date.isoformat() if ebr.completion_date else None,
                'signed_by': (ebr.signed_by.last_name + ' ' + ebr.signed_by.first_name) if ebr.signed_by else '—',
                'deviation_count': dev_count,
                'has_critical': has_critical,
                'qc_visual': qc.visual_control if qc else None,
                'qc_comments': qc.comments if qc else None,
            })

        return JsonResponse({'success': True, 'archived': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def ebr_reject(request, pk):
    """Начальник ОКК отклоняет EBR."""
    from ebr.models import EBR, EBRStatus
    from django.utils import timezone

    if 'user_id' not in request.session or request.session.get('user_role') != 'начальник ОКК':
        return redirect('users:login')

    ebr = get_object_or_404(EBR, document_id=pk)

    if request.method == 'POST':
        try:
            blocked_status = EBRStatus.objects.get(status_name='Заблокирована')
        except EBRStatus.DoesNotExist:
            messages.error(request, 'Статус "Заблокирована" не найден')
            return redirect('users:qc_chief_dashboard')

        ebr.status = blocked_status
        ebr.signed_by = request.current_user
        ebr.completion_date = timezone.now()
        ebr.save(update_fields=['status', 'signed_by', 'completion_date'])

        from audit.models import Action, AuditLog
        try:
            action = Action.objects.get(action_name='Отклонение EBR')
        except Action.DoesNotExist:
            action = Action.objects.create(action_name='Отклонение EBR')

        AuditLog.objects.create(
            user=request.current_user,
            action=action,
            document=ebr.document,
            comment=f"EBR {ebr.batch_number} отклонён"
        )

        messages.success(request, f'Партия {ebr.batch_number} отклонена')

    return redirect('users:qc_chief_dashboard')


def director_dashboard(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'директор':
        return redirect('users:login')

    from reports.models import GeneratedReport
    from ebr.models import EBR, EBRStatus, EBRActualParameter, EBRNominalParameter
    from quality.models import Deviation
    from mbr.models import Product
    from django.db.models import Count
    from datetime import datetime, timedelta
    import os, uuid
    from django.conf import settings

    user = User.objects.get(user_id=request.session['user_id'])

    # === Синхронизация Deviation из EBR при каждой загрузке ===
    def _sync_deviations_from_ebr():
        """Анализирует все EBR и заполняет таблицу Deviation."""
        from ebr.models import EBRActualParameter, EBRNominalParameter
        
        # Удаляем только те Deviation, которые созданы этой функцией (с description содержащим "diff=")
        # Deviation из quality/views.py (время распадаемости) останутся
        Deviation.objects.filter(description__contains='diff=').delete()
        
        ebrs = EBR.objects.all().prefetch_related('operations')
        for ebr in ebrs:
            actual_params = EBRActualParameter.objects.filter(ebr=ebr)
            for ap in actual_params:
                if ap.actual_value is None:
                    continue
                try:
                    nominal = EBRNominalParameter.objects.get(ebr=ebr, parameter=ap.parameter)
                except EBRNominalParameter.DoesNotExist:
                    continue

                diff = abs(float(ap.actual_value) - float(nominal.nominal_value))
                tol = float(nominal.tolerance_value)
                crit = float(nominal.critical_value)

                # Определяем тип отклонения
                dev_type = None
                if crit > 0 and diff > crit:
                    dev_type = 'critical'
                elif tol > 0 and diff > tol:
                    dev_type = 'deviation'
                elif tol > 0 and diff > tol * 0.9:
                    dev_type = 'warning'

                if dev_type:
                    Deviation.objects.create(
                        ebr=ebr,
                        deviation_type=dev_type,
                        parameter_name=nominal.parameter.parameter_name,
                        expected_value=nominal.nominal_value,
                        actual_value=ap.actual_value,
                        tolerance=nominal.tolerance_value,
                        description=f"{dev_type}: diff={diff:.2f}",
                        detected_at=ebr.start_date,
                    )

    _sync_deviations_from_ebr()
    # ============================================================

    # Фильтр по датам (GET-параметры для графиков)
    filter_start = request.GET.get('start_date')
    filter_end = request.GET.get('end_date')

    # Определяем период: по умолчанию последние 30 дней
    try:
        if filter_start and filter_end:
            period_start = datetime.strptime(filter_start, '%Y-%m-%d')
            period_end = datetime.strptime(filter_end, '%Y-%m-%d')
        else:
            period_end = timezone.now()
            period_start = period_end - timedelta(days=30)
    except (ValueError, TypeError):
        period_end = timezone.now()
        period_start = period_end - timedelta(days=30)

    month_ago = period_start

    # Обработка POST (генерация отчётов)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'generate_report':
            report_type = request.POST.get('report_type', 'production')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            fmt = request.POST.get('format', 'excel')

            try:
                sd = datetime.strptime(start_date, '%d.%m.%Y')
                ed = datetime.strptime(end_date, '%d.%m.%Y')
            except (ValueError, TypeError):
                try:
                    sd = datetime.strptime(start_date, '%Y-%m-%d')
                    ed = datetime.strptime(end_date, '%Y-%m-%d')
                except (ValueError, TypeError):
                    sd = month_ago
                    ed = timezone.now()

            # Генерируем отчёт
            from reports.views import _generate_report_data
            data = _generate_report_data(report_type, sd, ed)

            filename = f"report_{report_type}_{uuid.uuid4().hex[:8]}"
            if fmt == 'excel':
                from openpyxl import Workbook
                from openpyxl.styles import Font, Alignment, PatternFill
                wb = Workbook()
                ws = wb.active
                ws.title = "Отчёт"

                def sanitize_for_excel(val):
                    """Убирает timezone из datetime для openpyxl."""
                    import datetime as dt_module
                    if isinstance(val, dt_module.datetime) and val.tzinfo is not None:
                        return val.replace(tzinfo=None)
                    if isinstance(val, dt_module.date) and not isinstance(val, dt_module.datetime):
                        return val
                    return val

                row_num = 1

                # Заголовок отчёта
                title_font = Font(bold=True, size=14)
                header_font = Font(bold=True)
                header_fill = PatternFill(start_color="2a83bd", end_color="2a83bd", fill_type="solid")
                header_font_white = Font(bold=True, color="FFFFFF")

                if report_type == 'production':
                    ws.cell(row=row_num, column=1, value=f"Отчёт по выпуску продукции за период {sd.strftime('%d.%m.%Y')} — {ed.strftime('%d.%m.%Y')}").font = title_font
                    ws.merge_cells(f'A{row_num}:G{row_num}')
                    row_num += 2

                    # Сводка
                    ws.cell(row=row_num, column=1, value="Сводка по продуктам").font = Font(bold=True, size=12)
                    row_num += 1
                    for col, h in enumerate(data.get('summary_headers', []), 1):
                        cell = ws.cell(row=row_num, column=col, value=h)
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.font = header_font_white
                    row_num += 1
                    for rrow in data.get('summary_rows', []):
                        for col, val in enumerate(rrow, 1):
                            ws.cell(row=row_num, column=col, value=sanitize_for_excel(val))
                        row_num += 1

                    row_num += 2
                    ws.cell(row=row_num, column=1, value=f"Итого партий: {data.get('total', 0)}  |  Завершено: {data.get('completed', 0)}  |  Заблокировано: {data.get('blocked', 0)}  |  Брак: {data.get('defect_pct', 0)}%").font = Font(bold=True)
                    row_num += 2

                    # Детализация
                    ws.cell(row=row_num, column=1, value="Детализация по партиям").font = Font(bold=True, size=12)
                    row_num += 1
                    for col, h in enumerate(data.get('headers', []), 1):
                        cell = ws.cell(row=row_num, column=col, value=h)
                        cell.font = header_font_white
                        cell.fill = header_fill
                    row_num += 1
                    for rrow in data.get('rows', []):
                        for col, val in enumerate(rrow, 1):
                            ws.cell(row=row_num, column=col, value=sanitize_for_excel(val))
                        row_num += 1

                elif report_type == 'deviation':
                    ws.cell(row=row_num, column=1, value=f"Отчёт по отклонениям за период {sd.strftime('%d.%m.%Y')} — {ed.strftime('%d.%m.%Y')}").font = title_font
                    ws.merge_cells(f'A{row_num}:J{row_num}')
                    row_num += 2

                    ws.cell(row=row_num, column=1, value=f"Всего отклонений: {data.get('total_deviations', 0)}").font = Font(bold=True)
                    row_num += 2

                    by_type = data.get('by_type', {})
                    type_labels = {'warning': 'Предупреждение', 'deviation': 'Отклонение', 'critical': 'Критическое отклонение'}
                    for dtype, label in type_labels.items():
                        ws.cell(row=row_num, column=1, value=f"{label}: {by_type.get(dtype, 0)}")
                        row_num += 1

                    row_num += 1
                    # Таблица отклонений
                    for col, h in enumerate(data.get('headers', []), 1):
                        cell = ws.cell(row=row_num, column=col, value=h)
                        cell.font = header_font_white
                        cell.fill = header_fill
                    row_num += 1
                    for rrow in data.get('rows', []):
                        for col, val in enumerate(rrow, 1):
                            ws.cell(row=row_num, column=col, value=sanitize_for_excel(val))
                        row_num += 1

                elif report_type == 'efficiency':
                    ws.cell(row=row_num, column=1, value=f"Отчёт по эффективности за период {sd.strftime('%d.%m.%Y')} — {ed.strftime('%d.%m.%Y')}").font = title_font
                    ws.merge_cells(f'A{row_num}:B{row_num}')
                    row_num += 2

                    metrics = [
                        ('Всего партий', data.get('total_batches', 0)),
                        ('Завершено', data.get('completed', 0)),
                        ('Заблокировано', data.get('blocked', 0)),
                        ('В работе', data.get('in_progress', 0)),
                        ('В ожидании', data.get('waiting', 0)),
                        ('Эффективность', f"{data.get('efficiency', 0)}%"),
                        ('Процент брака', f"{data.get('defect_rate', 0)}%"),
                    ]
                    for label, value in metrics:
                        ws.cell(row=row_num, column=1, value=label).font = Font(bold=True)
                        ws.cell(row=row_num, column=2, value=value)
                        row_num += 1

                filepath = os.path.join(settings.MEDIA_ROOT, 'reports', f"{filename}.xlsx")
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                wb.save(filepath)
                file_rel = os.path.join('reports', f"{filename}.xlsx")
            else:
                import csv
                import datetime as dt_module

                def sanitize_for_excel(val):
                    if isinstance(val, dt_module.datetime) and val.tzinfo is not None:
                        return val.replace(tzinfo=None)
                    if isinstance(val, dt_module.date) and not isinstance(val, dt_module.datetime):
                        return val
                    return val

                filepath = os.path.join(settings.MEDIA_ROOT, 'reports', f"{filename}.csv")
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    if report_type == 'production':
                        writer.writerow([f"Отчёт по выпуску продукции за период {sd.strftime('%d.%m.%Y')} — {ed.strftime('%d.%m.%Y')}"])
                        writer.writerow([])
                        writer.writerow(data.get('summary_headers', []))
                        for rrow in data.get('summary_rows', []):
                            writer.writerow(rrow)
                        writer.writerow([])
                        writer.writerow([f"Итого: {data.get('total', 0)} партий, завершено {data.get('completed', 0)}, заблокировано {data.get('blocked', 0)}, брак {data.get('defect_pct', 0)}%"])
                        writer.writerow([])
                        writer.writerow(data.get('headers', []))
                        for rrow in data.get('rows', []):
                            writer.writerow([sanitize_for_excel(v) for v in rrow])
                    elif report_type == 'deviation':
                        writer.writerow([f"Отчёт по отклонениям за период {sd.strftime('%d.%m.%Y')} — {ed.strftime('%d.%m.%Y')}"])
                        writer.writerow([f"Всего отклонений: {data.get('total_deviations', 0)}"])
                        writer.writerow([])
                        writer.writerow(data.get('headers', []))
                        for rrow in data.get('rows', []):
                            writer.writerow([sanitize_for_excel(v) for v in rrow])
                    elif report_type == 'efficiency':
                        writer.writerow([f"Отчёт по эффективности за период {sd.strftime('%d.%m.%Y')} — {ed.strftime('%d.%m.%Y')}"])
                        writer.writerow([])
                        for label, value in [
                            ('Всего партий', data.get('total_batches', 0)),
                            ('Завершено', data.get('completed', 0)),
                            ('Заблокировано', data.get('blocked', 0)),
                            ('В работе', data.get('in_progress', 0)),
                            ('В ожидании', data.get('waiting', 0)),
                            ('Эффективность', f"{data.get('efficiency', 0)}%"),
                            ('Процент брака', f"{data.get('defect_rate', 0)}%"),
                        ]:
                            writer.writerow([label, value])
                file_rel = os.path.join('reports', f"{filename}.csv")

            # Создаём или получаем шаблон
            from reports.models import ReportTemplate
            try:
                template = ReportTemplate.objects.get(report_type=report_type)
            except ReportTemplate.DoesNotExist:
                template = ReportTemplate.objects.create(
                    report_type=report_type,
                    name=f'Отчёт {report_type}',
                    is_active=True,
                )

            GeneratedReport.objects.create(
                template=template,
                generated_by=user,
                start_date=sd,
                end_date=ed,
                format=fmt,
                file=file_rel
            )
            messages.success(request, 'Отчёт сгенерирован')
            return redirect('users:director_dashboard')

    # KPI при загрузке страницы — только подписанные (Завершена/Заблокирована + signed_by)
    total_batches = EBR.objects.filter(
        status__status_name__in=['Завершена', 'Заблокирована'],
        signed_by__isnull=False,
        start_date__gte=month_ago
    ).count()
    completed_batches = EBR.objects.filter(
        start_date__gte=month_ago, status__status_name='Завершена', signed_by__isnull=False
    ).count()
    blocked_batches = EBR.objects.filter(
        start_date__gte=month_ago, status__status_name='Заблокирована', signed_by__isnull=False
    ).count()

    # Отклонения за период — прямой запрос через ebr__start_date
    dev_kwargs_main = {}
    dev_kwargs_main['ebr__start_date__date__gte'] = month_ago
    total_deviations = Deviation.objects.filter(**dev_kwargs_main).count()

    defect_rate = 0
    if total_batches > 0:
        defect_rate = round((blocked_batches / total_batches) * 100, 1)

    efficiency = 0
    if total_batches > 0:
        efficiency = round((completed_batches / total_batches) * 100, 1)

    monthly_stats = {
        'batches': total_batches,
        'defect_rate': defect_rate,
        'deviations': total_deviations,
        'efficiency': efficiency,
    }

    # Статистика по продуктам
    products = Product.objects.all()
    product_stats = []
    for p in products:
        p_batches = EBR.objects.filter(mbr__product=p, start_date__gte=month_ago).count()
        p_blocked = EBR.objects.filter(mbr__product=p, start_date__gte=month_ago, status__status_name='Заблокирована').count()
        p_defect = round((p_blocked / p_batches * 100), 1) if p_batches > 0 else 0
        product_stats.append({
            'product_name': p.product_name,
            'batches': p_batches,
            'defect_rate': p_defect,
        })

    # Статистика по отклонениям — прямой запрос через ebr__start_date
    deviation_stats = {}
    dev_kwargs_main = {}
    if month_ago:
        dev_kwargs_main['ebr__start_date__date__gte'] = month_ago
    from django.db.models import Count
    for item in Deviation.objects.filter(**dev_kwargs_main).values('deviation_type').annotate(cnt=Count('id')):
        deviation_stats[item['deviation_type']] = item['cnt']

    deviation_stats_labeled = {}
    total_deviations = 0
    for dtype, label in [('warning', 'Предупреждение'), ('deviation', 'Отклонение'), ('critical', 'Критическое отклонение')]:
        cnt = deviation_stats.get(dtype, 0)
        deviation_stats_labeled[label] = cnt
        total_deviations += cnt

    # Процент от общего числа отклонений — список кортежей для шаблона
    deviation_rows = []
    for dtype, label in [('warning', 'Предупреждение'), ('deviation', 'Отклонение'), ('critical', 'Критическое отклонение')]:
        cnt = deviation_stats.get(dtype, 0)
        pct = round((cnt / total_deviations * 100), 1) if total_deviations > 0 else 0
        deviation_rows.append({'type': label, 'count': cnt, 'pct': pct})

    recent_reports = GeneratedReport.objects.filter(generated_by=user).order_by('-generated_at')[:6]

    # Начальные данные для графиков
    initial_stats = {
        'product_chart': [],
        'status_chart': {},
    }
    for p in products:
        cnt = EBR.objects.filter(mbr__product=p, start_date__gte=month_ago).count()
        if cnt > 0:
            initial_stats['product_chart'].append({
                'product_code': p.product_code,
                'product_name': p.product_name,
                'count': cnt,
            })
    for status_name in ['Завершена', 'Заблокирована', 'В работе', 'В ожидании']:
        cnt = EBR.objects.filter(status__status_name=status_name, start_date__gte=month_ago).count()
        if cnt > 0:
            initial_stats['status_chart'][status_name] = cnt

    context = {
        'user': user,
        'monthly_stats': monthly_stats,
        'product_stats': product_stats,
        'deviation_stats': deviation_stats_labeled,
        'deviation_rows': deviation_rows,
        'total_deviations': total_deviations,
        'recent_reports': recent_reports,
        # Для отображения в фильтре (ДД.ММ.ГГГГ)
        'filter_start': period_start.strftime('%d.%m.%Y'),
        'filter_end': period_end.strftime('%d.%m.%Y'),
        # Для input type="date" (YYYY-MM-DD)
        'filter_start_iso': period_start.strftime('%Y-%m-%d'),
        'filter_end_iso': period_end.strftime('%Y-%m-%d'),
        'initial_stats_json': json.dumps(initial_stats, ensure_ascii=False),
    }
    return render(request, 'users/director_dashboard.html', context)



from mbr.models import MBR, Parameter, RawMaterial, MBRParameter


def get_mbr_parameters(request, mbr_id):
    """API для получения параметров MBR"""
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        mbr = MBR.objects.select_related('product', 'status', 'document').get(document_id=mbr_id)
        # Получаем параметры из MBRParameter (собственные значения этого MBR)
        mbr_params = MBRParameter.objects.filter(mbr=mbr).select_related('parameter')
        
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
                    'id': mp.parameter.id,
                    'name': mp.parameter.parameter_name,
                    'value': float(mp.value),
                    'unit': mp.parameter.unit,
                    'tolerance': float(mp.tolerance),
                    'critical': float(mp.critical_deviation)
                } for mp in mbr_params
            ],
            'raw_materials': [
                {
                    'id': rm.id,
                    'name': rm.material_name
                } for rm in mbr.raw_materials.all()
            ]
        }
        return JsonResponse(data)
    except MBR.DoesNotExist:
        return JsonResponse({'error': 'MBR not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_mbr_for_edit(request, mbr_id):
    """API для получения данных MBR для редактирования"""
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        mbr = MBR.objects.get(document_id=mbr_id)

        # Проверяем, что MBR в статусе черновика
        if mbr.status.status_name != 'Черновик':
            return JsonResponse({'error': 'Can only edit draft MBR'}, status=400)

        # Получаем параметры из MBRParameter
        mbr_params = MBRParameter.objects.filter(mbr=mbr).select_related('parameter')

        data = {
            'id': mbr.document_id,
            'product_id': mbr.product.id,
            'product_code': mbr.product.product_code,
            'product_name': mbr.product.product_name,
            'version': mbr.version,
            'operations': mbr.operations,
            'comments': mbr.comments,
            'parameters': [
                {
                    'id': mp.parameter.id,
                    'name': mp.parameter.parameter_name,
                    'value': float(mp.value),
                    'unit': mp.parameter.unit,
                    'tolerance': float(mp.tolerance),
                    'critical': float(mp.critical_deviation)
                } for mp in mbr_params
            ],
            'raw_materials': [
                {
                    'id': rm.id,
                    'name': rm.material_name
                } for rm in mbr.raw_materials.all()
            ]
        }
        return JsonResponse(data)
    except MBR.DoesNotExist:
        return JsonResponse({'error': 'MBR not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def update_mbr(request, mbr_id):
    """Обновление существующего MBR"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        mbr = MBR.objects.get(document_id=mbr_id)

        # Проверяем статус
        if mbr.status.status_name != 'Черновик':
            return JsonResponse({'error': 'Can only edit draft MBR'}, status=400)

        # Обновляем поля
        operations = request.POST.get('operations')
        comments = request.POST.get('comments')

        if operations:
            mbr.operations = operations
        if comments is not None:  # может быть пустым
            mbr.comments = comments

        mbr.save()

        # Обновляем сырьё (сначала очищаем, потом добавляем новые)
        mbr.raw_materials.clear()
        raw_material_ids = request.POST.getlist('raw_materials')
        for rm_id in raw_material_ids:
            if rm_id and rm_id.isdigit():
                try:
                    material = RawMaterial.objects.get(id=int(rm_id))
                    mbr.raw_materials.add(material)
                except RawMaterial.DoesNotExist:
                    pass

        # Обновляем параметры (создаём новые MBRParameter вместо изменения глобальных Parameter)
        # Сначала удаляем старые
        MBRParameter.objects.filter(mbr=mbr).delete()

        for key, value in request.POST.items():
            if key.startswith('param_value_'):
                param_id = key.replace('param_value_', '')
                if not param_id or not param_id.isdigit():
                    continue

                try:
                    parameter = Parameter.objects.get(id=int(param_id))

                    param_value_str = request.POST.get(f'param_value_{param_id}', '0')
                    param_tolerance_str = request.POST.get(f'param_tolerance_{param_id}', '0')
                    param_critical_str = request.POST.get(f'param_critical_{param_id}', '0')

                    try:
                        param_value = float(param_value_str.replace(',', '.'))
                    except (ValueError, AttributeError):
                        param_value = 0

                    try:
                        param_tolerance = float(param_tolerance_str.replace(',', '.'))
                    except (ValueError, AttributeError):
                        param_tolerance = 0

                    try:
                        param_critical = float(param_critical_str.replace(',', '.'))
                    except (ValueError, AttributeError):
                        param_critical = 0

                    # Создаём MBRParameter с СОБСТВЕННЫМИ значениями для ЭТОГО MBR
                    MBRParameter.objects.create(
                        mbr=mbr,
                        parameter=parameter,
                        value=param_value,
                        tolerance=param_tolerance,
                        critical_deviation=param_critical
                    )
                except Parameter.DoesNotExist:
                    pass

        # Логируем действие
        try:
            from audit.models import Action, AuditLog
            action_obj = Action.objects.get(action_name='Редактирование MBR')
            AuditLog.objects.create(
                user=User.objects.get(user_id=request.session['user_id']),
                action=action_obj,
                document=mbr.document,
                comment=f"Отредактирован MBR для {mbr.product.product_code}"
            )
        except:
            pass

        return JsonResponse({'success': True, 'message': 'MBR updated successfully'})

    except MBR.DoesNotExist:
        return JsonResponse({'error': 'MBR not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def deactivate_user(request, user_id):
    """Деактивация пользователя (только для системного администратора)"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'системный администратор':
        messages.error(request, 'У вас нет доступа к этой функции')
        return redirect('users:admin_dashboard')

    if request.method == 'POST':
        user_to_deactivate = get_object_or_404(User, user_id=user_id)
        
        # Нельзя деактивировать самого себя
        if user_to_deactivate.user_id == request.session['user_id']:
            messages.error(request, 'Нельзя деактивировать свою учетную запись')
            return redirect('users:admin_dashboard')
        
        user_to_deactivate.is_active = False
        user_to_deactivate.save()

        # Логируем
        try:
            action = Action.objects.get(action_name='Деактивация пользователя')
            AuditLog.objects.create(
                user=User.objects.get(user_id=request.session['user_id']),
                action=action,
                comment=f"Деактивирован пользователь {user_to_deactivate.login}"
            )
        except:
            pass

        messages.success(request, f'Пользователь {user_to_deactivate.login} деактивирован')
    
    return redirect('users:admin_dashboard')


def batch_number_rules(request):
    """Настройка правил генерации номеров партий (только для системного администратора)"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'системный администратор':
        messages.error(request, 'У вас нет доступа к этой функции')
        return redirect('users:admin_dashboard')

    user = User.objects.get(user_id=request.session['user_id'])

    if request.method == 'POST':
        rule = request.POST.get('batch_rule')
        
        # Сохраняем правило в сессии (в реальном проекте - в БД)
        request.session['batch_number_rule'] = rule
        
        messages.success(request, f'Правило генерации номеров партий обновлено: {rule}')
        
        # Логируем
        try:
            action = Action.objects.get(action_name='Изменение правил генерации номеров партий')
            AuditLog.objects.create(
                user=user,
                action=action,
                comment=f"Установлено правило: {rule}"
            )
        except:
            pass
        
        return redirect('users:admin_dashboard')

    # Получаем текущее правило
    current_rule = request.session.get('batch_number_rule', 'B-<Код продукта>-<Год>-<Номер партии>')

    context = {
        'user': user,
        'current_rule': current_rule,
    }
    return render(request, 'users/batch_rules.html', context)


def approve_mbr_api(request, mbr_id):
    """API для утверждения MBR (вызывается из chief_technologist_dashboard)"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        from mbr.models import MBR, MBRStatus, MBRParameter

        mbr = MBR.objects.select_related('status', 'document', 'product').get(document_id=mbr_id)

        # Проверяем, что MBR в статусе черновика
        if mbr.status.status_name != 'Черновик':
            return JsonResponse({'error': 'MBR уже утверждён'}, status=400)

        # === ВАЛИДАЦИЯ: проверяем что всё заполнено ===
        errors = []

        # Проверяем продукт
        if not mbr.product:
            errors.append('Не выбран продукт')

        # Проверяем операции
        if not mbr.operations or not mbr.operations.strip():
            errors.append('Не заполнены технологические операции')

        # Проверяем параметры
        param_count = MBRParameter.objects.filter(mbr=mbr).count()
        if param_count == 0:
            errors.append('Не добавлены параметры')
        else:
            # Проверяем что у всех параметров есть значения
            empty_params = MBRParameter.objects.filter(mbr=mbr, value=0)
            if empty_params.exists():
                param_names = ', '.join([p.parameter.parameter_name for p in empty_params[:3]])
                errors.append(f'Не заполнены значения параметров: {param_names}')

        # Проверяем сырьё
        if mbr.raw_materials.count() == 0:
            errors.append('Не добавлено сырьё')

        if errors:
            return JsonResponse({
                'success': False,
                'error': 'Внесённая информация не является полной: ' + '; '.join(errors)
            }, status=400)

        # === ВСЁ ЗАПОЛНЕНО — утверждаем ===
        approved_status = MBRStatus.objects.get(status_name='Утверждён')

        # Обновляем MBR
        mbr.status_id = approved_status.id
        mbr.approval_date = datetime.date.today()
        mbr.signed_by_id = request.session['user_id']
        mbr.save(update_fields=['status_id', 'approval_date', 'signed_by_id'])

        # Логируем
        try:
            action = Action.objects.get(action_name='Утверждение MBR')
            AuditLog.objects.create(
                user_id=request.session['user_id'],
                action=action,
                document=mbr.document,
                comment=f"Утверждён MBR {mbr.product.product_code} {mbr.version} "
                        f"({mbr.product.product_name}). "
                        f"Утвердил: {request.current_user.last_name} {request.current_user.first_name}"
            )
        except Exception as e:
            logger.error(f"Logging error: {e}")

        return JsonResponse({'success': True, 'message': 'MBR утверждён'})

    except MBR.DoesNotExist:
        return JsonResponse({'error': 'MBR not found'}, status=404)
    except MBRStatus.DoesNotExist:
        return JsonResponse({'error': 'Approved status not found'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def director_stats_api(request):
    """API: данные для графиков и KPI панели директора."""
    if 'user_id' not in request.session or request.session.get('user_role') != 'директор':
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)

    from ebr.models import EBR, EBRStatus
    from mbr.models import Product

    # Фильтр по датам
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    kwargs = {}
    if start_date:
        try:
            sd = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            kwargs['start_date__date__gte'] = sd
        except ValueError:
            return JsonResponse({'error': 'Неверный формат start_date'}, status=400)
    if end_date:
        try:
            ed = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            kwargs['start_date__date__lte'] = ed
        except ValueError:
            return JsonResponse({'error': 'Неверный формат end_date'}, status=400)

    # KPI: только партии по которым принято решение (статус Завершена/Заблокирована + подписаны)
    total_signed = EBR.objects.filter(
        status__status_name__in=['Завершена', 'Заблокирована'],
        signed_by__isnull=False,
        **kwargs
    ).count()
    completed_signed = EBR.objects.filter(status__status_name='Завершена', signed_by__isnull=False, **kwargs).count()
    blocked_signed = EBR.objects.filter(status__status_name='Заблокирована', signed_by__isnull=False, **kwargs).count()

    defect_rate = round((blocked_signed / total_signed * 100), 1) if total_signed > 0 else 0
    efficiency = round((completed_signed / total_signed * 100), 1) if total_signed > 0 else 0

    # Отклонения за период — прямой запрос к Deviation через ebr__start_date
    from quality.models import Deviation
    from django.db.models import Count
    dev_kwargs = {}
    if 'start_date__date__gte' in kwargs:
        dev_kwargs['ebr__start_date__date__gte'] = kwargs['start_date__date__gte']
    if 'start_date__date__lte' in kwargs:
        dev_kwargs['ebr__start_date__date__lte'] = kwargs['start_date__date__lte']
    
    total_deviations = 0
    deviation_by_type = {'warning': 0, 'deviation': 0, 'critical': 0}
    qs = Deviation.objects.filter(**dev_kwargs)
    for item in qs.values('deviation_type').annotate(cnt=Count('id')):
        deviation_by_type[item['deviation_type']] = item['cnt']
        total_deviations += item['cnt']

    # 1. Круговая: выпуск по продуктам
    product_counts = []
    products = Product.objects.all()
    for p in products:
        cnt = EBR.objects.filter(mbr__product=p, **kwargs).count()
        if cnt > 0:
            product_counts.append({
                'product_code': p.product_code,
                'product_name': p.product_name,
                'count': cnt,
            })

    # 2. Гистограмма: партии по статусам
    status_counts = {}
    for status_name in ['Завершена', 'Заблокирована', 'В работе', 'В ожидании']:
        cnt = EBR.objects.filter(status__status_name=status_name, **kwargs).count()
        if cnt > 0:
            status_counts[status_name] = cnt

    # 3. Отклонения — прямой запрос через ebr__start_date
    dev_kwargs_api = {}
    if 'start_date__date__gte' in kwargs:
        dev_kwargs_api['ebr__start_date__date__gte'] = kwargs['start_date__date__gte']
    if 'start_date__date__lte' in kwargs:
        dev_kwargs_api['ebr__start_date__date__lte'] = kwargs['start_date__date__lte']

    deviation_stats = {}
    qs_api = Deviation.objects.filter(**dev_kwargs_api)
    for item in qs_api.values('deviation_type').annotate(cnt=Count('id')):
        deviation_stats[item['deviation_type']] = item['cnt']

    # Маппинг на русские label
    deviation_by_label = {}
    for dtype, label in [('warning', 'Предупреждение'), ('deviation', 'Отклонение'), ('critical', 'Критическое отклонение')]:
        cnt = deviation_stats.get(dtype, 0)
        if cnt > 0:
            deviation_by_label[label] = cnt

    return JsonResponse({
        'kpi': {
            'batches': total_signed,
            'defect_rate': defect_rate,
            'deviations': total_deviations,
            'efficiency': efficiency,
        },
        'product_chart': product_counts,
        'status_chart': status_counts,
        'deviation_stats': deviation_by_label,
    })


# ====================================================================
# API для справочников (администратор)
# ====================================================================

def api_admin_raw_materials(request):
    """CRUD справочника сырья (только администратор)."""
    if 'user_id' not in request.session or request.session.get('user_role') != 'системный администратор':
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)

    from mbr.models import RawMaterial
    admin_user = User.objects.get(user_id=request.session['user_id'])

    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Наименование не может быть пустым'}, status=400)
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-]+$', name):
            return JsonResponse({'error': 'Только буквы, цифры, пробелы и дефис'}, status=400)
        rm = RawMaterial.objects.create(material_name=name)
        return JsonResponse({'id': rm.pk, 'name': rm.material_name})

    elif request.method == 'PUT':
        import json
        data = json.loads(request.body)
        rm_id = data.get('id')
        name = data.get('name', '').strip()
        rm = get_object_or_404(RawMaterial, pk=rm_id)
        if not name or not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-]+$', name):
            return JsonResponse({'error': 'Неверное наименование'}, status=400)
        rm.material_name = name
        rm.save()
        return JsonResponse({'id': rm.pk, 'name': rm.material_name})

    elif request.method == 'DELETE':
        import json
        data = json.loads(request.body)
        rm = get_object_or_404(RawMaterial, pk=data.get('id'))
        rm.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def api_admin_products(request):
    """CRUD справочника продуктов (только администратор)."""
    if 'user_id' not in request.session or request.session.get('user_role') != 'системный администратор':
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)

    from mbr.models import Product
    admin_user = User.objects.get(user_id=request.session['user_id'])

    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        name = data.get('name', '').strip()
        if not code or not re.match(r'^[a-zA-Z0-9\-]+$', code):
            return JsonResponse({'error': 'Код: только латиница, цифры, минус'}, status=400)
        if not name or not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-]+$', name):
            return JsonResponse({'error': 'Наименование: только буквы, цифры, пробелы, дефис'}, status=400)
        if Product.objects.filter(product_code=code).exists():
            return JsonResponse({'error': 'Код продукта уже существует'}, status=400)
        p = Product.objects.create(product_code=code, product_name=name)
        return JsonResponse({'id': p.pk, 'code': p.product_code, 'name': p.product_name})

    elif request.method == 'PUT':
        import json
        data = json.loads(request.body)
        p_id = data.get('id')
        code = data.get('code', '').strip()
        name = data.get('name', '').strip()
        p = get_object_or_404(Product, pk=p_id)
        if not code or not re.match(r'^[a-zA-Z0-9\-]+$', code):
            return JsonResponse({'error': 'Код: только латиница, цифры, минус'}, status=400)
        if not name or not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-]+$', name):
            return JsonResponse({'error': 'Наименование: только буквы, цифры, пробелы, дефис'}, status=400)
        if Product.objects.filter(product_code=code).exclude(pk=p_id).exists():
            return JsonResponse({'error': 'Код продукта уже существует'}, status=400)
        p.product_code = code
        p.product_name = name
        p.save()
        return JsonResponse({'id': p.pk, 'code': p.product_code, 'name': p.product_name})

    elif request.method == 'DELETE':
        import json
        data = json.loads(request.body)
        p = get_object_or_404(Product, pk=data.get('id'))
        p.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Method not allowed'}, status=405)