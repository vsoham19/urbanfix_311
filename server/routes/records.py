from fastapi import APIRouter, Query
from typing import Optional
from services.supabase_client import DBWrapper

router = APIRouter(prefix="/records", tags=["Records"])

@router.get("/structured")
async def get_structured_records(batch_id: Optional[str] = Query(None, description="Filter by batch ID")):
    """
    Retrieves all fully cleaned structured records.
    """
    records = DBWrapper.get_records("structured_records", batch_id)
    return records

@router.get("/quarantine")
async def get_quarantine_records(batch_id: Optional[str] = Query(None, description="Filter by batch ID")):
    """
    Retrieves all quarantined records waiting for human review.
    """
    records = DBWrapper.get_records("quarantine_records", batch_id)
    return records

@router.get("/flagged")
async def get_flagged_records(batch_id: Optional[str] = Query(None, description="Filter by batch ID")):
    """
    Retrieves all flagged records waiting for human review.
    """
    records = DBWrapper.get_records("flagged_records", batch_id)
    return records

@router.get("/reports")
async def get_reports():
    """
    Retrieves execution/cleaning reports for all batches.
    """
    reports = DBWrapper.get_reports()
    return reports
