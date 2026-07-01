import uuid
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin


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


class CustomErrorResponseMiddleware(MiddlewareMixin):
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
