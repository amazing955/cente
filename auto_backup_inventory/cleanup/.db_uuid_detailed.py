import sqlite3
import os
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

models = {
    'inventory_applicationsetting': ['id'],
    'inventory_auditlog': ['id'],
    'inventory_customuser': ['id'],
    'inventory_monthlyreport': ['id', 'generated_by_id'],
    'inventory_reconciliation': ['id', 'performed_by_id', 'approved_by_id', 'reviewed_by_id'],
    'inventory_reconciliationresult': ['id', 'reconciliation_id', 'tape_id'],
    'inventory_reporttemplate': ['id'],
    'inventory_roletemplate': ['id'],
    'inventory_shipment': ['id', 'approved_by_id', 'created_by_id', 'last_updated_by_id'],
    'inventory_shipment_tapes': ['shipment_id', 'tape_id'],
    'inventory_tape': ['id'],
    'inventory_tapeinventory': ['id'],
}

for table, cols in models.items():
    print('TABLE', table)
    for col in cols:
        invalids = []
        for row in c.execute(f"SELECT rowid, {col} FROM {table}"):
            rowid, value = row
            if value is None or value == '' or isinstance(value, bytes):
                continue
            try:
                uuid.UUID(str(value))
            except Exception as e:
                invalids.append((rowid, value, str(e)))
        if invalids:
            print(' COL', col, 'INVALIDS:', invalids)
    print()

# Search for references to invalid tape ids and invalid shipment ids
for src_table, src_col in [('inventory_shipment_tapes','tape_id'), ('inventory_shipment_tapes','shipment_id'), ('inventory_reconciliationresult','tape_id'), ('inventory_auditlog','user_id'), ('inventory_monthlyreport','generated_by_id'), ('inventory_reconciliation','performed_by_id'), ('inventory_reconciliation','approved_by_id'), ('inventory_reconciliation','reviewed_by_id'), ('inventory_shipment','approved_by_id'), ('inventory_shipment','created_by_id'), ('inventory_shipment','last_updated_by_id')]:
    print('REF CHECK', src_table, src_col)
    invalid_refs = []
    for row in c.execute(f"SELECT rowid, {src_col} FROM {src_table}"):
        rowid, value = row
        if value is None or value == '' or isinstance(value, bytes):
            continue
        try:
            uuid.UUID(str(value))
        except Exception:
            invalid_refs.append((rowid, value))
    if invalid_refs:
        print('  INVALID REFS', invalid_refs)
    else:
        print('  none')

conn.close()
