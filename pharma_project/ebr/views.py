from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import EBR, EBRStatus, BatchOperation, EBRNominalParameter, EBRActualParameter
from mbr.models import MBR, Parameter, Document, DocumentType
import datetime
import json


def ebr_list(request):
    if 'user_id' not in request.session:
        return redirect('login')

    ebrs = EBR.objects.all().select_related('status', 'mbr', 'operator').order_by('-start_date')
    approved_mbrs = []
    if request.session.get('user_role') == 'технолог':
        from mbr.models import MBR
        from django.db.models import Max
        latest_mbr_ids = MBR.objects.filter(
            status__status_name='Утверждён'
        ).values('product_id').annotate(
            max_doc_id=Max('document_id')
        ).values_list('max_doc_id', flat=True)
        approved_mbrs = MBR.objects.filter(
            document_id__in=latest_mbr_ids
        ).select_related('product', 'status', 'signed_by')

    context = {
        'user': request.current_user,
        'ebrs': ebrs,
        'approved_mbrs': approved_mbrs,
    }
    return render(request, 'ebr/ebr_list.html', context)


def ebr_create(request, mbr_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if 'user_id' not in request.session or request.session.get('user_role') != 'технолог':
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Не авторизован'}, status=401)
        return redirect('users:login')

    mbr = get_object_or_404(MBR, document_id=mbr_id)

    if request.method == 'POST':
        # Генерация номера партии по формату B-<Код продукта>-<Год>-<Номер партии>
        now = timezone.now()
        product_code = mbr.product.product_code
        batch_count = EBR.objects.filter(
            batch_number__startswith=f"B-{product_code}-{now.year}-"
        ).count() + 1
        batch_number = f"B-{product_code}-{now.year}-{batch_count:03d}"

        # Создаём документ
        doc_type, _ = DocumentType.objects.get_or_create(type_name='EBR')
        doc = Document.objects.create(type=doc_type)

        # Создаём EBR со статусом «В ожидании» (оператор НЕ назначен)
        waiting_status, _ = EBRStatus.objects.get_or_create(status_name='В ожидании')
        ebr = EBR.objects.create(
            document=doc,
            batch_number=batch_number,
            status=waiting_status,
            mbr=mbr,
            operator=None
        )

        # Копируем параметры из MBRParameter
        from mbr.models import MBRParameter
        mbr_params = MBRParameter.objects.filter(mbr=mbr).select_related('parameter')
        for mbr_param in mbr_params:
            nominal = float(mbr_param.value)
            tol_percent = float(mbr_param.tolerance)
            crit_percent = float(mbr_param.critical_deviation)

            # Создаём номинальный параметр (абсолютные значения)
            EBRNominalParameter.objects.create(
                ebr=ebr,
                parameter=mbr_param.parameter,
                nominal_value=mbr_param.value,
                tolerance_value=round(nominal * (tol_percent / 100), 2),
                critical_value=round(nominal * (crit_percent / 100), 2),
            )

            # Создаём фактический параметр (пустой, будет заполнен позже)
            EBRActualParameter.objects.create(
                ebr=ebr,
                parameter=mbr_param.parameter,
                actual_value=None,
                max_value=None,
                source=None,
            )

        # Создаём 2 операции оператора
        BatchOperation.objects.create(
            ebr=ebr,
            operation_name='Выбор сырья',
            status='pending'
        )
        BatchOperation.objects.create(
            ebr=ebr,
            operation_name='Работа пресса',
            status='pending'
        )

        messages.success(request, f'Партия {batch_number} создана и ожидает оператора')

        # Логируем создание EBR
        from audit.models import Action, AuditLog
        try:
            action, _ = Action.objects.get_or_create(action_name='Создание EBR')
            AuditLog.objects.create(
                user=request.current_user,
                action=action,
                document=doc,
                comment=f"Создана партия {batch_number} ({mbr.product.product_name}) по MBR {mbr.product.product_code} {mbr.version}. "
                        f"Создал: {request.current_user.last_name} {request.current_user.first_name}"
            )
        except Exception:
            pass

        # Если AJAX — возвращаем JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'batch_number': batch_number,
                'ebr_id': ebr.document_id
            })

        return redirect('ebr:ebr_detail', pk=ebr.document_id)

    # Если GET — перенаправляем на список
    return redirect('ebr:ebr_list')


