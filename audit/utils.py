from django.contrib.contenttypes.models import ContentType
from .models import AuditLog, Action


def log_action(user, action_name, document, comment='', ip_address=None):
    """
    Логирование действия в журнал аудита (ТЗ 4.2.6.1.2)

    Args:
        user: Пользователь, совершивший действие
        action_name: Название действия (строка)
        document: Объект документа (MBR, EBR, и т.д.)
        comment: Комментарий к действию
        ip_address: IP-адрес пользователя
    """
    # Получение или создание действия
    action, _ = Action.objects.get_or_create(action_name=action_name)

    # Создание записи аудита
    AuditLog.objects.create(
        user=user,
        action=action,
        content_type=ContentType.objects.get_for_model(document),
        object_id=document.id,
        comment=comment,
        ip_address=ip_address
    )