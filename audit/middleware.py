from .utils import log_action
from django.utils.deprecation import MiddlewareMixin


class AuditMiddleware(MiddlewareMixin):
    """Автоматическое логирование критических действий"""

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Логирование доступа к критическим функциям
        critical_paths = ['/mbr/approve/', '/ebr/sign/', '/admin/user/']
        if any(path in request.path for path in critical_paths):
            request._audit_action = request.path.split('/')[-2]
        return None