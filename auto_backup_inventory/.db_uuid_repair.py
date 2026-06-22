import sqlite3
import os
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

repair_map = {
    'inventory_applicationsetting': ['id'],
    'inventory_auditlog': ['id'],
    'inventory_roletemplate': ['id'],
    'inventory_tape': ['id'],
}

for table, cols in repair_map.items():
    print('REPAIR TABLE', table)
    for col in cols:
        for row in c.execute(f"SELECT rowid, {col} FROM {table}"):
            rowid, value = row
            if value is None or value == '':
                continue
            try:
                uuid.UUID(str(value))
            except Exception:
                new_id = uuid.uuid4().hex
                print(f" UPDATE {table}.{col} rowid={rowid} {value} -> {new_id}")
                c.execute(f"UPDATE {table} SET {col} = ? WHERE rowid = ?", (new_id, rowid))
conn.commit()

# verify
print('\nVERIFY AFTER REPAIR')
for table, cols in repair_map.items():
    print('TABLE', table)
    for col in cols:
        for row in c.execute(f"SELECT rowid, {col} FROM {table}"):
            rowid, value = row
            try:
                uuid.UUID(str(value))
            except Exception as e:
                print(' BAD', table, col, rowid, value, e)
conn.close()
