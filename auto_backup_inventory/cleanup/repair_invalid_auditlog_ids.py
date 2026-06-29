import os
import sqlite3
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

print('Repairing invalid UUID values in inventory_auditlog.id...')
updated = 0
for rowid, value in c.execute("SELECT rowid, id FROM inventory_auditlog"):
    if value is None or value == '':
        continue
    try:
        uuid.UUID(str(value))
    except Exception:
        new_uuid = uuid.uuid4().hex
        print(f'Updating rowid={rowid} id={value} -> {new_uuid}')
        c.execute("UPDATE inventory_auditlog SET id = ? WHERE rowid = ?", (new_uuid, rowid))
        updated += 1

conn.commit()
conn.close()
print(f'Updated {updated} rows.')
