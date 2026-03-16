from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import EBR, EBRStatus, BatchOperation, EBRParameter
from mbr.models import MBR, Parameter, Document, DocumentType


def ebr_list(request):
    if 'user_id' not in request.session:
        return redirect('login')

    ebrs = EBR.objects.all().select_related('status', 'mbr', 'operator')
    context = {
        'user': request.current_user,
        'ebrs': ebrs,
    }
    return render(request, 'ebr/ebr_list.html', context)


def ebr_create(request, mbr_id):
    if 'user_id' not in request.session or request.session.get('user_role') != 'технолог':
        return redirect('login')

    mbr = get_object_or_404(MBR, document_id=mbr_id)

    if request.method == 'POST':
        # Генерация номера партии (упрощённо)
        import datetime
        now = datetime.datetime.now()
        batch_number = f"B-{now.year}-{now.strftime('%m%d')}-{EBR.objects.count() + 1:03d}"

        # Создаём документ
        doc_type = DocumentType.objects.get(type_name='EBR')
        doc = Document.objects.create(type=doc_type)

        # Создаём EBR
        status = EBRStatus.objects.get(status_name='В работе')
        ebr = EBR.objects.create(
            document=doc,
            batch_number=batch_number,
            status=status,
            mbr=mbr,
            operator=request.current_user
        )

        # Копируем параметры из MBR
        for param in mbr.parameters.all():
            EBRParameter.objects.create(
                ebr=ebr,
                parameter=param
            )

        messages.success(request, f'Партия {batch_number} создана')
        return redirect('ebr:ebr_detail', pk=ebr.document_id)

    return redirect('ebr:ebr_list')


def ebr_detail(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')

    ebr = get_object_or_404(EBR, document_id=pk)
    operations = ebr.operations.all()
    parameters = EBRParameter.objects.filter(ebr=ebr).select_related('parameter')

    context = {
        'user': request.current_user,
        'ebr': ebr,
        'operations': operations,
        'parameters': parameters,
    }
    return render(request, 'ebr/ebr_detail.html', context)


def ebr_start(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')

    ebr = get_object_or_404(EBR, document_id=pk)

    # Создаём первую операцию
    BatchOperation.objects.create(
        ebr=ebr,
        operation_name='Подготовка сырья',
        status='in_progress'
    )

    messages.success(request, 'Производство партии начато')
    return redirect('ebr:ebr_detail', pk=pk)


def complete_operation(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')

    operation = get_object_or_404(BatchOperation, id=pk)
    operation.status = 'completed'
    operation.completed_at = datetime.datetime.now()
    operation.save()

    messages.success(request, f'Операция {operation.operation_name} завершена')
    return redirect('ebr:ebr_detail', pk=operation.ebr.document_id)


def ebr_add_data(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')

    ebr = get_object_or_404(EBR, document_id=pk)

    if request.method == 'POST':
        # Обновляем фактические значения параметров
        for key, value in request.POST.items():
            if key.startswith('param_'):
                param_id = key.replace('param_', '')
                ebr_param = EBRParameter.objects.get(
                    ebr=ebr,
                    parameter_id=param_id
                )
                ebr_param.actual_value = value
                ebr_param.save()

        # Проверка на отклонения
        from quality.models import Deviation
        for ebr_param in EBRParameter.objects.filter(ebr=ebr):
            param = ebr_param.parameter
            if ebr_param.actual_value:
                diff_percent = abs((ebr_param.actual_value - param.value) / param.value * 100)

                if diff_percent > param.critical_deviation:
                    # Критическое отклонение
                    Deviation.objects.create(
                        ebr=ebr,
                        deviation_type='critical',
                        parameter_name=param.parameter_name,
                        expected_value=param.value,
                        actual_value=ebr_param.actual_value,
                        tolerance=param.tolerance,
                        description=f"Критическое отклонение: {diff_percent:.1f}%"
                    )
                    ebr.status = EBRStatus.objects.get(status_name='Заблокирована')
                    ebr.save()
                elif diff_percent > param.tolerance:
                    # Отклонение
                    Deviation.objects.create(
                        ebr=ebr,
                        deviation_type='deviation',
                        parameter_name=param.parameter_name,
                        expected_value=param.value,
                        actual_value=ebr_param.actual_value,
                        tolerance=param.tolerance,
                        description=f"Отклонение: {diff_percent:.1f}%"
                    )

        messages.success(request, 'Данные сохранены')
        return redirect('ebr:ebr_detail', pk=pk)

    return redirect('ebr:ebr_detail', pk=pk)