import os
import sys
# Ensure project root is on sys.path so Django can import the project package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
import django
django.setup()

from django.db import connection
from inventory.models import SchemaChangeLog, PendingApproval

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = %s ORDER BY ordinal_position", ["inventory_tape"])
    cols = [r[0] for r in cursor.fetchall()]

print('COLUMNS:', cols)

print('\nRecent SchemaChangeLog entries:')
for s in SchemaChangeLog.objects.order_by('-uploaded_date')[:20]:
    sql_excerpt = (s.sql_executed or '')[:400]
    print(f"{s.uploaded_date} | {s.column_name} | {s.detected_data_type} | {s.synchronization_status} | {sql_excerpt}")

print('\nRecent Tape Schema PendingApprovals:')
for pa in PendingApproval.objects.filter(transaction_type__icontains='Schema').order_by('-request_date')[:20]:
    payload = pa.request_payload or {}
    requested_changes = pa.requested_changes or []
    print('---')
    print('request_date:', pa.request_date)
    print('transaction_type:', pa.transaction_type)
    print('status:', pa.status)
    print('requester_id:', pa.requester_id)
    print('requested_changes_count:', len(requested_changes))
    print('request_payload_excerpt:', str(payload)[:400])

# Exit with success
sys.exit(0)
