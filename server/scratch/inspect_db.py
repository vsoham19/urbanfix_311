import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'urbanfix_311.db'))
print(f"Database path: {db_path}")

if not os.path.exists(db_path):
    print("Database file does not exist!")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print("Tables:", tables)
    for table_name_tup in tables:
        table_name = table_name_tup[0]
        cur.execute(f"PRAGMA table_info({table_name})")
        info = cur.fetchall()
        print(f"\nTable: {table_name}")
        for col in info:
            print(f"  Col: {col[1]} ({col[2]})")
    conn.close()
