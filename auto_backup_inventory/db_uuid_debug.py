import os
import sqlite3
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

print('Inspecting UUID-like columns in SQLite DB...')
for table_name, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    cols = [(row[1], row[2]) for row in c.execute(f"PRAGMA table_info({table_name})")]
    uuid_cols = [name for name, coltype in cols if coltype and ('uuid' in coltype.lower() or 'char(32)' in coltype.lower() or 'varchar(36)' in coltype.lower() or 'char(36)' in coltype.lower() or 'varchar(32)' in coltype.lower())]
    if not uuid_cols:
        continue
    print(f'\nTABLE {table_name} UUID-like columns: {uuid_cols}')
    for col_name in uuid_cols:
        invalids = []
        for rowid, value in c.execute(f"SELECT rowid, {col_name} FROM {table_name}"):
            if value is None or value == '' or isinstance(value, bytes):
                continue
            try:
                uuid.UUID(str(value))
            except Exception as e:
                invalids.append((rowid, value, type(value).__name__, len(str(value)), str(e)))
                if len(invalids) >= 20:
                    break
        if invalids:
            print(f'  INVALID {table_name}.{col_name}: {len(invalids)} invalid rows (showing up to 20)')
            for row in invalids:
                print('    ', row)
        else:
            print(f'  OK {table_name}.{col_name}')
conn.close()
