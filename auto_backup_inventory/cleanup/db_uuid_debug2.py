import os
import sqlite3
import uuid

path = os.path.join(os.getcwd(), 'db.sqlite3')
conn = sqlite3.connect(path)
c = conn.cursor()

print('DB file:', path)
for table in [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")] :
    print('\nTABLE', table)
    columns = list(c.execute(f"PRAGMA table_info('{table}')"))
    for cid, name, coltype, notnull, dflt_value, pk in columns:
        if coltype and any(x in coltype.lower() for x in ['uuid', 'char(32)', 'char(36)', 'varchar(32)', 'varchar(36)']):
            print('  COL', name, coltype)
            invalids = []
            for row in c.execute(f"SELECT rowid, {name} FROM {table}"):
                rowid, value = row
                if value is None or value == '':
                    continue
                try:
                    uuid.UUID(str(value))
                except Exception as e:
                    invalids.append((rowid, value, type(value).__name__, len(str(value)), str(e)))
                    if len(invalids) >= 20:
                        break
            if invalids:
                print(f'    INVALID {len(invalids)} rows:')
                for inv in invalids:
                    print('      ', inv)
            else:
                print('    OK')
conn.close()
