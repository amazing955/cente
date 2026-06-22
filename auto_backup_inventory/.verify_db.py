from inventory.models import ApplicationSetting, AuditLog, Tape, RoleTemplate

print('ApplicationSetting exists:', ApplicationSetting.objects.exists())
print('First ApplicationSetting:', ApplicationSetting.objects.first())
print('AuditLog count:', AuditLog.objects.count())
print('Tape count:', Tape.objects.count())
print('RoleTemplate count:', RoleTemplate.objects.count())
