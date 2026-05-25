from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class RawRecordSchema(BaseModel):
    id: Optional[str] = None
    batch_id: str
    raw_data: Dict[str, Any]
    created_at: Optional[datetime] = None

class StructuredRecordSchema(BaseModel):
    id: Optional[str] = None
    batch_id: str
    complaint_id: Optional[str] = None
    ward_name: Optional[str] = None
    complaint_category: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: Optional[str] = None
    postal_code: Optional[str] = None
    date_filed: Optional[datetime] = None
    confidence_score: float
    created_at: Optional[datetime] = None

class QuarantineRecordSchema(BaseModel):
    id: Optional[str] = None
    batch_id: str
    raw_data: Dict[str, Any]
    partial_clean: Optional[Dict[str, Any]] = None
    reason_code: str
    priority_flag: bool = False
    confidence_score: float
    status: str = "pending"  # pending, approved, rejected
    reviewed_by: Optional[str] = None
    created_at: Optional[datetime] = None

class FlaggedRecordSchema(BaseModel):
    id: Optional[str] = None
    batch_id: str
    raw_data: Dict[str, Any]
    partial_clean: Optional[Dict[str, Any]] = None
    confidence_score: float
    flags: List[str] = []
    status: str = "pending"  # pending, approved, rejected
    reviewed_by: Optional[str] = None
    created_at: Optional[datetime] = None

class CleaningReportSchema(BaseModel):
    id: Optional[str] = None
    batch_id: str
    total_records: int
    structured_count: int
    quarantined_count: int
    flagged_count: int
    dropped_count: int
    avg_confidence: float
    duplicate_count: int
    processing_time_ms: int
    created_at: Optional[datetime] = None
