from inventory.models import AuditLog

qs = AuditLog.objects.filter(severity__in=['warning', 'error']).order_by('-timestamp')[:5]
print('count', qs.count())
for item in qs:
    print('id=', item.id, 'severity=', item.severity, 'action=', item.action, 'user_id=', item.user_id)
