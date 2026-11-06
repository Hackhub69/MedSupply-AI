"""Generate SQL for a new Db2 demo schema; does not connect to Db2."""
import sqlite3, tempfile
from pathlib import Path
import app

def literal(value):
    if isinstance(value, int): return str(value)
    return "'" + str(value).replace("'", "''") + "'"

with tempfile.TemporaryDirectory() as directory:
    app.DB_PATH = str(Path(directory) / 'sample.db')
    app.init_demo()
    connection = sqlite3.connect(app.DB_PATH)
    statements = [s + ';' for s in app.SCHEMA]
    for table in ('hospitals', 'medicines', 'inventory', 'demand', 'suppliers', 'documents'):
        for row in connection.execute('SELECT * FROM ' + table):
            statements.append('INSERT INTO ' + table + ' VALUES (' + ', '.join(literal(v) for v in row) + ');')
    connection.close()
    Path('db2_seed.sql').write_text('-- Synthetic sample data. Use only in a new, empty schema.\n' + '\n'.join(statements) + '\n', encoding='utf-8')
print('Wrote db2_seed.sql. Review it before running against an empty Db2 schema.')
