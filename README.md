# UrbanFix 311 — Project Summary

A compact web application and backend for ingesting, reviewing, and predicting sewer/drainage-related 311 reports. This repository contains tools to generate mock IoT data, APIs to upload and review records, a predictive pipeline, and a Vite/React client for monitoring and interacting with records.

## Key Features
- Ingest CSV/KML datasets and mock IoT streams
- Web UI for uploading and reviewing reports (Vite + React)
- Backend API (Python FastAPI/Flask-style routes) for records, review, predictive endpoints
- Predictive engine and AI pipeline for labeling and scoring records
- Utilities to normalize records and integrate with Supabase/GROQ

## Repository Layout
- `client/` — Frontend (Vite + React). Main entry: `client/src/main.jsx` and components in `client/src/components/`.
- `server/` — Backend Python app. Entry: `server/main.py`. Routes live in `server/routes/`.
- `server/models/` — Pydantic schemas and model definitions.
- `server/services/` — Business logic: AI pipeline, predictive engine, DB clients.
- `server/generators/` — Scripts to create mock data and IoT streams.
- `server/requirements.txt` — Python dependencies.
- CSV/KML sample data at repo root: `sewer_drainage_311.csv`, `urbanfix_mock_311.csv`, `ahmedabad_wards_map_2024.kml`.

## Quickstart

Prerequisites:
- Python 3.10+ and pip
- Node 16+ / npm or Yarn

Backend (server):

1. Create and activate a Python environment (optional but recommended).
2. Install dependencies:

```bash
cd server
pip install -r requirements.txt
```

3. Run the backend API (example):

```bash
python main.py
```

Frontend (client):

1. Install Node dependencies and run dev server:

```bash
cd client
npm install
npm run dev
```

Open the client at the URL printed by Vite (usually `http://localhost:5173`). The frontend communicates with the backend routes under `server/routes/`.

## Important Files & Endpoints
- `server/routes/upload.py` — endpoints for uploading records and files.
- `server/routes/review.py` — review workflow and moderation endpoints.
- `server/routes/predictive.py` — prediction API used by UI and pipelines.
- `server/services/predictive_engine.py` — core prediction logic and model orchestration.
- `client/src/components/Upload.jsx`, `Review.jsx`, `Dashboard.jsx` — main UI flows.

## Data & Generators
- `server/generators/mock_data.py` and `iot_sewer_data.py` produce synthetic records for testing and development.
- Use provided CSV files for quick import and verification.

## Development Notes
- The project includes an AI pipeline (`server/services/ai_pipeline.py`) and utilities for normalizing and preparing records before storage.
- Integration helpers for Supabase and GROQ are in `server/services/` for easy data storage and queries.

## Contributing
- Follow existing code patterns. Add tests in `server/scratch/` or a new `tests/` folder if needed.
- Run linters and formatters consistent with `client/` and `server/` configurations.

## Contact
If you need help running the project or want features prioritized, open an issue or contact the maintainers.

---
Generated: concise README summarizing repository structure and run instructions.
