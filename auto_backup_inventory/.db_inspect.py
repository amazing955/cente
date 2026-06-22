import sqlite3
import os
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()
print('tables:')
for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(row[0])
print()
for table in ['inventory_applicationsetting','inventory_auditlog','inventory_customuser','inventory_customuser_groups','inventory_customuser_user_permissions','inventory_monthlyreport','inventory_reconciliation','inventory_reconciliationresult','inventory_reporttemplate','inventory_roletemplate','inventory_shipment','inventory_shipment_tapes','inventory_tape','inventory_tapeinventory','django_admin_log']:
    try:
        cols = [col[1] for col in c.execute(f"PRAGMA table_info({table})")]
    except sqlite3.OperationalError:
        continue
    print('TABLE', table, 'COLS', cols)
    for col in cols:
        if col.endswith('_id') or col == 'id':
            bad = []
            for val_row in c.execute(f"SELECT {col} FROM {table}"):
                v = val_row[0]
                if v is None or v == '' or isinstance(v, bytes):
                    continue
                try:
                    uuid.UUID(str(v))
                except Exception as e:
                    bad.append((v, str(e)))
                    break
            if bad:
                print(' BAD', col, bad[:10])
    print()
conn.close()
