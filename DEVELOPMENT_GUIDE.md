# UrbanFix 311 — Complete System Architecture & Development Guide

Welcome to the **UrbanFix 311** developer documentation. This document provides a complete guide to the system, detailing its purpose, architecture, technical stack, ingestion and analytics pipelines, database schemas, and setup instructions. It is designed to get any new developer or stakeholder fully aligned with how the system was built and how it can be extended.

---

## 1. System Overview & Purpose

**UrbanFix 311** is an AI-powered municipal intelligence platform designed for city engineers and operations managers at the **Ahmedabad Municipal Corporation (AMC)**. The platform solves a critical challenge: processing, organizing, and analyzing unstructured, multilingual public service complaints (311 reports) and combining them with live IoT telemetry and environmental data to guide sewage desilting operations and infrastructure maintenance.

### Core Problems Addressed:
1. **Messy & Multilingual Data**: Public complaints are submitted via various channels (phone calls, mobile apps, emails) in mixed languages (Gujarati, Hindi, English) with frequent misspellings, missing coordinates, and incomplete details.
2. **Duplicate Reports**: Multiple citizens often report the same issue (e.g., a major sewer overflow on a busy road), leading to duplicate resource dispatching.
3. **Reactive vs. Proactive Maintenance**: Municipal crews historically respond to failures after they occur, rather than predicting which sewer segments are at risk of structural collapse or major blockage.
4. **CORS and API Rate Limiting**: Browser-side GIS rendering of street networks via public APIs is highly unreliable, subject to strict rate limits and network latency.

---

## 2. Technical Stack

The application is built on a split client-server architecture designed for high performance, ease of local development, and rapid cloud deployment.

### Frontend (Client)
- **Framework**: React 19 (JavaScript ES6 modules)
- **Build Tool**: Vite 8.0
- **GIS Mapping Engine**: Leaflet 1.9 & React-Leaflet 5.0 (Light Matter CARTO basemaps)
- **Telemetry Charts**: Recharts 3.8 (Custom responsive line, bar, and area charts)
- **Styling**: Vanilla CSS + PostCSS + Tailwind CSS v4 (Pure white theme compliance)
- **HTTP Client**: Axios 1.16
- **Iconography**: Lucide React

