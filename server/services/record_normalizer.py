from typing import Dict, Iterable, List, Optional


FIELD_ALIASES = {
    "Complaint ID": ["Complaint ID", "complaint_id", "complaint_ref", "ticket_id", "reference_id"],
    "Date": ["Date", "date", "report_date", "reported_at", "created_at"],
    "Ward/Area": ["Ward/Area", "ward", "ward_name", "area", "location", "zone"],
    "Complaint Details": ["Complaint Details", "description", "issue_description", "complaint", "details"],
    "Reporter Phone": ["Reporter Phone", "phone", "contact_number", "mobile", "reporter_phone"],
    "Pincode": ["Pincode", "pincode", "postal", "postal_code", "zip_code"],
    "Latitude": ["Latitude", "lat", "coords_lat", "latitude"],
    "Longitude": ["Longitude", "lng", "lon", "long", "coords_long", "longitude"],
    "Reporter Name": ["Reporter Name", "person", "name", "reporter_name"],
    "Extra Notes": ["Extra Notes", "notes", "remark", "remarks", "comment"],
}


def _clean_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _first_present(record: Dict[str, object], aliases: Iterable[str]) -> str:
    for key in aliases:
        value = _clean_text(record.get(key))
        if value:
            return value
    return ""


def normalize_record(record: Dict[str, object]) -> Dict[str, object]:
    normalized = dict(record)

    for canonical_name, aliases in FIELD_ALIASES.items():
        normalized[canonical_name] = _first_present(record, aliases)

    details = normalized["Complaint Details"]
    notes = normalized["Extra Notes"]
    if details and notes and notes.lower() not in details.lower():
        separator = " " if details.endswith((".", "!", "?")) else ". "
        normalized["Complaint Details"] = f"{details}{separator}{notes}"
    elif notes and not details:
        normalized["Complaint Details"] = notes

    return normalized


def normalize_records(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [normalize_record(record) for record in records]
