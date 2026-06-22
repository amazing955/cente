import os
import sqlite3
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

invalid_rows = []
for rowid, value in c.execute("SELECT rowid, id FROM inventory_auditlog"):
    value_str = str(value) if value is not None else ''
    if not value_str:
        continue
    try:
        uuid.UUID(value_str)
    except Exception:
        invalid_rows.append((rowid, value_str))

print(f'Found {len(invalid_rows)} invalid AuditLog id rows')
for rowid, value in invalid_rows:
    new_uuid = uuid.uuid4().hex
    print(f'Updating rowid={rowid} id={value} -> {new_uuid}')
    c.execute("UPDATE inventory_auditlog SET id = ? WHERE rowid = ?", (new_uuid, rowid))

conn.commit()
conn.close()
print('Repair complete')
