import sqlite3
import os
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

checks = {
    'inventory_applicationsetting': ['id'],
    'inventory_auditlog': ['id', 'user_id'],
    'inventory_customuser': ['id'],
    'inventory_customuser_groups': ['customuser_id'],
    'inventory_customuser_user_permissions': ['customuser_id'],
    'inventory_monthlyreport': ['id', 'generated_by_id'],
    'inventory_reconciliation': ['id', 'performed_by_id', 'approved_by_id', 'reviewed_by_id'],
    'inventory_reconciliationresult': ['id', 'reconciliation_id', 'tape_id'],
    'inventory_reporttemplate': ['id'],
    'inventory_roletemplate': ['id'],
    'inventory_shipment': ['id', 'approved_by_id', 'created_by_id', 'last_updated_by_id'],
    'inventory_shipment_tapes': ['id', 'shipment_id', 'tape_id'],
    'inventory_tape': ['id'],
    'inventory_tapeinventory': ['id'],
    'django_admin_log': ['id', 'user_id'],
}

for table, cols in checks.items():
    print('TABLE', table)
    for col in cols:
        print(' COL', col)
        try:
            for val_row in c.execute(f"SELECT {col} FROM {table}"):
                v = val_row[0]
                if v is None or v == '' or isinstance(v, bytes):
                    continue
                try:
                    uuid.UUID(str(v))
                except Exception as e:
                    print('  BAD', v, str(e))
                    break
        except sqlite3.OperationalError as e:
            print('  ERROR', e)
    print()
conn.close()
