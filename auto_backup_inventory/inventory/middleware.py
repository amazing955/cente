import time
import uuid
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from .models import AuditLog


class ClearInvalidSessionUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        session_key = request.session.session_key
        if not session_key:
            return

        user_id = request.session.get('_auth_user_id')
        if user_id is None:
            return

        try:
            uuid.UUID(str(user_id))
        except (ValueError, TypeError, AttributeError):
            request.session.pop('_auth_user_id', None)
            request.session.pop('_auth_user_backend', None)
            request.session.pop('_auth_user_hash', None)
            request.session.save()


class APIAuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._audit_start_time = time.perf_counter()

    def process_response(self, request, response):
        try:
            path = request.path or ''
            is_api_path = path.startswith('/api') or path.startswith('/apis') or '/investigation' in path
            if not is_api_path:
                return response

            user = getattr(request, 'user', None)
            user_id = getattr(user, 'pk', None)
            username = getattr(user, 'username', None)
            duration_ms = int((time.perf_counter() - getattr(request, '_audit_start_time', time.perf_counter())) * 1000)
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
            AuditLog.objects.create(
                name='API Access',
                action=f'{request.method} {path}',
                user=user if getattr(user, 'is_authenticated', False) else None,
                message=f'Status: {response.status_code} | IP: {ip_address} | Duration: {duration_ms}ms',
                severity='warning' if response.status_code >= 400 else 'info',
            )
        except Exception:
            pass
        return response


class CustomErrorResponseMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('//'):
            normalized_path = '/' + request.path.lstrip('/')
            request.path = normalized_path
            request.path_info = normalized_path

    def process_response(self, request, response):
        if not response.get('Content-Type', '').startswith('text/html'):
            return response

        if not request.accepts('text/html'):
            return response

        template_map = {
            400: '400.html',
            403: '403.html',
            404: '404.html',
            500: '500.html',
        }

        template_name = template_map.get(response.status_code)
        if template_name:
            return render(request, template_name, status=response.status_code)

        return response
