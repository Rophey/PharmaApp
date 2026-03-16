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
        # Здесь будет логика создания MBR
        messages.success(request, 'MBR создан')
        return redirect('mbr:mbr_list')

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
        messages.success(request, 'MBR обновлён')
        return redirect('mbr:mbr_detail', pk=pk)

    context = {
        'user': request.current_user,
        'mbr': mbr,
    }
    return render(request, 'mbr/mbr_form.html', context)


def mbr_approve(request, pk):
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('login')

    mbr = get_object_or_404(MBR, document_id=pk)
    if request.method == 'POST':
        from audit.models import Action, AuditLog
        import datetime

        mbr.status_id = 2  # Утверждён
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
    return redirect('mbr:mbr_detail', pk=pk)


def mbr_new_version(request, pk):
    if 'user_id' not in request.session or request.session.get('user_role') != 'главный технолог':
        return redirect('login')

    old_mbr = get_object_or_404(MBR, document_id=pk)

    # Создаём новый документ
    doc_type = DocumentType.objects.get(type_name='MBR')
    new_doc = Document.objects.create(type=doc_type)

    # Новая версия
    import re
    version_num = int(re.search(r'v(\d+)', old_mbr.version).group(1)) + 1

    from .models import MBRStatus
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
    for param in old_mbr.parameters.all():
        new_mbr.parameters.add(param)

    messages.success(request, f'Создана новая версия {new_mbr.version}')
    return redirect('mbr:mbr_edit', pk=new_mbr.document_id)