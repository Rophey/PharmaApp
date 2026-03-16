from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
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

    context = {
        'user': request.current_user,
        'task': task,
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
        task.completed_at = datetime.datetime.now()
        task.save()

        # Обновляем EBR
        ebr = task.ebr
        ebr.inspection_notes = f"Визуальный контроль: {visual}\nЛабораторные: {lab}"
        ebr.save()

        messages.success(request, 'Результаты контроля сохранены')

        # Логируем
        from audit.models import Action, AuditLog
        action = Action.objects.get(action_name='Ввод данных контроля')
        AuditLog.objects.create(
            user=request.current_user,
            action=action,
            document=ebr.document,
            comment=f"Внесены результаты ОКК по заданию #{task.id}"
        )

        return redirect('quality:qc_tasks')

    return redirect('quality:qc_task_detail', pk=pk)


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
        deviation.resolved_at = datetime.datetime.now()
        deviation.save()

        # Если действие - разблокировать
        if action == 'accept' or action == 'rework':
            from ebr.models import EBRStatus
            ebr = deviation.ebr
            ebr.status = EBRStatus.objects.get(status_name='В работе')
            ebr.save()

        # Логируем
        from audit.models import Action, AuditLog
        action_obj = Action.objects.get(
            action_name='Блокировка партии' if action == 'block' else 'Разблокировка партии')
        AuditLog.objects.create(
            user=request.current_user,
            action=action_obj,
            document=deviation.ebr.document,
            comment=f"Решение по отклонению: {action} - {comment}"
        )

        messages.success(request, 'Решение по отклонению принято')
        return redirect('quality:deviation_list')

    return redirect('quality:deviation_list')