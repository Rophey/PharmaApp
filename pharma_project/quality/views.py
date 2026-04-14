from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import QCTask, QCResult, Deviation
from ebr.models import EBR
from users.models import User
import datetime


def qc_tasks(request):
    if 'user_id' not in request.session:
        return redirect('login')

    if request.session.get('user_role') == 'сотрудник ОКК':
        tasks = QCTask.objects.filter(
            assigned_to=request.current_user
        ).select_related('ebr', 'created_by').order_by('due_date')
    else:
        tasks = QCTask.objects.all().select_related('ebr', 'assigned_to', 'created_by')

    context = {
        'user': request.current_user,
        'tasks': tasks,
    }
    return render(request, 'quality/task_list.html', context)


def qc_task_detail(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')

    task = get_object_or_404(QCTask, id=pk)

    # Проверка доступа
    if request.session.get('user_role') == 'сотрудник ОКК' and task.assigned_to != request.current_user:
        messages.error(request, 'У вас нет доступа к этому заданию')
        return redirect('quality:qc_tasks')

    # Загружаем параметры EBR
    from ebr.models import EBRNominalParameter, EBRActualParameter
    nominal_params = EBRNominalParameter.objects.filter(ebr=task.ebr).select_related('parameter')
    actual_params = EBRActualParameter.objects.filter(ebr=task.ebr).select_related('parameter')

    parameters = []
    for np in nominal_params:
        ap = actual_params.filter(parameter_id=np.parameter_id).first()
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
        parameters.append({'nominal': np, 'actual': ap, 'status': status})

    context = {
        'user': request.current_user,
        'task': task,
        'parameters': parameters,
    }
    return render(request, 'quality/task_detail.html', context)


def qc_submit_results(request, pk):
    if 'user_id' not in request.session or request.session.get('user_role') != 'сотрудник ОКК':
        return redirect('login')

    task = get_object_or_404(QCTask, id=pk)

    if task.assigned_to != request.current_user:
        messages.error(request, 'У вас нет доступа к этому заданию')
        return redirect('quality:qc_tasks')

    if request.method == 'POST':
        visual = request.POST.get('visual_control')
        lab = request.POST.get('lab_results')
        files = request.FILES.get('qc_files')
        disintegration_time = request.POST.get('disintegration_time', '').strip()

        # Создаём результат
        result = QCResult.objects.create(
            task=task,
            visual_control=visual,
            lab_results=lab,
            files=files,
            submitted_by=request.current_user
        )

        # Обновляем статус задания
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()

        # Обновляем EBR
        ebr = task.ebr
        ebr.inspection_notes = f"Визуальный контроль: {visual}\nЛабораторные: {lab}"
        ebr.save()

        # Записываем время распадаемости если введено отдельно
        if disintegration_time:
            _save_disintegration_time(ebr, disintegration_time)
        else:
            # Пытаемся извлечь из lab_results
            _extract_disintegration_time(ebr, lab)

        messages.success(request, 'Результаты контроля сохранены')

        # Логируем
        from audit.models import Action, AuditLog
        try:
            action, _ = Action.objects.get_or_create(action_name='Ввод данных контроля')
        except Action.DoesNotExist:
            action = Action.objects.create(action_name='Ввод данных контроля')
        AuditLog.objects.create(
            user=request.current_user,
            action=action,
            document=ebr.document,
            comment=f"Внесены результаты ОКК по партии {ebr.batch_number} ({ebr.mbr.product.product_name}). "
                    f"Визуальный контроль: {visual[:50]}... "
                    f"Внёс: {request.current_user.last_name} {request.current_user.first_name}"
        )

        return redirect('quality:qc_tasks')

    return redirect('quality:qc_task_detail', pk=pk)


def _save_disintegration_time(ebr, value_str):
    """Сохранить время распадаемости в EBRActualParameter."""
    from ebr.models import EBRActualParameter, EBRNominalParameter

    try:
        value = float(value_str.replace(',', '.'))
    except ValueError:
        return

    from ebr.models import Parameter
    dis_param = Parameter.objects.filter(parameter_name__icontains='распадаем').first()
    if not dis_param:
        return

    try:
        ap = EBRActualParameter.objects.get(ebr=ebr, parameter=dis_param)
        ap.actual_value = value
        ap.source = 'manual'
        ap.max_value = value
        ap.save(update_fields=['actual_value', 'max_value', 'source'])

        # Проверяем отклонение
        try:
            nominal = EBRNominalParameter.objects.get(ebr=ebr, parameter=dis_param)
        except EBRNominalParameter.DoesNotExist:
            return

        diff = abs(value - float(nominal.nominal_value))
        tol = float(nominal.tolerance_value)
        crit = float(nominal.critical_value)

        if crit > 0 and diff > crit:
            from quality.models import Deviation
            Deviation.objects.create(
                ebr=ebr, deviation_type='critical',
                parameter_name=nominal.parameter.parameter_name,
                expected_value=nominal.nominal_value, actual_value=value,
                tolerance=nominal.tolerance_value,
                description=f"Критическое отклонение: {diff:.1f} > {crit:.1f}"
            )
            ap.max_value = None
            ap.save(update_fields=['max_value'])
            ebr.recalculate_status()
        elif tol > 0 and diff > tol:
            from quality.models import Deviation
            Deviation.objects.create(
                ebr=ebr, deviation_type='deviation',
                parameter_name=nominal.parameter.parameter_name,
                expected_value=nominal.nominal_value, actual_value=value,
                tolerance=nominal.tolerance_value,
                description=f"Отклонение: {diff:.1f} > {tol:.1f}"
            )
    except EBRActualParameter.DoesNotExist:
        pass


def _extract_disintegration_time(ebr, lab_text):
    """Извлечь время распадаемости из текста lab_results и записать в EBRActualParameter."""
    import re
    from ebr.models import EBRActualParameter, EBRNominalParameter
    from quality.models import Deviation

    if not lab_text:
        return

    # Ищем числовое значение — время распадаемости в минутах
    match = re.search(r'(\d+[.,]?\d*)\s*(?:мин|minute)', lab_text, re.IGNORECASE)
    if not match:
        match = re.search(r'(\d+[.,]?\d*)', lab_text)

    if not match:
        return

    try:
        value = float(match.group(1).replace(',', '.'))
    except ValueError:
        return

    # Валидация: >0 и <=4320 (72 часа)
    if value <= 0 or value > 4320:
        return  # Не сохраняем невалидное значение

    # Находим параметр «Время распадаемости»
    from ebr.models import Parameter
    dis_param = Parameter.objects.filter(parameter_name__icontains='распадаем').first()
    if not dis_param:
        return

    # Обновляем EBRActualParameter
    try:
        ap = EBRActualParameter.objects.get(ebr=ebr, parameter=dis_param)
        ap.actual_value = value
        ap.source = 'manual'
        ap.max_value = value
        ap.save(update_fields=['actual_value', 'max_value', 'source'])

        # Проверяем отклонение
        try:
            nominal = EBRNominalParameter.objects.get(ebr=ebr, parameter=dis_param)
        except EBRNominalParameter.DoesNotExist:
            return

        diff = abs(value - float(nominal.nominal_value))
        tol = float(nominal.tolerance_value)
        crit = float(nominal.critical_value)

        if crit > 0 and diff > crit:
            Deviation.objects.create(
                ebr=ebr,
                deviation_type='critical',
                parameter_name=nominal.parameter.parameter_name,
                expected_value=nominal.nominal_value,
                actual_value=value,
                tolerance=nominal.tolerance_value,
                description=f"Критическое отклонение: {diff:.1f} > {crit:.1f}"
            )
            ap.max_value = None
            ap.save(update_fields=['max_value'])
            ebr.recalculate_status()
        elif tol > 0 and diff > tol:
            Deviation.objects.create(
                ebr=ebr,
                deviation_type='deviation',
                parameter_name=nominal.parameter.parameter_name,
                expected_value=nominal.nominal_value,
                actual_value=value,
                tolerance=nominal.tolerance_value,
                description=f"Отклонение: {diff:.1f} > {tol:.1f}"
            )
    except EBRActualParameter.DoesNotExist:
        pass


def deviation_list(request):
    if 'user_id' not in request.session:
        return redirect('login')

    if request.session.get('user_role') == 'начальник ОКК':
        deviations = Deviation.objects.filter(action_taken__isnull=True).select_related('ebr', 'detected_by')
    else:
        deviations = Deviation.objects.all().select_related('ebr', 'detected_by', 'resolved_by')

    context = {
        'user': request.current_user,
        'deviations': deviations,
    }
    return render(request, 'quality/deviation_list.html', context)


def deviation_resolve(request, pk):
    if 'user_id' not in request.session or request.session.get('user_role') != 'начальник ОКК':
        return redirect('login')

    deviation = get_object_or_404(Deviation, id=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment')

        deviation.action_taken = action
        deviation.action_comment = comment
        deviation.resolved_by = request.current_user
        deviation.resolved_at = timezone.now()
        deviation.save()

        # Если действие - разблокировать
        if action == 'accept' or action == 'rework':
            from ebr.models import EBRStatus
            ebr = deviation.ebr
            ebr.status = EBRStatus.objects.get(status_name='В работе')
            ebr.save()

        # Логируем
        from audit.models import Action, AuditLog
        action_name = 'Блокировка партии' if action == 'block' else 'Разблокировка партии'
        action_obj, _ = Action.objects.get_or_create(action_name=action_name)
        ebr = deviation.ebr
        AuditLog.objects.create(
            user=request.current_user,
            action=action_obj,
            document=ebr.document,
            comment=f"Решение по отклонению партии {ebr.batch_number} ({ebr.mbr.product.product_name}): "
                    f"{action} — {comment}. "
                    f"Решил: {request.current_user.last_name} {request.current_user.first_name}"
        )

        messages.success(request, 'Решение по отклонению принято')
        return redirect('quality:deviation_list')

    return redirect('quality:deviation_list')