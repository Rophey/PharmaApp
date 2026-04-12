from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import AuditLog, Action, ElectronicSignature
from mbr.models import Document
from ebr.models import EBR
import hashlib
import json
import datetime


def audit_log(request):
    if 'user_id' not in request.session:
        return redirect('login')

    # Только начальник ОКК и выше имеют доступ
    allowed_roles = ['начальник ОКК', 'директор', 'системный администратор']
    if request.session.get('user_role') not in allowed_roles:
        messages.error(request, 'У вас нет доступа к журналу аудита')
        return redirect('dashboard')

    logs = AuditLog.objects.all().select_related('user', 'action', 'document').order_by('-timestamp')[:100]

    context = {
        'user': request.current_user,
        'logs': logs,
    }
    return render(request, 'audit/audit_log.html', context)


def signature_list(request):
    if 'user_id' not in request.session:
        return redirect('login')

    signatures = ElectronicSignature.objects.all().select_related('user', 'document').order_by('-signature_date')[:50]

    context = {
        'user': request.current_user,
        'signatures': signatures,
    }
    return render(request, 'audit/signature_list.html', context)


def sign_document(request, doc_id):
    if 'user_id' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        comment = request.POST.get('comment', '')

        document = get_object_or_404(Document, document_id=doc_id)

        # Создаём хэш подписи
        signature_data = {
            'user_id': request.current_user.user_id,
            'document_id': doc_id,
            'timestamp': str(datetime.datetime.now()),
            'comment': comment
        }
        signature_hash = hashlib.sha256(
            json.dumps(signature_data, sort_keys=True).encode()
        ).hexdigest()

        # Сохраняем подпись
        signature = ElectronicSignature.objects.create(
            user=request.current_user,
            document=document,
            signature_hash=signature_hash,
            comment=comment
        )

        # Обновляем документ
        if document.type.type_name == 'MBR':
            from mbr.models import MBR
            mbr = MBR.objects.get(document=document)
            mbr.signed_by = request.current_user
            mbr.save()
        elif document.type.type_name == 'EBR':
            from ebr.models import EBR
            ebr = EBR.objects.get(document=document)
            ebr.signed_by = request.current_user
            ebr.save()

        # Логируем
        action = Action.objects.get(
            action_name='Подписание EBR' if document.type.type_name == 'EBR' else 'Утверждение MBR')
        AuditLog.objects.create(
            user=request.current_user,
            action=action,
            document=document,
            comment=f"Подписан документ {document.document_id}"
        )

        messages.success(request, 'Документ подписан')

        # Перенаправляем на соответствующий документ
        if document.type.type_name == 'MBR':
            return redirect('mbr:mbr_detail', pk=doc_id)
        else:
            return redirect('ebr:ebr_detail', pk=doc_id)

    return redirect('dashboard')