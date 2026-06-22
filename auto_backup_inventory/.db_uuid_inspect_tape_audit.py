import sqlite3
import os
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

def check_table(table, col):
    print(f'CHECK {table}.{col}')
    for rowid, value, value_type in c.execute(f"SELECT rowid, {col}, typeof({col}) FROM {table} ORDER BY rowid LIMIT 200"):
        if value is None or value == '' or isinstance(value, bytes):
            continue
        try:
            uuid.UUID(str(value))
        except Exception as e:
            print('INVALID', rowid, repr(value), value_type, type(value).__name__, str(e))
    print()

for table, col in [
    ('inventory_auditlog', 'id'),
    ('inventory_tape', 'id'),
    ('inventory_auditlog', 'user_id'),
    ('inventory_shipment', 'id'),
    ('inventory_reconciliation', 'id'),
]:
    check_table(table, col)

conn.close()
