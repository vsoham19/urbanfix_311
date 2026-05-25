import os
import sqlite3
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class SQLiteFallback:
    """
    A robust fallback database layer using SQLite to store records 
    in case Supabase URL/Key are missing or invalid.
    """
    def __init__(self, db_path="urbanfix_311.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            # raw_records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_records (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT,
                    raw_data TEXT,
                    created_at TEXT
                )
            """)
            # structured_records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS structured_records (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT,
                    complaint_id TEXT,
                    ward_name TEXT,
                    complaint_category TEXT,
                    severity TEXT,
                    description TEXT,
                    language TEXT,
                    lat REAL,
                    lng REAL,
                    phone TEXT,
                    postal_code TEXT,
                    date_filed TEXT,
                    confidence_score REAL,
                    created_at TEXT
                )
            """)
            # quarantine_records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quarantine_records (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT,
                    raw_data TEXT,
                    partial_clean TEXT,
                    reason_code TEXT,
                    priority_flag INTEGER DEFAULT 0,
                    confidence_score REAL,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    created_at TEXT
                )
            """)
            # flagged_records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flagged_records (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT,
                    raw_data TEXT,
                    partial_clean TEXT,
                    confidence_score REAL,
                    flags TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    created_at TEXT
                )
            """)
            # cleaning_reports table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cleaning_reports (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT,
                    total_records INTEGER,
                    structured_count INTEGER,
                    quarantined_count INTEGER,
                    flagged_count INTEGER,
                    dropped_count INTEGER,
                    avg_confidence REAL,
                    duplicate_count INTEGER,
                    processing_time_ms INTEGER,
                    created_at TEXT
                )
            """)
            # Drop old sewer_infrastructure if it doesn't have the new columns to avoid schema mismatch
            try:
                cursor = conn.execute("PRAGMA table_info(sewer_infrastructure)")
                cols = [row[1] for row in cursor.fetchall()]
                if cols and "installation_method" not in cols:
                    conn.execute("DROP TABLE IF EXISTS sewer_infrastructure")
            except Exception:
                pass

            # sewer_infrastructure table for Phase 2
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sewer_infrastructure (
                    id TEXT PRIMARY KEY,
                    ward_name TEXT UNIQUE NOT NULL,
                    avg_sewer_age_years REAL NOT NULL,
                    tree_count INTEGER NOT NULL,
                    population_density REAL NOT NULL,
                    restaurant_count INTEGER NOT NULL,
                    pipe_diameter_mm REAL NOT NULL,
                    installation_method TEXT NOT NULL,
                    pipe_length_m REAL NOT NULL,
                    pipe_depth_m REAL NOT NULL,
                    connections_count INTEGER NOT NULL,
                    sensor_latitude REAL NOT NULL,
                    sensor_longitude REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def insert_raw_records(self, records):
        with self._get_conn() as conn:
            for r in records:
                conn.execute(
                    "INSERT INTO raw_records (id, batch_id, raw_data, created_at) VALUES (?, ?, ?, ?)",
                    (r["id"], r["batch_id"], json.dumps(r["raw_data"]), r["created_at"])
                )
            conn.commit()

    def insert_structured_records(self, records):
        with self._get_conn() as conn:
            for r in records:
                conn.execute("""
                    INSERT INTO structured_records (
                        id, batch_id, complaint_id, ward_name, complaint_category,
                        severity, description, language, lat, lng, phone,
                        postal_code, date_filed, confidence_score, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["id"], r["batch_id"], r["complaint_id"], r["ward_name"],
                    r["complaint_category"], r["severity"], r["description"],
                    r["language"], r["lat"], r["lng"], r["phone"],
                    r["postal_code"], r["date_filed"], r["confidence_score"], r["created_at"]
                ))
            conn.commit()

    def insert_quarantine_records(self, records):
        with self._get_conn() as conn:
            for r in records:
                conn.execute("""
                    INSERT INTO quarantine_records (
                        id, batch_id, raw_data, partial_clean, reason_code,
                        priority_flag, confidence_score, status, reviewed_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["id"], r["batch_id"], json.dumps(r["raw_data"]),
                    json.dumps(r["partial_clean"]) if r.get("partial_clean") else None,
                    r["reason_code"], 1 if r["priority_flag"] else 0, r["confidence_score"],
                    r["status"], r["reviewed_by"], r["created_at"]
                ))
            conn.commit()

    def insert_flagged_records(self, records):
        with self._get_conn() as conn:
            for r in records:
                conn.execute("""
                    INSERT INTO flagged_records (
                        id, batch_id, raw_data, partial_clean, confidence_score,
                        flags, status, reviewed_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["id"], r["batch_id"], json.dumps(r["raw_data"]),
                    json.dumps(r["partial_clean"]) if r.get("partial_clean") else None,
                    r["confidence_score"], json.dumps(r.get("flags", [])),
                    r["status"], r["reviewed_by"], r["created_at"]
                ))
            conn.commit()

    def insert_cleaning_report(self, r):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO cleaning_reports (
                    id, batch_id, total_records, structured_count, quarantined_count,
                    flagged_count, dropped_count, avg_confidence, duplicate_count,
                    processing_time_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r["id"], r["batch_id"], r["total_records"], r["structured_count"],
                r["quarantined_count"], r["flagged_count"], r["dropped_count"],
                r["avg_confidence"], r["duplicate_count"], r["processing_time_ms"], r["created_at"]
            ))
            conn.commit()

    def get_records(self, table_name, batch_id=None):
        with self._get_conn() as conn:
            query = f"SELECT * FROM {table_name}"
            params = []
            if batch_id:
                query += " WHERE batch_id = ?"
                params.append(batch_id)
            query += " ORDER BY created_at DESC"
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                d = dict(row)
                # Parse json fields
                if "raw_data" in d and d["raw_data"]:
                    d["raw_data"] = json.loads(d["raw_data"])
                if "partial_clean" in d and d["partial_clean"]:
                    d["partial_clean"] = json.loads(d["partial_clean"])
                if "flags" in d and d["flags"]:
                    d["flags"] = json.loads(d["flags"])
                if "priority_flag" in d:
                    d["priority_flag"] = bool(d["priority_flag"])
                result.append(d)
            return result

    def update_record_status(self, table_name, record_id, status, reviewed_by="human"):
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE {table_name} SET status = ?, reviewed_by = ? WHERE id = ?",
                (status, reviewed_by, record_id)
            )
            conn.commit()

    def get_record_by_id(self, table_name, record_id):
        with self._get_conn() as conn:
            cursor = conn.execute(f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            if "raw_data" in d and d["raw_data"]:
                d["raw_data"] = json.loads(d["raw_data"])
            if "partial_clean" in d and d["partial_clean"]:
                d["partial_clean"] = json.loads(d["partial_clean"])
            if "flags" in d and d["flags"]:
                d["flags"] = json.loads(d["flags"])
            if "priority_flag" in d:
                d["priority_flag"] = bool(d["priority_flag"])
            return d

    def get_reports(self):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM cleaning_reports ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def insert_sewer_infrastructure(self, records):
        with self._get_conn() as conn:
            for r in records:
                conn.execute("""
                    INSERT OR REPLACE INTO sewer_infrastructure (
                        id, ward_name, avg_sewer_age_years, tree_count, 
                        population_density, restaurant_count, pipe_diameter_mm,
                        installation_method, pipe_length_m, pipe_depth_m, 
                        connections_count, sensor_latitude, sensor_longitude
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.get("id") or str(uuid.uuid4()), r["ward_name"], 
                    r["avg_sewer_age_years"], r["tree_count"],
                    r["population_density"], r["restaurant_count"], r["pipe_diameter_mm"],
                    r["installation_method"], r["pipe_length_m"], r["pipe_depth_m"],
                    r["connections_count"], r["sensor_latitude"], r["sensor_longitude"]
                ))
            conn.commit()

    def get_sewer_infrastructure(self):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM sewer_infrastructure ORDER BY ward_name ASC")
            return [dict(row) for row in cursor.fetchall()]


# Choose DB strategy
use_supabase = False
supabase_client = None

# Sanitize SUPABASE_URL to prevent double path errors (e.g., /rest/v1/rest/v1/)
sanitized_url = SUPABASE_URL
if sanitized_url:
    sanitized_url = sanitized_url.strip()
    if sanitized_url.endswith("/"):
        sanitized_url = sanitized_url[:-1]
    if sanitized_url.endswith("/rest/v1"):
        sanitized_url = sanitized_url[:-8]
    if sanitized_url.endswith("/"):
        sanitized_url = sanitized_url[:-1]

if sanitized_url and SUPABASE_KEY and "your_supabase" not in sanitized_url:
    print(f"[DB] Performing reachability pre-check for Supabase at: {sanitized_url}")
    import urllib.request
    try:
        # Supabase projects return 200 JSON at /rest/v1/ with proper api key header
        test_url = f"{sanitized_url}/rest/v1/"
        req = urllib.request.Request(
            test_url,
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        )
        # Fast 2-second timeout to avoid blocking the event loop on startup
        with urllib.request.urlopen(req, timeout=2.0) as response:
            if response.status in (200, 201, 204):
                supabase_client = create_client(sanitized_url, SUPABASE_KEY)
                use_supabase = True
                print(f"[DB] Successfully connected to Supabase at {sanitized_url}")
            else:
                print(f"[DB] Supabase ping returned unexpected status {response.status}. Falling back to SQLite.")
    except Exception as e:
        print(f"[DB] Supabase connection check failed (host offline or timeout): {e}. Falling back to SQLite immediately.")

db = SQLiteFallback()

class DBWrapper:
    """
    Wrapper class to transparently delegate calls to Supabase or SQLite fallback.
    """
    @staticmethod
    def insert_raw_records(records):
        if use_supabase:
            try:
                # Format for Supabase
                supabase_client.table("raw_records").insert(records).execute()
                return
            except Exception as e:
                print(f"[Supabase Error] Ingest failed: {e}. Writing to SQLite fallback.")
        db.insert_raw_records(records)

    @staticmethod
    def insert_structured_records(records):
        if use_supabase:
            try:
                supabase_client.table("structured_records").insert(records).execute()
                return
            except Exception as e:
                print(f"[Supabase Error] Structured insert failed: {e}")
        db.insert_structured_records(records)

    @staticmethod
    def insert_quarantine_records(records):
        if use_supabase:
            try:
                # Adjust format slightly if needed
                formatted = []
                for r in records:
                    formatted.append({
                        **r,
                        "priority_flag": r["priority_flag"]
                    })
                supabase_client.table("quarantine_records").insert(formatted).execute()
                return
            except Exception as e:
                print(f"[Supabase Error] Quarantine insert failed: {e}")
        db.insert_quarantine_records(records)

    @staticmethod
    def insert_flagged_records(records):
        if use_supabase:
            try:
                supabase_client.table("flagged_records").insert(records).execute()
                return
            except Exception as e:
                print(f"[Supabase Error] Flagged insert failed: {e}")
        db.insert_flagged_records(records)

    @staticmethod
    def insert_cleaning_report(report):
        if use_supabase:
            try:
                supabase_client.table("cleaning_reports").insert(report).execute()
                return
            except Exception as e:
                print(f"[Supabase Error] Report insert failed: {e}")
        db.insert_cleaning_report(report)

    @staticmethod
    def get_records(table_name, batch_id=None):
        if use_supabase:
            try:
                q = supabase_client.table(table_name).select("*")
                if batch_id:
                    q = q.eq("batch_id", batch_id)
                res = q.order("created_at", desc=True).execute()
                if res and hasattr(res, 'data') and res.data is not None:
                    return res.data
            except Exception as e:
                print(f"[Supabase Error] Fetch records failed: {e}")
        return db.get_records(table_name, batch_id)

    @staticmethod
    def get_record_by_id(table_name, record_id):
        if use_supabase:
            try:
                res = supabase_client.table(table_name).select("*").eq("id", record_id).execute()
                if res and hasattr(res, 'data') and res.data:
                    return res.data[0]
            except Exception as e:
                print(f"[Supabase Error] Fetch record by ID failed: {e}")
        return db.get_record_by_id(table_name, record_id)

    @staticmethod
    def update_record_status(table_name, record_id, status, reviewed_by="human"):
        if use_supabase:
            try:
                supabase_client.table(table_name).update({
                    "status": status,
                    "reviewed_by": reviewed_by
                }).eq("id", record_id).execute()
                return
            except Exception as e:
                print(f"[Supabase Error] Update status failed: {e}")
        db.update_record_status(table_name, record_id, status, reviewed_by)

    @staticmethod
    def get_reports():
        if use_supabase:
            try:
                res = supabase_client.table("cleaning_reports").select("*").order("created_at", desc=True).execute()
                if res and hasattr(res, 'data') and res.data is not None:
                    return res.data
            except Exception as e:
                print(f"[Supabase Error] Fetch reports failed: {e}")
        return db.get_reports()

    @staticmethod
    def insert_sewer_infrastructure(records):
        if use_supabase:
            try:
                supabase_client.table("sewer_infrastructure").upsert(records).execute()
                return
            except Exception as e:
                print(f"[Supabase Error] Upsert infrastructure failed: {e}")
        db.insert_sewer_infrastructure(records)

    @staticmethod
    def get_sewer_infrastructure():
        if use_supabase:
            try:
                res = supabase_client.table("sewer_infrastructure").select("*").order("ward_name", desc=False).execute()
                if res and hasattr(res, 'data') and res.data is not None:
                    return res.data
            except Exception as e:
                print(f"[Supabase Error] Fetch infrastructure failed: {e}")
        return db.get_sewer_infrastructure()
