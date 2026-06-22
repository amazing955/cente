import os
import sqlite3
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
if not os.path.exists(path):
    raise FileNotFoundError(f"Database not found at {path}")

conn = sqlite3.connect(path)
c = conn.cursor()

print('Repairing malformed UUIDs in char(32) primary key columns...')

invalid_map = {}

# Inspect all char(32) primary key columns and replace malformed UUID values.
for table, col, pk in c.execute("SELECT tbl.name, pr.name, pr.pk FROM sqlite_master AS tbl JOIN pragma_table_info(tbl.name) AS pr WHERE tbl.type='table' AND pr.[type]='char(32)'"):
    if pk != 1:
        continue
    print(f'Checking PK {table}.{col}')
    for rowid, value in c.execute(f"SELECT rowid, {col} FROM {table}"):
        if value is None or value == '' or isinstance(value, bytes):
            continue
        try:
            uuid.UUID(str(value))
        except Exception:
            new_id = uuid.uuid4().hex
            invalid_map[value] = new_id
            print(f'  Replace {table}.{col} rowid={rowid}: {value} -> {new_id}')
            c.execute(f"UPDATE {table} SET {col} = ? WHERE rowid = ?", (new_id, rowid))

if invalid_map:
    print('\nPropagating replacements to all char(32) columns...')
    for table, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})") if row[2].lower() == 'char(32)']
        if not cols:
            continue
        for col in cols:
            for rowid, value in c.execute(f"SELECT rowid, {col} FROM {table}"):
                if value is None or value == '' or isinstance(value, bytes):
                    continue
                replacement = invalid_map.get(value)
                if replacement:
                    print(f'  Update ref {table}.{col} rowid={rowid}: {value} -> {replacement}')
                    c.execute(f"UPDATE {table} SET {col} = ? WHERE rowid = ?", (replacement, rowid))

conn.commit()

print('\nVerifying char(32) column UUID validity...')
errors = False
for table, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})") if row[2].lower() == 'char(32)']
    if not cols:
        continue
    for col in cols:
        for rowid, value in c.execute(f"SELECT rowid, {col} FROM {table}"):
            if value is None or value == '' or isinstance(value, bytes):
                continue
            try:
                uuid.UUID(str(value))
            except Exception as e:
                if not errors:
                    print('Invalid UUID values still present:')
                    errors = True
                print(f'BAD {table}.{col} rowid={rowid}: {value} ({e})')

if not invalid_map:
    print('No malformed primary key UUID values found.')
else:
    print('Repair completed. Invalid UUID primary keys replaced:')
    for old, new in invalid_map.items():
        print(f'  {old} -> {new}')

if not errors:
    print('All char(32) UUID values are now valid.')

conn.close()
