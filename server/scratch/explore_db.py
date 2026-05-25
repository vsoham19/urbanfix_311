import sqlite3
import os

db_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\server\urbanfix_311.db"

if not os.path.exists(db_path):
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    print("Tables:", tables)
    
    # Check structured_records distinct wards
    if "structured_records" in tables:
        cursor.execute("SELECT DISTINCT ward_name FROM structured_records")
        wards = [r[0] for r in cursor.fetchall()]
        print(f"\nDistinct wards in structured_records ({len(wards)}):")
        print(sorted(wards))
        
    # Check sewer_infrastructure distinct wards
    if "sewer_infrastructure" in tables:
        cursor.execute("SELECT DISTINCT ward_name FROM sewer_infrastructure")
        wards = [r[0] for r in cursor.fetchall()]
        print(f"\nDistinct wards in sewer_infrastructure ({len(wards)}):")
        print(sorted(wards))
        
    conn.close()
