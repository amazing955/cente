import sqlite3
import os
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()
print('=== Invalid char(32) UUID values ===')
for table, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    cols = [(row[1], row[2]) for row in c.execute(f"PRAGMA table_info({table})")]
    char32_cols = [name for name, coltype in cols if coltype.lower() == 'char(32)']
    if not char32_cols:
        continue
    for col in char32_cols:
        rows = []
        for rowid, value in c.execute(f"SELECT rowid, {col} FROM {table}"):
            if value is None or value == '' or isinstance(value, bytes):
                continue
            try:
                uuid.UUID(str(value))
            except Exception as e:
                rows.append((rowid, value, str(e)))
        if rows:
            print('TABLE', table, 'COL', col, 'INVALID:', len(rows), 'sample', rows[:10])
conn.close()