### Backend (Server)
- **Framework**: Python 3.10+ with FastAPI 1.0 & Uvicorn (Fully async routing, auto-generated Swagger documentation at `/docs`)
- **Data Science & ML Engine**: 
  - `scikit-learn` (DBSCAN for spatial clustering, LinearRegression for localized models)
  - `scipy.stats` (For Student's t-distribution coefficient p-values and F-statistic calculations)
  - `numpy` & `pandas` (Matrix operations and data wrangling)
- **LLM AI Integration**: Groq SDK client querying LLaMA-3.3-70B-Versatile (for complaint records cleaning, category parsing, deduplication, and conversational advice)
- **Database Layer**: Dual-mode storage client:
  - **SQLite** (Local fallback file `urbanfix_311.db` for instant zero-config development)
  - **Supabase / PostgreSQL** (Cloud production instance)

---

## 3. High-Level Architecture & Data Flow

Below is the diagram showcasing how data flows through the UrbanFix 311 ecosystem, from raw CSV files to cleaned GIS displays and predictive planning reports:

```
[Messy 311 CSV Files] OR [Faker Mock Data]
        │
        ▼
┌─────────────────────────────────────────┐
│     AI Cleaning & Ingestion Pipeline    │
│  (1. Save Raw ──► 2. LLM Parse & Clean) │
│                     │                   │
│                     ▼                   │
│         (3. Duplicate Detection)        │
│                     │                   │
│                     ▼                   │
│        (4. Routing & Classification)    │
└─────────────────────┬───────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  (Conf >= 0.85)  (0.50-0.84)   (Conf < 0.50)
  [Structured]    [Flagged]     [Quarantine]
        │             │             │
        │             └──────┬──────┘
        │                    ▼
        │          ┌───────────────────┐
        │          │ Human Admin UI    │
        │          │ (Approve / Edit)  │
        │          └─────────┬─────────┘
        ▼                    ▼
┌─────────────────────────────────────────┐
│        SQLite / Supabase Database       │
└────────────────────┬────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│  Spatial DBSCAN  │   │  OLS & GWR GIST  │
│  Clustering      │   │  Regression Math │
└────────┬─────────┘   └─────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
┌─────────────────────────────────────────┐
│          Natural Language AI            │
│       Municipal Advisory Briefing       │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│         Vite / React GIS Client         │
│ (Layer 1 Wards ──► Layer 2 Streets Map) │
└─────────────────────────────────────────┘
```

---

## 4. In-Depth Feature Breakdown & Code Paths

### A. The 7-Step AI Cleaning Ingestion Pipeline
Implemented in [ai_pipeline.py](file:///c:/Users/vsoha/Desktop/Work/urbanfix/311/server/services/ai_pipeline.py), this module processes uploaded rows using LLaMA 3.3. When a CSV or batch of mock data is submitted to `POST /upload/csv` or `POST /upload/csv/merge`, the following steps run:

1. **Raw Storage Logging**: The raw dictionary payload is immediately archived in the database with a unique `batch_id`.
2. **Ward Name Standardization**: Corrects misspellings (e.g., "Paldy" -> "Paldi", "Bapu Nagar" -> "Bapunagar") by comparing the parsed input against a master geographic list of Ahmedabad's 48 sewage wards.
3. **Semantic Category Parsing**: Maps unstructured complaints into structured categories: `Sewer & Drainage`, `Roads & Potholes`, `Water Supply`, or `Garbage & Waste`.
4. **Deduplication Check**: Computes similarity scores using a Gestalt pattern matching algorithm on description fields. If a complaint is identical to another record in the same ward and phone number context, it is flagged as a duplicate.
5. **Geocoding Coordinate Assignment**: Matches description cues to coordinates, mapping the issue to the nearest historical cluster centroid or ward centroid.
6. **Phone & Pincode Normalization**: Standardizes contact numbers into a standard format and parses pincodes.
7. **Routing & Confidence Scoring**: Calculates a confidence index ($0.0 \le C \le 1.0$) based on LLM outputs and duplication flags. The record is routed based on this score:
   - **$C \ge 0.85$**: Promoted directly to `structured_records` for immediate dispatch.
   - **$0.50 \le C \le 0.84$**: Routed to `flagged_records` for administrator verification.
   - **$C < 0.50$**: Routed to `quarantine_records` for extensive manual repair.

### B. Human Moderation & Promotion Workflow
Implemented in [review.py](file:///c:/Users/vsoha/Desktop/Work/urbanfix/311/server/routes/review.py), this provides human-in-the-loop validation:
- **Flagged & Quarantine Review**: Administrators view reports matching pending statuses.
- **Correction Editing**: Admins can edit fields (e.g., category, severity, description, coordinates) prior to resolving.
- **Approval & Rejection**: Approving a record generates a new `structured_records` row and updates the source record's status to `approved`. Rejection archives the record as `rejected`, excluding it from downstream analytics.

### C. Spatial Predictive Modeling Engine
Implemented in [predictive_engine.py](file:///c:/Users/vsoha/Desktop/Work/urbanfix/311/server/services/predictive_engine.py), the predictive engine executes three mathematical modeling operations:

#### 1. DBSCAN Spatial Hotspot Clustering
Groups complaint coordinates to identify physical failure hotspots:
- Samples all longitude/latitude pairs from structured complaints.
- Runs DBSCAN with customizable epsilon radius ($\epsilon$, defaults to $0.015^\circ$) and minimum density criteria ($MinPts$, defaults to 3).
- Outputs centroids and counts of complaints, which the GIS map renders as pulsing blue clusters.

#### 2. Global Ordinary Least Squares (OLS) Regression
Identifies macroscopic infrastructure indicators driving sewer blockage frequencies. The math calculates regression coefficients using:
\[\text{Blockages} = \beta_0 + \beta_1 \cdot \text{SewerAge} + \beta_2 \cdot \text{TreeRoots} + \beta_3 \cdot \text{Connections} + \beta_4 \cdot \text{PopDensity} + \beta_5 \cdot \text{PipeDiameter} + \epsilon\]

The standard errors, t-statistics, p-values (via Student's t-distribution), and model R-squared validation are calculated analytically in pure Python:
- **R-Squared ($R^2$)**: Represents the percentage of variance explained by environmental features.
- **p-value Significance ($p < 0.05$)**: Confirms if predictors like tree root counts or connection densities are statistically significant drivers of blockage events.

#### 3. Localized Geographically Weighted Regression (GWR)
Since municipal indicators behave differently across different regions (e.g., tree roots affect suburban pipes more, whereas high household connections affect crowded inner-city pipes), the engine performs localized weighted regressions for each of the 48 wards.
For a target ward, it calculates a spatial weight matrix using a Gaussian distance-decay kernel:
\[w_{ij} = \exp\left(-\frac{1}{2} \left(\frac{d_{ij}}{b}\right)^2\right)\]
- \(d_{ij}\): Euclidean distance between target ward \(i\) and observation ward \(j\).
- \(b\): Spatial kernel bandwidth (defaults to $0.08^\circ$).
- Fits a localized linear regression model for each ward using these weights, outputting ward-specific coefficients and a localized risk percentage (0-100%).

### D. Layer 2 GIS Map & Server-Side OSM Street Engine
Located in [iot.py](file:///c:/Users/vsoha/Desktop/Work/urbanfix/311/server/routes/iot.py) and [Dashboard.jsx](file:///c:/Users/vsoha/Desktop/Work/urbanfix/311/client/src/components/Dashboard.jsx), this houses the mapping layers:

1. **Layer 1 (City-Wide Overview)**: Renders the 48 ward boundaries as KML-derived GeoJSON polygons, colored on a scale from light yellow (low risk) to dark red (critical risk) based on the GWR localized risk scores.
2. **Layer 2 (Explore Street-Level View)**: Renders the selected ward's actual streets, complaint pins, and IoT sewer flow sensors.

#### The Server-Side OSM Engine Design:
To make street fetching 100% reliable, we implemented the following server-side architecture:
* **Multi-Mirror API Failover**: When a ward is selected, the server makes a POST interpreter call. If the primary Overpass server fails (e.g., HTTP 504 Gateway Timeout), it immediately cycles through backup mirrors:
  1. `https://overpass-api.de/api/interpreter` (Main)
  2. `https://lz4.overpass-api.de/api/interpreter` (Backup)
  3. `https://z.overpass-api.de/api/interpreter` (Backup)
  4. `https://overpass.kumi.systems/api/interpreter` (Mirror)
  5. `https://overpass.nchc.org.tw/api/interpreter` (Mirror)
* **Persistent Disk JSON Cache**: Fetched OSM street data is written to disk at `server/data/osm_cache/{normalized_ward_name}.json`. Subsequent requests load the streets in under a millisecond, completely bypassing public network requests.
* **Organic Proximity Fallback**: If all external OSM mirrors fail, the engine triggers a realistic synthetic street generator. It samples coordinates inside the ward's actual KML boundary using a Ray-Casting algorithm, builds a network using a distance-limited proximity graph, adds organic wobbles, and assigns realistic Indian street names (e.g., "Subhash Avenue", "Bose Marg") deterministically.

---

## 5. Database Schema & Data Models

### A. Raw Records (`raw_records`)
Stores the original, unmodified uploads.
```sql
CREATE TABLE raw_records (
    id TEXT PRIMARY KEY,       -- UUID
    batch_id TEXT,             -- UUID identifying the ingestion batch
    raw_data TEXT,             -- JSON string of original CSV row key-values
    created_at TEXT            -- ISO 8601 Timestamp
);
```

### B. Structured Records (`structured_records`)
Stores fully cleaned, geocoded, and validated reports.
```sql
CREATE TABLE structured_records (
    id TEXT PRIMARY KEY,
    batch_id TEXT,
    complaint_id TEXT,
    ward_name TEXT,
    complaint_category TEXT,   -- Sewer & Drainage, Roads & Potholes, Water Supply, Garbage & Waste
    severity TEXT,             -- Low, Medium, High
    description TEXT,
    language TEXT,
    lat REAL,
    lng REAL,
    phone TEXT,
    postal_code TEXT,
    date_filed TEXT,
    confidence_score REAL,
    created_at TEXT
);
```

### C. Quarantine Records (`quarantine_records`)
Stores reports with confidence scores below 0.50, awaiting human moderation.
```sql
CREATE TABLE quarantine_records (
    id TEXT PRIMARY KEY,
    batch_id TEXT,
    raw_data TEXT,
    partial_clean TEXT,        -- JSON string of partial fields extracted by LLM
    reason_code TEXT,          -- Reason for quarantine (e.g. ERR_MISSING_DETAILS)
    priority_flag INTEGER,     -- 1 for high severity, 0 otherwise
    confidence_score REAL,
    status TEXT,               -- pending, approved, rejected
    reviewed_by TEXT,
    created_at TEXT
);
```

### D. Flagged Records (`flagged_records`)
Stores reports with confidence scores between 0.50 and 0.84 (often containing duplicate flags).
```sql
CREATE TABLE flagged_records (
    id TEXT PRIMARY KEY,
    batch_id TEXT,
    raw_data TEXT,
    partial_clean TEXT,
    confidence_score REAL,
    flags TEXT,                -- JSON array of flags (e.g. ["duplicate_record"])
    status TEXT,
    reviewed_by TEXT,
    created_at TEXT
);
```

### E. Sewer Infrastructure (`sewer_infrastructure`)
Maintains environmental predictors used by the regression formulas. Seeded on server startup.
```sql
CREATE TABLE sewer_infrastructure (
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
    created_at TEXT
);
```

---

## 6. Local Setup & Startup Guide

### Prerequisites
- **Python 3.10+** (with pip)
- **Node.js 16+** (with npm)
- A **Groq API Key** (for LLaMA 3.3 pipeline and chatbot)

### Step 1: Clone the Repository & Configure Environment
Create a `.env` file in the `server/` directory (or workspace root):
```env
# Groq credentials for LLM pipeline & chat advisor
GROQ_API_KEY=gsk_your_actual_groq_api_key

# Supabase details (Optional. If omitted, server defaults to SQLite fallback db)
SUPABASE_URL=
SUPABASE_KEY=
```

### Step 2: Set Up the Backend Server
Navigate to the server directory, set up a virtual environment, install requirements, and run the FastAPI server:

```bash
cd server
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python main.py
```
*The backend API will start at [http://127.0.0.1:8000](http://127.0.0.1:8000). You can explore the interactive API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

### Step 3: Set Up the Frontend Client
Navigate to the client directory, install the Node packages, and start the development server:

```bash
cd client
npm install
npm run dev
```
*The frontend development server will launch at [http://localhost:5173/](http://localhost:5173/). Vite is configured via `.env.development` to auto-route API calls to the local Python backend port.*

---

## 7. Verification & Developer Scripts

The repository includes helper scripts inside the `scratch/` folder to verify the analytical engines:
- **`test_osm_streets.py`**: Queries the backend `/iot/ward-streets/{ward}` endpoint for key wards (Paldi, Bapunagar, Navrangpura, Ghatlodia, Bodakdev), testing mirror failovers and verifying JSON disk caching.
- **`test_synthetic.py`**: Runs the Ray-Casting algorithm and proximity-based grid generator independently to verify fallback calculations.
- **`test_predictive_api.py`**: Invokes the regression mathematical equations and DBSCAN spatial coordinates directly.
