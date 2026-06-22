import os
import sqlite3
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
if not os.path.exists(path):
    raise FileNotFoundError(f"Database not found at {path}")

conn = sqlite3.connect(path)
c = conn.cursor()

invalid_map = {}

print('Scanning char(32) primary key columns for malformed UUID values...')
for table_name, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    cols = [(row[1], row[2], row[5]) for row in c.execute(f"PRAGMA table_info({table_name})")]
    for col_name, col_type, pk in cols:
        if col_type and col_type.lower() == 'char(32)' and pk == 1:
            print(f'Checking PK {table_name}.{col_name}')
            for rowid, value in c.execute(f"SELECT rowid, {col_name} FROM {table_name}"):
                if value is None or value == '' or isinstance(value, bytes):
                    continue
                try:
                    uuid.UUID(str(value))
                except Exception:
                    if value not in invalid_map:
                        invalid_map[value] = uuid.uuid4().hex
                    replacement = invalid_map[value]
                    print(f'  Replace {table_name}.{col_name} rowid={rowid}: {value} -> {replacement}')
                    c.execute(f"UPDATE {table_name} SET {col_name} = ? WHERE rowid = ?", (replacement, rowid))

if invalid_map:
    print('\nPropagating replacements to all char(32) columns...')
    for table_name, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = [row[1] for row in c.execute(f"PRAGMA table_info({table_name})") if row[2].lower() == 'char(32)']
        if not cols:
            continue
        for col_name in cols:
            for rowid, value in c.execute(f"SELECT rowid, {col_name} FROM {table_name}"):
                if value is None or value == '' or isinstance(value, bytes):
                    continue
                if value in invalid_map:
                    replacement = invalid_map[value]
                    print(f'  Update ref {table_name}.{col_name} rowid={rowid}: {value} -> {replacement}')
                    c.execute(f"UPDATE {table_name} SET {col_name} = ? WHERE rowid = ?", (replacement, rowid))

conn.commit()

print('\nVerifying all char(32) UUID values...')
errors = 0
for table_name, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    cols = [row[1] for row in c.execute(f"PRAGMA table_info({table_name})") if row[2].lower() == 'char(32)']
    if not cols:
        continue
    for col_name in cols:
        for rowid, value in c.execute(f"SELECT rowid, {col_name} FROM {table_name}"):
            if value is None or value == '' or isinstance(value, bytes):
                continue
            try:
                uuid.UUID(str(value))
            except Exception as e:
                errors += 1
                print(f'BAD {table_name}.{col_name} rowid={rowid}: {value} ({e})')

if invalid_map:
    print('\nReplaced invalid UUID values:')
    for old, new in invalid_map.items():
        print(f'  {old} -> {new}')

if errors:
    print(f'Verification failed: {errors} invalid UUID values remain.')
else:
    print('Verification succeeded: all char(32) UUID values are valid.')

conn.close()