def ebr_detail(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')

    ebr = get_object_or_404(EBR, document_id=pk)
    operations = ebr.operations.all()
    nominal_params = EBRNominalParameter.objects.filter(ebr=ebr).select_related('parameter')
    actual_params = EBRActualParameter.objects.filter(ebr=ebr).select_related('parameter')

    # Сопоставляем номинальные и фактические параметры
    params_dict = {}
    for np in nominal_params:
        pid = np.parameter_id
        ap = actual_params.filter(parameter_id=pid).first()
        params_dict[pid] = {
            'nominal': np,
            'actual': ap,
        }

    # Рассчитываем статус для каждого параметра
    parameters_with_status = []
    for pid, data in params_dict.items():
        np = data['nominal']
        ap = data['actual']
        status = 'pending'

        if ap and ap.actual_value is not None:
            diff = abs(float(ap.actual_value) - float(np.nominal_value))
            if diff > float(np.critical_value):
                status = 'critical'
            elif diff > float(np.tolerance_value):
                status = 'deviation'
            elif diff > float(np.tolerance_value) * 0.9:
                status = 'warning'
            else:
                status = 'ok'

        parameters_with_status.append({
            'nominal': np,
            'actual': ap,
            'status': status,
        })

    # Список сырья из MBR
    raw_materials = ebr.mbr.raw_materials.all() if ebr.mbr else []

    # QC результаты (если есть)
    from quality.models import QCResult
    qc_result = QCResult.objects.filter(task__ebr=ebr).first()

    # Электронная подпись (если есть)
    from audit.models import ElectronicSignature
    e_signature = ElectronicSignature.objects.filter(document=ebr.document).first()

    context = {
        'user': request.current_user,
        'ebr': ebr,
        'operations': operations,
        'parameters': parameters_with_status,
        'raw_materials': raw_materials,
        'qc_result': qc_result,
        'e_signature': e_signature,
    }
    return render(request, 'ebr/ebr_detail.html', context)


def ebr_start(request, pk):
    """Оператор начинает производство — выбирает партию из «В ожидании»."""
    is_ajax_req = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if 'user_id' not in request.session or request.session.get('user_role') != 'оператор':
        if is_ajax_req:
            return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        return redirect('users:login')

    ebr = get_object_or_404(EBR, document_id=pk)

    # Меняем статус с «В ожидании» на «В работе»
    in_work_status, _ = EBRStatus.objects.get_or_create(status_name='В работе')
    ebr.status = in_work_status
    ebr.operator = request.current_user
    ebr.save(update_fields=['status', 'operator'])

    # Первая операция → in_progress
    first_op = ebr.operations.filter(operation_name='Выбор сырья').first()
    if first_op:
        first_op.status = 'in_progress'
        first_op.started_at = timezone.now()
        first_op.save(update_fields=['status', 'started_at'])

    messages.success(request, f'Партия {ebr.batch_number} взята в производство')

    if is_ajax_req:
        return JsonResponse({'success': True, 'message': 'Производство начато'})

    return redirect('users:operator_dashboard')


def complete_operation(request, pk):
    """Оператор подтверждает завершение операции."""
    is_ajax_req = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if 'user_id' not in request.session:
        if is_ajax_req:
            return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        return redirect('users:login')

    operation = get_object_or_404(BatchOperation, id=pk)
    ebr = operation.ebr

    # Проверка: если EBR заблокирована, нельзя подтверждать
    if ebr.status.status_name == 'Заблокирована':
        messages.error(request, 'Партия заблокирована. Операции недоступны.')
        if is_ajax_req:
            return JsonResponse({'success': False, 'error': 'Партия заблокирована'})
        return redirect('users:operator_dashboard')

    # Проверка последовательности: все предыдущие операции должны быть completed
    ops = list(ebr.operations.order_by('id'))
    op_index = ops.index(operation)
    for i in range(op_index):
        if ops[i].status != 'completed':
            messages.error(request, f'Сначала завершите операцию: {ops[i].operation_name}')
            if is_ajax_req:
                return JsonResponse({'success': False, 'error': f'Сначала завершите: {ops[i].operation_name}'})
            return redirect('users:operator_dashboard')

    operation.status = 'completed'
    operation.completed_at = timezone.now()
    operation.save(update_fields=['status', 'completed_at'])

    next_op_name = None
    # Если это была не последняя операция — запускаем следующую
    if op_index + 1 < len(ops):
        next_op = ops[op_index + 1]
        next_op.status = 'in_progress'
        next_op.started_at = timezone.now()
        next_op.save(update_fields=['status', 'started_at'])
        next_op_name = next_op.operation_name

    messages.success(request, f'Операция {operation.operation_name} завершена')
    if next_op_name:
        messages.success(request, f'Начата операция: {next_op_name}')

    if is_ajax_req:
        return JsonResponse({'success': True, 'next_operation': next_op_name})

    return redirect('users:operator_dashboard')


def ebr_add_data(request, pk):
    """Ручной ввод фактических параметров (сотрудник ОКК — время распадаемости)."""
    if 'user_id' not in request.session:
        return redirect('login')

    ebr = get_object_or_404(EBR, document_id=pk)

    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('param_'):
                param_id = key.replace('param_', '')
                try:
                    ebr_param = EBRActualParameter.objects.get(
                        ebr=ebr,
                        parameter_id=param_id
                    )
                    new_value = float(value.replace(',', '.') if value else 0)
                    ebr_param.actual_value = new_value
                    ebr_param.source = 'manual'

                    # max_value = actual_value (однократный ручной ввод)
                    if ebr_param.max_value is None or new_value > float(ebr_param.max_value):
                        ebr_param.max_value = new_value

                    ebr_param.save(update_fields=['actual_value', 'max_value', 'source'])

                    # Проверка отклонений и пересчёт статуса EBR
                    _check_and_update_deviation(ebr, ebr_param)
                except EBRActualParameter.DoesNotExist:
                    continue

        messages.success(request, 'Данные сохранены')
        return redirect('ebr:ebr_detail', pk=pk)

    return redirect('ebr:ebr_detail', pk=pk)


def _check_and_update_deviation(ebr, ebr_param):
    """Проверить отклонение одного параметра и обновить статус EBR."""
    from quality.models import Deviation

    try:
        nominal = EBRNominalParameter.objects.get(ebr=ebr, parameter=ebr_param.parameter)
    except EBRNominalParameter.DoesNotExist:
        return

    if ebr_param.actual_value is None or float(nominal.nominal_value) == 0:
        return

    diff = abs(float(ebr_param.actual_value) - float(nominal.nominal_value))
    tol = float(nominal.tolerance_value)
    crit = float(nominal.critical_value)

    if crit > 0 and diff > crit:
        # Критическое отклонение
        Deviation.objects.create(
            ebr=ebr,
            deviation_type='critical',
            parameter_name=nominal.parameter.parameter_name,
            expected_value=nominal.nominal_value,
            actual_value=ebr_param.actual_value,
            tolerance=nominal.tolerance_value,
            description=f"Критическое отклонение: {diff:.1f} > {crit:.1f}"
        )
        # max_value = NULL (сигнал, что было критическое)
        ebr_param.max_value = None
        ebr_param.save(update_fields=['max_value'])
        # Блокируем EBR
        ebr.recalculate_status()
    elif tol > 0 and diff > tol:
        Deviation.objects.create(
            ebr=ebr,
            deviation_type='deviation',
            parameter_name=nominal.parameter.parameter_name,
            expected_value=nominal.nominal_value,
            actual_value=ebr_param.actual_value,
            tolerance=nominal.tolerance_value,
            description=f"Отклонение: {diff:.1f} > {tol:.1f}"
        )


def ebr_start_pressing(request, pk):
    """Оператор запускает пресс с заданным временем (сек)."""
    if 'user_id' not in request.session or request.session.get('user_role') != 'оператор':
        return JsonResponse({'error': 'Not authorized'}, status=403)

    ebr = get_object_or_404(EBR, document_id=pk)

    if ebr.status.status_name != 'В работе':
        return JsonResponse({'error': 'EBR is not in work'}, status=400)

    pressing_time = int(request.POST.get('pressing_time', 30))
    if pressing_time < 30 or pressing_time > 300:
        return JsonResponse({'error': 'pressing_time must be 30-300'}, status=400)

    # Подтверждаем операцию «Работа пресса»
    press_op = ebr.operations.filter(operation_name='Работа пресса').first()
    if press_op and press_op.status == 'in_progress':
        press_op.status = 'completed'
        press_op.completed_at = timezone.now()
        press_op.save(update_fields=['status', 'completed_at'])

    # Записываем время начала и длительность прессования
    now = timezone.now()
    ebr.pressing_start_time = now
    ebr.pressing_duration = pressing_time
    ebr.save(update_fields=['pressing_start_time', 'pressing_duration'])

    # Запускаем симулятор
    from equipment.simulator import simulator
    simulator.start_production(pk, pressing_time)

    messages.success(request, f'Пресс запущен на {pressing_time} секунд')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'pressing_time': pressing_time,
            'pressing_start': now.isoformat(),
        })

    return redirect('users:operator_dashboard')


