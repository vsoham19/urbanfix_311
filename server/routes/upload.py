import csv
import io
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from generators.mock_data import generate_dirty_csv_data
from services.ai_pipeline import run_ai_cleaning_pipeline
from services.record_normalizer import normalize_records
from typing import List

router = APIRouter(prefix="/upload", tags=["Upload"])

@router.post("/csv")
async def upload_csv_file(file: UploadFile = File(...)):
    """
    Uploads a raw, unstructured 311 CSV file, parses it, and runs the AI Cleaning Pipeline.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    try:
        contents = await file.read()
        decoded = contents.decode('utf-8')
        csv_file = io.StringIO(decoded)

        # Parse CSV
        reader = csv.DictReader(csv_file)
        raw_records = normalize_records([row for row in reader])

        if not raw_records:
            raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")

        # Run AI Cleaning pipeline
        results = run_ai_cleaning_pipeline(raw_records)
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")

@router.post("/csv/merge")
async def merge_csv_files(
    files: List[UploadFile] = File(...),
    merge_option: str = Query("latest", description="Merge option: 'latest', 'previous', or 'both'")
):
    """
    Merges multiple CSV files and runs the AI Cleaning Pipeline.

    merge_option:
    - 'latest': Use only the most recent file
    - 'previous': Use only the previous file (if available, otherwise latest)
    - 'both': Combine all files
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one CSV file is required.")

    valid_options = ['latest', 'previous', 'both']
    if merge_option not in valid_options:
        raise HTTPException(status_code=400, detail=f"merge_option must be one of: {', '.join(valid_options)}")

    try:
        all_records = []

        # Parse all uploaded files
        for file in files:
            if not file.filename.endswith('.csv'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a CSV file.")

            contents = await file.read()
            decoded = contents.decode('utf-8')
            csv_file = io.StringIO(decoded)

            reader = csv.DictReader(csv_file)
            records = normalize_records([row for row in reader])
            all_records.extend(records)

        # Apply merge option logic
        if merge_option == 'latest':
            # Use only the last file (most recent)
            file_record_count = len(all_records) // len(files)
            raw_records = all_records[-file_record_count:] if file_record_count > 0 else all_records
        elif merge_option == 'previous':
            # Use only the first file (previous)
            file_record_count = len(all_records) // len(files)
            raw_records = all_records[:file_record_count] if file_record_count > 0 else all_records
        else:  # 'both' or any other value defaults to combining all
            # Combine all records
            raw_records = all_records

        if not raw_records:
            raise HTTPException(status_code=400, detail="No records found after processing CSV files.")

        # Run AI Cleaning pipeline
        results = run_ai_cleaning_pipeline(raw_records)
        results['merge_info'] = {
            'merge_option': merge_option,
            'total_files': len(files),
            'total_records_merged': len(raw_records)
        }
        return results

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to merge and process CSV files: {str(e)}")

@router.post("/generate-mock")
async def generate_and_process_mock_data(num_rows: int = 50):
    """
    Generates a set of dirty 311 complaints using Faker and automatically
    runs them through the AI Cleaning Pipeline. Great for demo/testing.
    """
    try:
        csv_data = generate_dirty_csv_data(num_rows)
        csv_file = io.StringIO(csv_data)
        
        reader = csv.DictReader(csv_file)
        raw_records = normalize_records([row for row in reader])
        
        results = run_ai_cleaning_pipeline(raw_records)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate and clean mock data: {str(e)}")
