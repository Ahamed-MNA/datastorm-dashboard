# 🌩️ Outlet Intelligence Backend API

FastAPI backend server for the **Outlet Intelligence Web App**. Built using FastAPI, SQLAlchemy (SQLite), NumPy, and SciPy, this service is fully isolated and ready to run locally.

---

## 🚀 Key Features

1. **Dashboard Analytics**: Exposes aggregate stats and distribution data for charts.
2. **Outlet Explorer**: Search, filter (by province, distributor), sort (by predicted potential, opportunity gap, growth percentage, allocated budget), and paginate through the full dataset of 19,960 outlets.
3. **Geospatial Metrics**: Detailed proximity and distance-decay POI gravity scores for each outlet.
4. **Interactive Budget Optimization**: Business users can view promotional spend allocations. It also provides a **dynamic optimization engine** that runs the KKT dual-bisection solver in real-time if a custom total budget limit is supplied.
5. **Explainable AI (XAI)**: Generates 3-paragraph executive-grade commercial consultant narratives utilizing Google Gemini or Groq models.

---

## 🛠️ Setup Instructions

### 1. Prerequisites
- **Python**: $\ge 3.11$
- **uv**: Astral's high-performance Python package installer (recommended) or standard `pip`.

### 2. Environment Setup

From the `datastorm-dashboard/backend` directory:

```powershell
# Install dependencies and create isolated virtual environment
uv sync
```

### 3. Initialize & Populate SQLite Database

Run the database ingestion script to load cleaned outlets, transaction aggregations, spatial gravity indices, SFA potential predictions, and budget allocations:

```powershell
# Seeding SQLite database from outputs
uv run python db/ingest_db.py
```

This creates a SQLite database file at `db/database.db`.

### 4. Configure API Keys (for XAI generation)

Create a `.env` file in `datastorm-dashboard/backend` (or reuse the parent root `.env`):

```dotenv
GEMINI_API_KEY=AIza...      # Preferred Google Gemini key
GROQ_API_KEY=gsk_...        # Fallback Groq LLaMA key
```

---

## 🏃 Running the Application

Start the local development server:

```powershell
# Start Uvicorn
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Verification & Testing

Verify that all routers, services, database tables, and the LLM generation are working perfectly by running the in-memory test suite:

```powershell
# Execute API tests
uv run python test_backend.py
```

---

## 📖 API Documentation Reference

For the complete API schemas, JSON examples, request bodies, and database field mappings, please refer to [API_DOCUMENTATION.md](file:///c:/data-storm/datastorm-dashboard/backend/API_DOCUMENTATION.md).

Here is the quick-reference checklist of all 34 active endpoints:

### 📊 Dashboard
- `GET /api/dashboard/summary`: Summary of total outlets, budget allocation, lift, and average efficiency.
- `GET /api/dashboard/distributors`: Detail aggregates grouped by distributor ID.
- `GET /api/dashboard/provinces`: Detail aggregates grouped by province.

### 💰 Budget & Simulation
- `POST /api/budget/simulate`: Re-run KKT optimization dynamically with custom budget, elasticity (b_param), and segment filters (province, outlet type, outlet size).
- `GET /api/budget/outlets`: Detailed spend allocations per outlet.
- `GET /api/budget/distributors`: Distributor-wise spend aggregates, active counts, and average ROI.
- `GET /api/budget/summary`: Overall promotional spend allocation summary.

### 🗺️ Map Layers
- `GET /api/map/heatmap`: Coordinates and weight indices for drawing heatmaps.
- `GET /api/map/competitors`: Competitor connections with coordinates for draw lines.
- `GET /api/map/pois`: Coordinates and POI gravity index scores.
- `GET /api/map/outlets`: Coordinate points and metadata markers for rendering outlet markers.

### 🏪 Outlets
- `GET /api/outlets/{id}/spatial`: Proximity and gravity metrics for a single outlet.
- `GET /api/outlets/{id}/history`: 3-year historical monthly transaction logs.
- `GET /api/outlets/{id}`: Detailed prediction profile for a single outlet.
- `GET /api/outlets/export`: Downloads a generated CSV containing the entire prediction dataset.
- `GET /api/outlets`: Paginated, searchable, and sortable outlet listings.

### 🧠 Explainable AI
- `GET /api/xai/{outlet_id}/explanation`: SFA local driver attributions and 3-paragraph executive narrative.
- `GET /api/xai/{outlet_id}`: Quick fetch of local signals, features, and efficiency.

### 📢 Campaigns
- `GET /api/campaigns`: List all created campaigns (Active/Completed).
- `POST /api/campaigns`: Create a new campaign manually.
- `POST /api/campaigns/create-from-simulation`: Create campaign directly from simulated allocations.
- `GET /api/campaigns/{id}`: Get single campaign metadata.
- `POST /api/campaigns/{id}/end`: Terminate active campaign (transitions status to Completed).
- `GET /api/campaigns/{id}/monitoring`: Get weekly snapshots timeline and the composite Campaign Health Score.
- `GET /api/campaigns/{id}/monitoring/{outlet_id}`: Get weekly timeline snapshots for a specific outlet.
- `GET /api/campaigns/{id}/treatment`: Get treatment outlet list with weekly performance data.
- `GET /api/campaigns/{id}/control`: Get matched control outlet list with baseline data.
- `POST /api/campaigns/{id}/evaluate/pre-post`: Post/Initiate pre-post impact evaluation analysis.
- `GET /api/campaigns/{id}/evaluate/pre-post`: Get pre-post evaluation summary.
- `POST /api/campaigns/{id}/evaluate/did`: Post/Initiate Difference-in-Differences evaluation.
- `GET /api/campaigns/{id}/evaluate/did`: Get DiD analysis summary.
- `POST /api/campaigns/{id}/reallocate`: Generate optimized mid-campaign reallocation recommendations.
- `POST /api/campaigns/{id}/reallocate/apply`: Apply budget reallocation recommendations.


