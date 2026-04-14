from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from .models import AuditLog, Action, ElectronicSignature
from mbr.models import Document, MBR
from ebr.models import EBR
from users.models import User
import hashlib
import json
import datetime
import csv


def audit_log(request):
    if 'user_id' not in request.session:
        return redirect('users:login')

    # Только начальник ОКК и выше имеют доступ
    allowed_roles = ['начальник ОКК', 'директор', 'системный администратор']
    if request.session.get('user_role') not in allowed_roles:
        messages.error(request, 'У вас нет доступа к журналу аудита')
        return redirect('users:qc_chief_dashboard')

    # Получаем фильтры
    filter_user = request.GET.get('user', '')
    filter_action = request.GET.get('action', '')
    filter_date_from = request.GET.get('date_from', '')
    filter_date_to = request.GET.get('date_to', '')
    filter_search = request.GET.get('search', '')

    # Формируем queryset
    logs = AuditLog.objects.all().select_related('user', 'action', 'document')

    if filter_user:
        logs = logs.filter(user__user_id=filter_user)
    if filter_action:
        logs = logs.filter(action_id=filter_action)
    if filter_date_from:
        logs = logs.filter(timestamp__date__gte=filter_date_from)
    if filter_date_to:
        logs = logs.filter(timestamp__date__lte=filter_date_to)
    if filter_search:
        logs = logs.filter(
            comment__icontains=filter_search
        ) | logs.filter(
            action__action_name__icontains=filter_search
        ) | logs.filter(
            user__last_name__icontains=filter_search
        ) | logs.filter(
            user__first_name__icontains=filter_search
        )

    logs = logs.order_by('-timestamp')

    # Пагинация
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Список пользователей и действий для фильтров
    users = User.objects.filter(auditlog__isnull=False).distinct().order_by('last_name')[:50]
    actions = Action.objects.filter(auditlog__isnull=False).distinct().order_by('action_name')

    # Экспорт в CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="audit_log.csv"'
        # BOM для корректного отображения кириллицы в Excel
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow(['Дата и время', 'Пользователь', 'Действие', 'Документ', 'Комментарий', 'IP-адрес'])

        for log in logs[:500]:  # Ограничиваем экспорт 500 записями
            doc_info = ''
            if log.document:
                doc_info = _get_document_info(log.document)
            writer.writerow([
                log.timestamp.strftime('%d.%m.%Y %H:%M:%S'),
                f"{log.user.last_name} {log.user.first_name}",
                log.action.action_name,
                doc_info,
                log.comment or '',
                log.ip_address or '',
            ])

        return response

    context = {
        'user': request.current_user,
        'page_obj': page_obj,
        'users': users,
        'actions': actions,
        'filter_user': filter_user,
        'filter_action': filter_action,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'filter_search': filter_search,
    }
    return render(request, 'audit/audit_log.html', context)


def _get_document_info(doc):
    """Возвращает информативное описание документа."""
    try:
        if doc.type.type_name == 'MBR':
            mbr = MBR.objects.get(document=doc)
            return f"MBR {mbr.product.product_code} {mbr.version} ({mbr.product.product_name})"
        elif doc.type.type_name == 'EBR':
            ebr = EBR.objects.get(document=doc)
            return f"Партия {ebr.batch_number} ({ebr.mbr.product.product_name})"
    except Exception:
        pass
    return f"Документ #{doc.pk} ({doc.type.type_name})"


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

        document = get_object_or_404(Document, id=doc_id)

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
        try:
            if document.type.type_name == 'MBR':
                from mbr.models import MBR
                try:
                    mbr = MBR.objects.get(document=document)
                    mbr.signed_by = request.current_user
                    mbr.save()
                except MBR.DoesNotExist:
                    pass
            elif document.type.type_name == 'EBR':
                from ebr.models import EBR
                try:
                    ebr = EBR.objects.get(document=document)
                    ebr.signed_by = request.current_user
                    ebr.save()
                except EBR.DoesNotExist:
                    pass
        except Exception:
            pass

        # Логируем
        try:
            action_name = 'Подписание EBR' if document.type.type_name == 'EBR' else 'Утверждение MBR'
            action, _ = Action.objects.get_or_create(action_name=action_name)
        except Exception:
            action = None

        if action:
            AuditLog.objects.create(
                user=request.current_user,
                action=action,
                document=document,
                comment=f"Подписан документ {document.id}"
            )

        messages.success(request, 'Документ подписан')

        # Перенаправляем на соответствующий документ
        if document.type.type_name == 'MBR':
            return redirect('mbr:mbr_detail', pk=doc_id)
        else:
            return redirect('ebr:ebr_detail', pk=doc_id)

    return redirect('users:director_dashboard')
