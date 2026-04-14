from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import MBR, Product, RawMaterial, Parameter, Document, DocumentType


def mbr_list(request):
    if 'user_id' not in request.session:
        return redirect('login')

    mbrs = MBR.objects.all().select_related('product', 'status', 'signed_by')
    context = {
        'user': request.current_user,
        'mbrs': mbrs,
    }
    return render(request, 'mbr/mbr_list.html', context)


def mbr_create(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('login')

    if request.method == 'POST':
        import datetime
        from audit.models import Action, AuditLog
        from .models import MBRStatus, MBRParameter, MBRRawMaterial, Document

        product_name = request.POST.get('product_name', '').strip()
        product_code = request.POST.get('product_code', '').strip()
        operations = request.POST.get('operations', '').strip()
        comments = request.POST.get('comments', '').strip()
        raw_material_ids = request.POST.getlist('raw_materials')

        # Создаём или получаем продукт
        product, _ = Product.objects.get_or_create(
            product_code=product_code,
            defaults={'product_name': product_name}
        )

        # Создаём документ
        doc_type = DocumentType.objects.get(type_name='MBR')
        doc = Document.objects.create(type=doc_type)

        # Получаем статус "Черновик"
        draft_status = MBRStatus.objects.get(status_name='Черновик')

        # Создаём MBR
        mbr = MBR.objects.create(
            document=doc,
            product=product,
            version='v1',
            status=draft_status,
            operations=operations,
            comments=comments,
        )

        # Привязываем сырьё
        for rm_id in raw_material_ids:
            if rm_id:
                MBRRawMaterial.objects.create(mbr=mbr, raw_material_id=int(rm_id))

        # Сохраняем параметры (value, tolerance, critical_deviation — собственные для этого MBR)
        from decimal import Decimal, InvalidOperation
        parameters = Parameter.objects.all()
        for param in parameters:
            value_str = request.POST.get(f'param_value_{param.id}', '0').replace(',', '.')
            tolerance_str = request.POST.get(f'param_tolerance_{param.id}', '0').replace(',', '.')
            critical_str = request.POST.get(f'param_critical_{param.id}', '0').replace(',', '.')

            try:
                value = Decimal(value_str) if value_str else Decimal('0')
                tolerance = Decimal(tolerance_str) if tolerance_str else Decimal('0')
                critical = Decimal(critical_str) if critical_str else Decimal('0')
            except InvalidOperation:
                value = Decimal('0')
                tolerance = Decimal('0')
                critical = Decimal('0')

            MBRParameter.objects.create(
                mbr=mbr,
                parameter=param,
                value=value,
                tolerance=tolerance,
                critical_deviation=critical,
            )

        # Лог в аудит
        action = Action.objects.get(action_name='Создание MBR')
        AuditLog.objects.create(
            user=request.current_user,
            action=action,
            document=doc,
            comment=f"Создан MBR {product_code} v1"
        )

        messages.success(request, 'MBR создан')
        return redirect('mbr:mbr_detail', pk=mbr.document_id)

    products = Product.objects.all()
    raw_materials = RawMaterial.objects.all()
    parameters = Parameter.objects.all()

    context = {
        'user': request.current_user,
        'products': products,
        'raw_materials': raw_materials,
        'parameters': parameters,
    }
    return render(request, 'mbr/mbr_form.html', context)


def mbr_detail(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')

    mbr = get_object_or_404(MBR, document_id=pk)
    context = {
        'user': request.current_user,
        'mbr': mbr,
    }
    return render(request, 'mbr/mbr_detail.html', context)


def mbr_edit(request, pk):
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('login')

    mbr = get_object_or_404(MBR, document_id=pk)
    if mbr.status.status_name == 'Утверждён':
        messages.error(request, 'Нельзя редактировать утверждённый MBR')
        return redirect('mbr:mbr_detail', pk=pk)

    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        from audit.models import Action, AuditLog

        product_name = request.POST.get('product_name', '').strip()
        product_code = request.POST.get('product_code', '').strip()
        operations = request.POST.get('operations', '').strip()
        comments = request.POST.get('comments', '').strip()
        raw_material_ids = request.POST.getlist('raw_materials')

        # Обновляем продукт
        mbr.product.product_name = product_name
        mbr.product.product_code = product_code
        mbr.product.save()

        # Обновляем поля MBR
        mbr.operations = operations
        mbr.comments = comments
        mbr.save()

        # Обновляем сырьё
        MBRRawMaterial.objects.filter(mbr=mbr).delete()
        for rm_id in raw_material_ids:
            if rm_id:
                MBRRawMaterial.objects.create(mbr=mbr, raw_material_id=int(rm_id))

        # Обновляем параметры
        parameters = Parameter.objects.all()
        for param in parameters:
            value_str = request.POST.get(f'param_value_{param.id}', '0').replace(',', '.')
            tolerance_str = request.POST.get(f'param_tolerance_{param.id}', '0').replace(',', '.')
            critical_str = request.POST.get(f'param_critical_{param.id}', '0').replace(',', '.')

            try:
                value = Decimal(value_str) if value_str else Decimal('0')
                tolerance = Decimal(tolerance_str) if tolerance_str else Decimal('0')
                critical = Decimal(critical_str) if critical_str else Decimal('0')
            except InvalidOperation:
                value = Decimal('0')
                tolerance = Decimal('0')
                critical = Decimal('0')

            MBRParameter.objects.update_or_create(
                mbr=mbr,
                parameter=param,
                defaults={
                    'value': value,
                    'tolerance': tolerance,
                    'critical_deviation': critical,
                }
            )

        # Лог в аудит
        action = Action.objects.get(action_name='Редактирование MBR')
        AuditLog.objects.create(
            user=request.current_user,
            action=action,
            document=mbr.document,
            comment=f"Редактирован MBR {product_code} {mbr.version}"
        )

        messages.success(request, 'MBR обновлён')
        return redirect('mbr:mbr_detail', pk=pk)

    raw_materials = RawMaterial.objects.all()
    parameters = Parameter.objects.all()

    context = {
        'user': request.current_user,
        'mbr': mbr,
        'raw_materials': raw_materials,
        'parameters': parameters,
    }
    return render(request, 'mbr/mbr_form.html', context)


def mbr_approve(request, pk):
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('login')

    mbr = get_object_or_404(MBR, document_id=pk)
    if request.method == 'POST':
        from audit.models import Action, AuditLog
        import datetime

        # Получаем статус "Утверждён" динамически
        try:
            approved_status = MBRStatus.objects.get(status_name='Утверждён')
            mbr.status = approved_status
            mbr.approval_date = datetime.date.today()
            mbr.signed_by = request.current_user
            mbr.save()

            # Логируем
            action = Action.objects.get(action_name='Утверждение MBR')
            AuditLog.objects.create(
                user=request.current_user,
                action=action,
                document=mbr.document,
                comment=f"Утверждён MBR {mbr.product.product_code} v{mbr.version}"
            )

            messages.success(request, 'MBR утверждён')
        except MBRStatus.DoesNotExist:
            messages.error(request, 'Ошибка: статус "Утверждён" не найден в базе данных')
        
    return redirect('mbr:mbr_detail', pk=pk)


def mbr_new_version(request, pk):
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('login')

    old_mbr = get_object_or_404(MBR, document_id=pk)

    # Создаём новый документ
    doc_type, _ = DocumentType.objects.get_or_create(type_name='MBR')
    new_doc = Document.objects.create(type=doc_type)

    # Новая версия
    import re
    match = re.search(r'v(\d+)', old_mbr.version)
    version_num = int(match.group(1)) + 1 if match else 1

    from .models import MBRStatus, MBRParameter
    draft_status = MBRStatus.objects.get(status_name='Черновик')

    new_mbr = MBR.objects.create(
        document=new_doc,
        product=old_mbr.product,
        version=f'v{version_num}',
        status=draft_status,
        operations=old_mbr.operations,
        comments=f"Новая версия на основе {old_mbr.version}"
    )

    # Копируем связи
    for rm in old_mbr.raw_materials.all():
        new_mbr.raw_materials.add(rm)
    
    # Копируем параметры (вместе со значениями из MBRParameter)
    old_params = MBRParameter.objects.filter(mbr=old_mbr)
    for old_param in old_params:
        MBRParameter.objects.create(
            mbr=new_mbr,
            parameter=old_param.parameter,
            value=old_param.value,
            tolerance=old_param.tolerance,
            critical_deviation=old_param.critical_deviation
        )

    messages.success(request, f'Создана новая версия {new_mbr.version}')
    
    # Если AJAX — возвращаем JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        return JsonResponse({
            'success': True,
            'message': f'Создана версия {new_mbr.version}',
            'new_mbr_id': new_mbr.document_id
        })
    
    return redirect('mbr:mbr_edit', pk=new_mbr.document_id)


def mbr_delete(request, pk):
    """Удаление MBR (только черновики)"""
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('login')

    mbr = get_object_or_404(MBR, document_id=pk)
    
    # Можно удалять только черновики
    if mbr.status.status_name != 'Черновик':
        messages.error(request, 'Можно удалять только черновики')
        return redirect('mbr:mbr_list')
    
    if request.method == 'POST':
        product_name = mbr.product.product_code
        # Удаляем параметры
        from .models import MBRParameter
        MBRParameter.objects.filter(mbr=mbr).delete()
        # Удаляем MBR
        mbr.delete()
        messages.success(request, f'Черновик MBR {product_name} удалён')
        
        # Если AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': True, 'message': 'MBR удалён'})
    
    return redirect('mbr:mbr_list')