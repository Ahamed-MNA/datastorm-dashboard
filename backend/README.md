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

## 📖 API Documentation Summary

### 📊 Dashboard endpoints
- `GET /api/dashboard/stats`: Returns high-level KPIs (total outlets, budget allocations, lift, efficiency).
- `GET /api/dashboard/charts`: Returns distributor, province, size, and type counts for frontend charts.

### 🏪 Outlets endpoints
- `GET /api/outlets/`: Lists outlets with query param filtering (`province`, `distributor`, `search`), sorting, and pagination.
- `GET /api/outlets/{outlet_id}`: Retrieves profile details, predictions, spatial features, and budget spend for a single outlet.

### 🗺️ Spatial endpoints
- `GET /api/spatial/{outlet_id}`: Retrieves competitor count, POI distances, and category impact scores.
- `GET /api/spatial/summary`: Returns spatial averages across all outlets.

### 💰 Budget & Optimizer endpoints
- `GET /api/budget/`: List allocations.
- `GET /api/budget/summary`: Budget breakdown tables grouped by distributor, size, and type.
- `POST /api/budget/optimize`: Re-runs the dual-bisection solver with a custom promotional budget to return new spend allocations.

### 🧠 Explainable AI endpoints
- `GET /api/xai/{outlet_id}`: Fetches or generates a 3-paragraph business narrative explaining the SFA potential score.
