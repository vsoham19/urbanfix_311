import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from services.supabase_client import DBWrapper

router = APIRouter(prefix="/review", tags=["Review"])

class ReviewActionPayload(BaseModel):
    record_id: str
    source_table: str  # "quarantine_records" or "flagged_records"
    action: str  # "approve" or "reject"
    reviewer: Optional[str] = "Human Admin"
    edited_data: Optional[Dict[str, Any]] = None  # If the human corrected any values

@router.post("/submit")
async def submit_review_action(payload: ReviewActionPayload):
    """
    Submits a human review decision (approve/reject) on a quarantined or flagged record.
    If approved, the record is promoted to the structured_records table.
    """
    record_id = payload.record_id
    table = payload.source_table
    action = payload.action.lower()
    
    if table not in ["quarantine_records", "flagged_records"]:
        raise HTTPException(status_code=400, detail="Invalid source table.")
        
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    # 1. Fetch the record from the database
    record = DBWrapper.get_record_by_id(table, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
        
    if record.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Record is already reviewed and set to {record.get('status')}.")

    # 2. Process Approval
    if action == "approve":
        # Determine the cleaned data structure to insert into structured_records.
        # If user provided corrected/edited data, use it. Otherwise, fallback to AI's partial clean output,
        # or construct it from raw data.
        partial_clean = record.get("partial_clean") or {}
        
        # Merge edits if supplied
        if payload.edited_data:
            for k, v in payload.edited_data.items():
                partial_clean[k] = v

        # Construct final structured record
        structured_record = {
            "id": str(uuid.uuid4()),
            "batch_id": record["batch_id"],
            "complaint_id": partial_clean.get("complaint_id") or record["raw_data"].get("Complaint ID"),
            "ward_name": partial_clean.get("ward_name"),
            "complaint_category": partial_clean.get("complaint_category") or "Other",
            "severity": partial_clean.get("severity") or "Medium",
            "description": partial_clean.get("description") or record["raw_data"].get("Complaint Details", ""),
            "language": partial_clean.get("language") or "English",
            "lat": partial_clean.get("lat") or 23.0225,
            "lng": partial_clean.get("lng") or 72.5714,
            "phone": partial_clean.get("phone") or record["raw_data"].get("Reporter Phone"),
            "postal_code": partial_clean.get("postal_code") or record["raw_data"].get("Pincode"),
            # Ensure proper datetime parsing if needed
            "date_filed": partial_clean.get("date_filed") or datetime.now().isoformat(),
            "confidence_score": 1.0,  # Promoted by human, confidence is now 1.0
            "created_at": datetime.now().isoformat()
        }
        
        # Insert into structured table
        DBWrapper.insert_structured_records([structured_record])
        
        # Update status to approved
        DBWrapper.update_record_status(table, record_id, "approved", payload.reviewer)
        
        return {"status": "success", "message": "Record approved and promoted to structured database.", "record": structured_record}

    else:
        # Process Rejection
        DBWrapper.update_record_status(table, record_id, "rejected", payload.reviewer)
        return {"status": "success", "message": "Record rejected and excluded from structured database."}
