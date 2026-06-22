import sqlite3
import os
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

for table, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})") if row[2].lower() == 'char(32)']
    if not cols:
        continue
    updates = 0
    for col in cols:
        rows = list(c.execute(f"SELECT rowid, {col} FROM {table}"))
        for rowid, value in rows:
            if value is None or value == '' or isinstance(value, bytes):
                continue
            try:
                uuid.UUID(str(value))
            except Exception:
                new_id = uuid.uuid4().hex
                print(f"UPDATE {table}.{col} rowid={rowid} {value} -> {new_id}")
                c.execute(f"UPDATE {table} SET {col} = ? WHERE rowid = ?", (new_id, rowid))
                updates += 1
    if updates:
        print(f"{table}: {updates} invalid {len(cols)} char(32) column values updated")

conn.commit()

print('\nVERIFY ALL CHAR(32) VALUES')
for table, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})") if row[2].lower() == 'char(32)']
    if not cols:
        continue
    for col in cols:
        bad = []
        for rowid, value in c.execute(f"SELECT rowid, {col} FROM {table}"):
            if value is None or value == '' or isinstance(value, bytes):
                continue
            try:
                uuid.UUID(str(value))
            except Exception as e:
                bad.append((rowid, value, str(e)))
        if bad:
            print('BAD', table, col, bad[:20])
conn.close()
