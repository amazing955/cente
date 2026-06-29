import sqlite3
import os

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()
for table in ['inventory_applicationsetting','inventory_auditlog','inventory_customuser','inventory_customuser_groups','inventory_customuser_user_permissions','inventory_reporttemplate','inventory_roletemplate','inventory_tape','inventory_tapeinventory','inventory_monthlyreport','inventory_reconciliation','inventory_reconciliationresult']:
    try:
        cols = [col[1] for col in c.execute(f"PRAGMA table_info({table})")]
    except sqlite3.OperationalError:
        continue
    print('TABLE', table, 'COLS', cols)
    for row in c.execute(f"SELECT * FROM {table}"):
        print(row)
    print()
conn.close()
