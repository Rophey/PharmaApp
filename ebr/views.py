from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import EBR, EBRStatus
from mbr.models import MBR
from quality.models import Alert, QualityTask
from audit.utils import log_action


def is_technologist(user):
    return user.role == 'technologist'


def is_qc_head(user):
    return user.role == 'qc_head'


@login_required
@user_passes_test(is_technologist)
def launch_batch(request, mbr_id):
    """Запуск новой партии на основе MBR"""
    mbr = get_object_or_404(MBR, id=mbr_id, status__status_name='approved')

    with transaction.atomic():
        # Генерация номера партии (по правилам из системных настроек)
        from accounts.models import SystemSettings
        settings = SystemSettings.objects.first()
        batch_number = generate_batch_number(settings.batch_rule if settings else 'B-YYYY-XXX')

        # Создание EBR
        ebr = EBR.objects.create(
            mbr=mbr,
            batch_number=batch_number,
            status=EBRStatus.objects.get(status_name='in_progress'),
            start_date=timezone.now()
        )

        # Копирование параметров из MBR
        for param in mbr.parameters.all():
            ebr.actual_parameters.add(param)

        # Создание задания для ОКК
        QualityTask.objects.create(
            ebr=ebr,
            task_type='sampling',
            assigned_to=None,  # Назначается автоматически
            deadline=timezone.now() + timezone.timedelta(hours=24)
        )

        log_action(
            user=request.user,
            action_name='Запуск партии',
            document=ebr,
            comment=f'Запущена партия {batch_number} на основе MBR {mbr.version}'
        )

    messages.success(request, f'Партия {batch_number} запущена в производство')
    return redirect('technologist_dashboard')


@login_required
def ebr_detail(request, ebr_id):
    """Просмотр EBR"""
    ebr = get_object_or_404(EBR.objects.select_related('mbr', 'status'), id=ebr_id)
    alerts = ebr.alerts.all()
    return render(request, 'ebr/ebr_detail.html', {'ebr': ebr, 'alerts': alerts})


@login_required
@user_passes_test(is_qc_head)
def ebr_sign(request, ebr_id):
    """Подписание EBR электронной подписью"""
    ebr = get_object_or_404(EBR, id=ebr_id, status__status_name='pending_review')

    if request.method == 'POST':
        with transaction.atomic():
            ebr.status = EBRStatus.objects.get(status_name='completed')
            ebr.completion_date = timezone.now()
            ebr.signed_by = request.user
            ebr.save()

            log_action(
                user=request.user,
                action_name='Подписание EBR',
                document=ebr,
                comment='EBR подписан начальником ОКК'
            )

        messages.success(request, f'EBR {ebr.batch_number} подписан')
        return redirect('qc_head_dashboard')

    return redirect('qc_head_dashboard')


@login_required
@user_passes_test(is_qc_head)
def ebr_block(request, ebr_id):
    """Блокировка партии"""
    ebr = get_object_or_404(EBR, id=ebr_id)

    if request.method == 'POST':
        with transaction.atomic():
            ebr.status = EBRStatus.objects.get(status_name='blocked')
            ebr.save()

            log_action(
                user=request.user,
                action_name='Блокировка партии',
                document=ebr,
                comment='Партия заблокирована начальником ОКК'
            )

        messages.warning(request, f'Партия {ebr.batch_number} заблокирована')
        return redirect('qc_head_dashboard')

    return redirect('qc_head_dashboard')


def generate_batch_number(rule):
    """Генерация номера партии по правилу"""
    from datetime import datetime
    from ebr.models import EBR

    last_ebr = EBR.objects.all().order_by('-id').first()
    next_num = int(last_ebr.batch_number.split('-')[-1]) + 1 if last_ebr else 1

    if rule == 'B-YYYY-XXX':
        return f"B-{datetime.now().year}-{next_num:03d}"
    elif rule == 'PRODUCT-YYMMDD-XXX':
        # Нужен код продукта из MBR
        return f"ASP-{datetime.now().strftime('%y%m%d')}-{next_num:03d}"
    else:
        return f"{datetime.now().strftime('%y%m%d')}-{next_num:03d}-ASP"