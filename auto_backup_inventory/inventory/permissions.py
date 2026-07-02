from django.contrib.auth.models import Group
from rest_framework.permissions import BasePermission


class InvestigationPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        return request.user.groups.filter(name='DR Team').exists()