def ebr_sign(request, pk):
    """Начальник ОКК подписывает EBR электронной подписью."""
    if 'user_id' not in request.session or request.session.get('user_role') != 'начальник ОКК':
        return redirect('login')

    ebr = get_object_or_404(EBR, document_id=pk)

    if request.method == 'POST':
        # Проверка: все параметры заполнены?
        actual_count = EBRActualParameter.objects.filter(ebr=ebr, actual_value__isnull=False).count()
        total_count = EBRActualParameter.objects.filter(ebr=ebr).count()

        if actual_count < total_count:
            messages.error(request, f'Не все параметры заполнены ({actual_count}/{total_count})')
            return redirect('ebr:ebr_detail', pk=pk)

        if ebr.status.status_name == 'Заблокирована':
            messages.error(request, 'Нельзя подписать заблокированную партию')
            return redirect('ebr:ebr_detail', pk=pk)

        # Подписываем
        ebr.signed_by = request.current_user
        ebr.completion_date = timezone.now()
        completed_status, _ = EBRStatus.objects.get_or_create(status_name='Завершена')
        ebr.status = completed_status
        ebr.save(update_fields=['signed_by', 'completion_date', 'status'])

        # Создаём электронную подпись
        from audit.models import ElectronicSignature
        import hashlib
        signature_data = {
            'user_id': request.current_user.user_id,
            'document_id': ebr.document_id,
            'timestamp': str(timezone.now()),
            'batch_number': ebr.batch_number,
        }
        signature_hash = hashlib.sha256(
            json.dumps(signature_data, sort_keys=True).encode()
        ).hexdigest()
        ElectronicSignature.objects.create(
            user=request.current_user,
            document=ebr.document,
            signature_hash=signature_hash,
            comment=f"Подписание партии {ebr.batch_number}"
        )

        # Логируем
        from audit.models import Action, AuditLog
        try:
            action = Action.objects.get(action_name='Подписание EBR')
        except Action.DoesNotExist:
            action = Action.objects.create(action_name='Подписание EBR')

        AuditLog.objects.create(
            user=request.current_user,
            action=action,
            document=ebr.document,
            comment=f"Партия {ebr.batch_number} ({ebr.mbr.product.product_name}) подписана и завершена. "
                    f"Подписал: {request.current_user.last_name} {request.current_user.first_name}"
        )

        messages.success(request, f'Партия {ebr.batch_number} подписана и завершена')
        return redirect('ebr:ebr_detail', pk=pk)

    return redirect('ebr:ebr_detail', pk=pk)