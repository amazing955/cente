import sqlite3
import os

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()
for table in ['inventory_applicationsetting','inventory_auditlog','inventory_customuser_groups','inventory_customuser_user_permissions','inventory_roletemplate','inventory_tape','django_admin_log']:
    print('TABLE', table)
    for row in c.execute(f"PRAGMA table_info({table})"):
        print(row)
    print()
conn.close()
