import sqlite3
import os

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()
print('PRAGMA foreign_keys:', c.execute('PRAGMA foreign_keys').fetchall())
for table in ['inventory_applicationsetting', 'inventory_auditlog', 'inventory_customuser', 'inventory_customuser_groups', 'inventory_customuser_user_permissions', 'inventory_monthlyreport', 'inventory_reconciliation', 'inventory_reconciliationresult', 'inventory_reporttemplate', 'inventory_roletemplate', 'inventory_shipment', 'inventory_shipment_tapes', 'inventory_tape', 'inventory_tapeinventory', 'django_admin_log']:
    print('TABLE', table)
    try:
        for fk in c.execute(f"PRAGMA foreign_key_list({table})"):
            print(' FK', fk)
    except sqlite3.OperationalError as e:
        print(' ERROR', e)
    print()
conn.close()
