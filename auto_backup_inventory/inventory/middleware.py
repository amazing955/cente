import uuid
from django.contrib.auth import get_user_model
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
