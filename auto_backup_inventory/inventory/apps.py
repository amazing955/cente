from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'inventory'

    def ready(self):
        from django.contrib.auth.models import Group
        from django.db.utils import OperationalError, ProgrammingError

        group_names = [
            'Backup Administrator',
            'Operations Manager',
            'Warehouse Operations',
            'Compliance Auditor',
            'Courier',
            'Auditor',
            'Security Officer',
            'Information Security Officer',
            'DR Team',
            'System Administrator',
            'Supreme Approver',
        ]

        try:
            for name in group_names:
                Group.objects.get_or_create(name=name)
        except (OperationalError, ProgrammingError):
            # Database tables may not be ready yet (migrations running)
            pass
