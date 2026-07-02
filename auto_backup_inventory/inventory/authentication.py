import logging
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError

from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditedJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except TokenError as exc:
            self._log_auth_failure(request, str(exc))
            raise

    def _log_auth_failure(self, request, reason):
        path = request.path if hasattr(request, 'path') else ''
        ip_address = self._get_client_ip(request)
        AuditLog.objects.create(
            name='Authentication Failed',
            action=f'{request.method} {path}',
            user=None,
            message=f'Reason: {reason} | IP: {ip_address}',
            severity='warning',
        )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
