import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
import django
django.setup()
from inventory.models import AuditLog

qs = AuditLog.objects.filter(severity__in=['warning', 'error']).order_by('-timestamp')[:10]
print('Query OK, count:', qs.count())
for i, audit in enumerate(qs, start=1):
    print(i, audit.id, type(audit.id), audit.user_id, audit.severity, audit.timestamp)
