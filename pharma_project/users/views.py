from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import User
from audit.models import Action, AuditLog
from mbr.models import DocumentType, Document
import re
import datetime
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
    from django.db.models import Max

    user = User.objects.get(user_id=request.session['user_id'])

    # Только последняя утверждённая версия каждого продукта
    # Находим max document_id для каждого product_id среди утверждённых
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

    context = {
        'user': user,
        'approved_mbrs': approved_mbrs,
        'products': products,
        'ebrs': ebrs,
    }
    return render(request, 'users/technologist_dashboard.html', context)


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
                        mbr.approval_date = datetime.now().date()
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
                        comment=f"Создан MBR для {product.product_code}"
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
                comment=f"Утверждён MBR {mbr.product.product_code} v{mbr.version}"
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