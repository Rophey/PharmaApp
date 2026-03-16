from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from .models import MBR, Product, Parameter, RawMaterial, MBRStatus
from .forms import MBRForm, MBRApproveForm
from audit.utils import log_action


def is_chief_technologist(user):
    return user.role == 'chief_technologist'


@login_required
@user_passes_test(is_chief_technologist)
def mbr_list(request):
    """Список всех MBR"""
    mbrs = MBR.objects.select_related('product', 'status').all().order_by('-created_at')
    return render(request, 'accounts/chief_technologist_dashboard.html', {'mbrs': mbrs})


@login_required
@user_passes_test(is_chief_technologist)
def mbr_create(request):
    """Создание нового MBR"""
    if request.method == 'POST':
        form = MBRForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                mbr = form.save(commit=False)
                mbr.status = MBRStatus.objects.get(status_name='draft')

                # Проверка на утверждение
                if 'approve' in request.POST:
                    # Проверка полноты данных (ТЗ 4.2.2.1.1 п.2.l)
                    if not form.is_complete():
                        messages.error(request, 'Внесённая информация не является полной')
                        return render(request, 'accounts/chief_technologist_dashboard.html', {'form': form})

                    mbr.status = MBRStatus.objects.get(status_name='approved')
                    mbr.approval_date = timezone.now().date()
                    mbr.signed_by = request.user

                mbr.save()
                form.save_m2m()

                # Аудит (ТЗ 4.2.6.1.2)
                log_action(
                    user=request.user,
                    action_name='Создание MBR' if mbr.status.status_name == 'draft' else 'Утверждение MBR',
                    document=mbr,
                    comment=form.cleaned_data.get('comments', '')
                )

                messages.success(request, f'MBR {mbr.product.product_code} успешно создан')
                return redirect('mbr_list')
        else:
            messages.error(request, 'Ошибка валидации формы')
    else:
        form = MBRForm()

    return render(request, 'accounts/chief_technologist_dashboard.html', {'form': form})


@login_required
@user_passes_test(is_chief_technologist)
def mbr_detail(request, mbr_id):
    """Просмотр MBR"""
    mbr = get_object_or_404(MBR.objects.select_related('product', 'status'), id=mbr_id)
    return render(request, 'mbr/mbr_detail.html', {'mbr': mbr})


@login_required
@user_passes_test(is_chief_technologist)
def mbr_edit(request, mbr_id):
    """Редактирование черновика MBR"""
    mbr = get_object_or_404(MBR, id=mbr_id, status__status_name='draft')

    if request.method == 'POST':
        form = MBRForm(request.POST, request.FILES, instance=mbr)
        if form.is_valid():
            mbr = form.save(commit=False)
            mbr.updated_at = timezone.now()
            mbr.save()
            form.save_m2m()

            log_action(
                user=request.user,
                action_name='Редактирование MBR',
                document=mbr,
                comment=form.cleaned_data.get('comments', '')
            )

            messages.success(request, 'MBR обновлён')
            return redirect('mbr_list')
    else:
        form = MBRForm(instance=mbr)

    return render(request, 'mbr/mbr_edit.html', {'form': form, 'mbr': mbr})


@login_required
@user_passes_test(is_chief_technologist)
def mbr_approve(request, mbr_id):
    """Утверждение MBR"""
    mbr = get_object_or_404(MBR, id=mbr_id, status__status_name='draft')

    if request.method == 'POST':
        with transaction.atomic():
            mbr.status = MBRStatus.objects.get(status_name='approved')
            mbr.approval_date = timezone.now().date()
            mbr.signed_by = request.user
            mbr.save()

            log_action(
                user=request.user,
                action_name='Утверждение MBR',
                document=mbr,
                comment='MBR утверждён главным технологом'
            )

        messages.success(request, f'MBR {mbr.product.product_code} утверждён')
        return redirect('mbr_list')

    return redirect('mbr_list')


@login_required
@user_passes_test(is_chief_technologist)
def mbr_new_version(request, mbr_id):
    """Создание новой версии MBR на основе утверждённой"""
    old_mbr = get_object_or_404(MBR, id=mbr_id, status__status_name='approved')

    with transaction.atomic():
        # Копирование данных
        new_mbr = MBR.objects.create(
            product=old_mbr.product,
            version=f'v{int(old_mbr.version.replace("v", "")) + 1}',
            status=MBRStatus.objects.get(status_name='draft'),
            operations=old_mbr.operations,
            comments=f'Новая версия на основе {old_mbr.version}'
        )

        # Копирование параметров
        for param in old_mbr.parameters.all():
            new_mbr.parameters.add(param)

        # Копирование сырья
        for material in old_mbr.raw_materials.all():
            new_mbr.raw_materials.add(material)

        log_action(
            user=request.user,
            action_name='Создание новой версии MBR',
            document=new_mbr,
            comment=f'Создано на основе {old_mbr.version}'
        )

    messages.success(request, f'Создана новая версия MBR: {new_mbr.version}')
    return redirect('mbr_edit', mbr_id=new_mbr.id)