import sqlite3
import os

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

for table, cols in [
    ('inventory_applicationsetting', ['id']),
    ('inventory_auditlog', ['id']),
    ('inventory_roletemplate', ['id']),
    ('inventory_tape', ['id']),
    ('django_admin_log', ['id','user_id','object_id','content_type_id']),
]:
    print('TABLE', table)
    headers = [d[1] for d in c.execute(f"PRAGMA table_info({table})")]
    query = f"SELECT rowid, * FROM {table}"
    for row in c.execute(query):
        rowid = row[0]
        values = dict(zip(['rowid'] + headers, row))
        bad = []
        for col in cols:
            v = values[col]
            if v is None or v == '' or isinstance(v, bytes):
                continue
            try:
                import uuid
                uuid.UUID(str(v))
            except Exception:
                bad.append((col, v))
        if bad:
            print(values)
    print()
conn.close()
