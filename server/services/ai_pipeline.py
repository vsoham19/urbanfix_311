import uuid
import time
from datetime import datetime
import difflib
from .groq_client import GroqClient
from .supabase_client import DBWrapper

groq_client = GroqClient()

def compute_similarity(str1: str, str2: str) -> float:
    if not str1 or not str2:
        return 0.0
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def run_ai_cleaning_pipeline(raw_records_list: list) -> dict:
    """
    Executes the entire AI Cleaning Pipeline on a list of raw records.
    - Saves raw records.
    - Resolves ward names, category, severity, language, phone, pincode, dates, coordinates.
    - Performs duplicate detection & grouping.
    - Segments into Structured (>= 0.85), Flagged (0.50-0.84), or Quarantine (< 0.50).
    - Logs details to database.
    - Generates a full cleaning report.
    """
    start_time = time.time()
    batch_id = str(uuid.uuid4())
    created_at_str = datetime.now().isoformat()
    
    # 1. Save raw records to DB
    raw_to_insert = []
    for r in raw_records_list:
        raw_to_insert.append({
            "id": str(uuid.uuid4()),
            "batch_id": batch_id,
            "raw_data": r,
            "created_at": created_at_str
        })
    DBWrapper.insert_raw_records(raw_to_insert)

    # 2. Clean each record
    cleaned_records = []
    for raw_item in raw_to_insert:
        cleaned = groq_client.clean_record(raw_item["raw_data"])
        cleaned["raw_record_id"] = raw_item["id"]
        cleaned["raw_data"] = raw_item["raw_data"]
        cleaned_records.append(cleaned)

    # 3. Duplicate Detection & Grouping
    # We group duplicates within the batch.
    # If a record is a duplicate of a previously processed record in this batch, we mark it.
    is_duplicate = [False] * len(cleaned_records)
    duplicate_groups = {}  # primary_id -> list of duplicate_ids
    
    for i in range(len(cleaned_records)):
        if is_duplicate[i]:
            continue
        primary = cleaned_records[i]
        primary_id = primary["raw_record_id"]
        primary_desc = primary.get("description", "")
        primary_ward = primary.get("ward_name", "")
        
        for j in range(i + 1, len(cleaned_records)):
            if is_duplicate[j]:
                continue
            other = cleaned_records[j]
            other_desc = other.get("description", "")
            other_ward = other.get("ward_name", "")
            
            # Check similarity
            sim = compute_similarity(primary_desc, other_desc)
            # If descriptions are highly similar (>0.75) and ward matches
            if sim > 0.75 and primary_ward == other_ward:
                is_duplicate[j] = True
                if primary_id not in duplicate_groups:
                    duplicate_groups[primary_id] = []
                duplicate_groups[primary_id].append(other["raw_record_id"])
                
                # Flag as duplicate
                if "duplicate" not in other["flags"]:
                    other["flags"].append("duplicate")
                # Decrease confidence
                other["confidence_score"] = max(0.1, round(other["confidence_score"] * 0.5, 2))

    # 4. Route records to appropriate tables
    structured_to_insert = []
    quarantine_to_insert = []
    flagged_to_insert = []
    dropped_count = 0
    total_confidence = 0.0
    
    for i, cleaned in enumerate(cleaned_records):
        score = cleaned["confidence_score"]
        total_confidence += score
        
        record_id = str(uuid.uuid4())
        
        # Check routing
        if score >= 0.85:
            # Check if this record is marked as duplicate.
            # If it's a duplicate, we flag it. (Duplicate can go to flagged instead of structured)
            if is_duplicate[i]:
                flagged_to_insert.append({
                    "id": record_id,
                    "batch_id": batch_id,
                    "raw_data": cleaned["raw_data"],
                    "partial_clean": cleaned,
                    "confidence_score": score,
                    "flags": cleaned["flags"] + ["duplicate_record"],
                    "status": "pending",
                    "reviewed_by": None,
                    "created_at": created_at_str
                })
            else:
                structured_to_insert.append({
                    "id": record_id,
                    "batch_id": batch_id,
                    "complaint_id": cleaned.get("complaint_id"),
                    "ward_name": cleaned.get("ward_name"),
                    "complaint_category": cleaned.get("complaint_category"),
                    "severity": cleaned.get("severity"),
                    "description": cleaned.get("description"),
                    "language": cleaned.get("language"),
                    "lat": cleaned.get("lat"),
                    "lng": cleaned.get("lng"),
                    "phone": cleaned.get("phone"),
                    "postal_code": cleaned.get("postal_code"),
                    "date_filed": cleaned.get("date_filed"),
                    "confidence_score": score,
                    "created_at": created_at_str
                })
        elif score < 0.50:
            # Quarantine Table
            # Determine priority flag (High severity gets priority flag)
            priority_flag = cleaned.get("severity") == "High"
            
            quarantine_to_insert.append({
                "id": record_id,
                "batch_id": batch_id,
                "raw_data": cleaned["raw_data"],
                "partial_clean": cleaned,
                "reason_code": cleaned.get("reason_code") or "ERR_LOW_CONFIDENCE",
                "priority_flag": priority_flag,
                "confidence_score": score,
                "status": "pending",
                "reviewed_by": None,
                "created_at": created_at_str
            })
        else:
            # Flagged Table (0.50 - 0.84)
            flagged_to_insert.append({
                "id": record_id,
                "batch_id": batch_id,
                "raw_data": cleaned["raw_data"],
                "partial_clean": cleaned,
                "confidence_score": score,
                "flags": cleaned.get("flags", []),
                "status": "pending",
                "reviewed_by": None,
                "created_at": created_at_str
            })

    # Save outputs
    if structured_to_insert:
        DBWrapper.insert_structured_records(structured_to_insert)
    if quarantine_to_insert:
        DBWrapper.insert_quarantine_records(quarantine_to_insert)
    if flagged_to_insert:
        DBWrapper.insert_flagged_records(flagged_to_insert)

    processing_time = int((time.time() - start_time) * 1000)
    avg_confidence = round(total_confidence / len(cleaned_records), 2) if cleaned_records else 1.0
    duplicate_count = sum(len(v) for v in duplicate_groups.values())

    # Create cleaning report
    report = {
        "id": str(uuid.uuid4()),
        "batch_id": batch_id,
        "total_records": len(raw_records_list),
        "structured_count": len(structured_to_insert),
        "quarantined_count": len(quarantine_to_insert),
        "flagged_count": len(flagged_to_insert),
        "dropped_count": dropped_count,
        "avg_confidence": avg_confidence,
        "duplicate_count": duplicate_count,
        "processing_time_ms": processing_time,
        "created_at": created_at_str
    }
    DBWrapper.insert_cleaning_report(report)

    return {
        "batch_id": batch_id,
        "report": report,
        "structured": structured_to_insert,
        "quarantine": quarantine_to_insert,
        "flagged": flagged_to_insert
    }
