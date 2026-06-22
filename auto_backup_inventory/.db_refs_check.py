import sqlite3
import os

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

for table, cols in [
    ('inventory_shipment_tapes', ['rowid', 'id', 'shipment_id', 'tape_id']),
    ('inventory_reconciliationresult', ['rowid', 'id', 'reconciliation_id', 'tape_id']),
    ('inventory_monthlyreport', ['rowid', 'id', 'generated_by_id']),
    ('django_admin_log', ['rowid', 'id', 'object_id', 'user_id', 'content_type_id']),
]:
    print('TABLE', table)
    for row in c.execute(f"SELECT {', '.join(cols)} FROM {table}"):
        print(row)
    print()

print('TAPES:')
for row in c.execute("SELECT rowid, id, volser FROM inventory_tape"):
    print(row)

conn.close()
