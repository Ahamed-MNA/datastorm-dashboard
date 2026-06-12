# 🌩️ Outlet Intelligence — Web Dashboard

> **Full-stack interactive dashboard** for exploring outlet-level sales predictions, geospatial heatmaps, trade-spend optimisation, and AI-generated narratives.
>
> Built with **React + TypeScript (Vite)** on the frontend and **FastAPI + SQLite** on the backend.

---

## 📑 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [Repository Structure](#-repository-structure)
3. [Prerequisites](#-prerequisites)
4. [Quick Start](#-quick-start)
   - [Step 1 — Environment Variables](#step-1--environment-variables)
   - [Step 2 — Backend](#step-2--backend)
   - [Step 3 — Frontend](#step-3--frontend)
5. [Dashboard Pages & Features](#-dashboard-pages--features)
6. [API Reference](#-api-reference)
7. [Key Dependencies](#-key-dependencies)
8. [Backend Tests](#-backend-tests)
9. [Troubleshooting](#-troubleshooting)

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│   React Frontend                  FastAPI Backend            │
│   (Vite + TanStack Router)        (Python + Uvicorn)         │
│   http://localhost:3000    ◄────► http://localhost:8000      │
│                             REST                             │
│                              API      SQLite Database        │
│                                    (db/database.db)          │
│                                    Pre-seeded from ML        │
│                                    pipeline outputs          │
└──────────────────────────────────────────────────────────────┘
```

The **frontend** is a single-page React app that fetches all data from the backend via a typed API client (`src/lib/api.ts`). The **backend** serves a FastAPI application backed by a SQLite database that is pre-seeded from the ML pipeline Parquet/CSV outputs.

---

## 📁 Repository Structure

```
datastorm-dashboard/
│
├── backend/                          # FastAPI REST API server
│   ├── app/
│   │   ├── main.py                   # FastAPI app entry point + CORS setup
│   │   ├── routers/
│   │   │   ├── dashboard.py          # GET /api/dashboard/*
│   │   │   ├── outlets.py            # GET /api/outlets/*
│   │   │   ├── budget.py             # GET/POST /api/budget/*
│   │   │   ├── map.py                # GET /api/map/*
│   │   │   └── xai.py               # GET /api/xai/*
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic response schemas
│   │   └── services/
│   │       ├── xai_service.py        # LLM narrative orchestration
│   │       ├── optimization_service.py  # KKT dual-bisection solver
│   │       ├── prediction_service.py    # SFA prediction queries
│   │       └── spatial_service.py       # Spatial/POI queries
│   ├── db/
│   │   ├── ingest_db.py              # Seeds SQLite from Parquet/CSV pipeline outputs
│   │   ├── models.py                 # SQLAlchemy ORM table definitions
│   │   ├── database.py               # SQLAlchemy engine config
│   │   ├── session.py                # DB session dependency
│   │   └── database.db               # SQLite database file (auto-created by ingest)
│   ├── pyproject.toml                # Python dependencies
│   ├── test_backend.py               # API integration test suite
│   └── API_DOCUMENTATION.md          # Full endpoint + schema reference
│
└── frontend/                         # React + Vite SPA
    ├── src/
    │   ├── routes/
    │   │   ├── __root.tsx            # Root layout (sidebar + header shell)
    │   │   ├── index.tsx             # / → Executive Dashboard
    │   │   ├── outlets.tsx           # Layout route for outlets
    │   │   ├── outlets.index.tsx     # /outlets → Outlet Explorer
    │   │   ├── outlets.$id.tsx       # /outlets/:id → Outlet Detail
    │   │   ├── map.tsx               # /map → Geospatial Map
    │   │   ├── budget.tsx            # /budget → Trade-Spend Optimiser
    │   │   ├── monitoring.tsx        # /monitoring → Pilot Campaign Monitoring
    │   │   └── evaluation.tsx        # /evaluation → Campaign Evaluation Console
    │   ├── components/
    │   │   ├── app-sidebar.tsx       # Navigation sidebar
    │   │   ├── kpi-card.tsx          # Metric display card
    │   │   ├── metric-tooltip.tsx    # Glossary tooltips
    │   │   └── ui/                   # shadcn/ui component library
    │   ├── lib/
    │   │   ├── api.ts                # Typed fetch client for all endpoints
    │   │   └── format.ts             # Number, currency, percentage formatters
    │   ├── styles.css                # Global Tailwind + CSS variables
    │   └── main.tsx                  # App entry point
    ├── package.json
    ├── vite.config.ts
    └── tsconfig.json
```

---

## ✅ Prerequisites

| Tool | Version | How to install |
|------|---------|----------------|
| **Python** | ≥ 3.11 | [python.org](https://python.org) |
| **uv** | latest | `pip install uv` |
| **Node.js** | ≥ 18 | [nodejs.org](https://nodejs.org) |
| **npm** | ≥ 9 | Bundled with Node.js |

> **Note:** The SQLite database (`backend/db/database.db`) is pre-seeded and ready to use. You do **not** need to run the ML pipeline to use the dashboard.

---

## 🚀 Quick Start

You need **two terminals** running simultaneously — one for the backend, one for the frontend.

### Step 1 — Environment Variables

The XAI (Explainable AI) narrative endpoint requires an LLM API key.
Create a `.env` file at the **project root** (`data-storm/.env`) if one doesn't already exist:

```dotenv
GEMINI_API_KEY=AIza...       # Google Gemini 2.5 Flash (primary — recommended)
GROQ_API_KEY=gsk_...         # Groq LLaMA 3.3 70B (fallback — optional)
```

> All other dashboard features (dashboard, outlets, map, budget) work without any API keys.

---

### Step 2 — Backend

```powershell
# From the datastorm-dashboard/ directory:
cd backend

# Install all Python dependencies into an isolated virtual environment
uv sync

# (First time only) Seed the SQLite database from ML pipeline outputs
# Skip if backend/db/database.db already exists and is non-empty (~28 MB)
uv run python db/ingest_db.py

# Start the FastAPI server with hot reload
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify it's running:

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/ | Health check — returns `{"status": "online"}` |
| http://127.0.0.1:8000/docs | Swagger UI — interactive API explorer |
| http://127.0.0.1:8000/redoc | ReDoc — clean API reference |

---

### Step 3 — Frontend

```powershell
# From the datastorm-dashboard/ directory:
cd frontend

# Install Node.js dependencies (only needed once)
npm install

# Start the Vite development server
npm run dev
```

Open the app: 👉 **[http://localhost:3000](http://localhost:3000)**

> If port 3000 is taken, Vite picks the next available port and prints it to the terminal.

---

### Both Servers at a Glance

| Terminal | Command | URL |
|----------|---------|-----|
| **1 — Backend** | `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` | http://localhost:8000 |
| **2 — Frontend** | `npm run dev` | http://localhost:3000 |

---

## 🖥️ Dashboard Pages & Features

### 📊 Executive Dashboard — `/`

> _"A single view of network performance, latent opportunity, and trade-spend efficiency."_

| Component | Description |
|-----------|-------------|
| **KPI Cards (×6)** | Total Outlets · Active Outlets · Budget Allocated · Expected Lift · Avg ROI · Avg Efficiency Score |
| **Provinces by Opportunity** | Bar chart of total opportunity gap per region (sorted largest first) |
| **Distributors by Opportunity** | Top-10 distributors ranked by aggregated opportunity gap |
| **Provincial Efficiency** | Colour-coded bar chart — green ≥ 60%, amber 40–60%, red < 40% |
| **Top Distributors — Avg Potential** | Horizontal bar chart of average predicted volume per outlet |

---

### 🏪 Outlet Explorer — `/outlets`

> _"Search, filter, and sort across all 19,960 outlets in the network."_

| Feature | Detail |
|---------|--------|
| **Search** | Full-text search by Outlet ID or Outlet Name |
| **Filter** | Province dropdown · Distributor dropdown |
| **Sort** | Any column — ID, Predicted Potential, Opportunity Gap, Growth %, Efficiency Score, Budget |
| **Pagination** | Configurable page size; total count displayed |
| **CSV Export** | Downloads the full prediction dataset as a CSV file |
| **Row click** | Navigates to the individual Outlet Detail page |

---

### 🏪 Outlet Detail — `/outlets/:id`

> _"Deep-dive into a single outlet — predictions, spatial context, history, and AI explanation."_

**Prediction Panel**

| Metric | Description |
|--------|-------------|
| Historical Sales | Actual monthly volume baseline (litres) |
| Predicted Potential | SFA model latent demand ceiling |
| Opportunity Gap | Ceiling minus actual (untapped potential) |
| Growth % | Percentage headroom above current baseline |
| Efficiency Score | Actual ÷ Ceiling — how close to full potential |

**Spatial Features Panel**

Proximity gravity scores for 7 POI categories: School · Hospital · Transit · Religious · Commercial · Residential · Tourism, plus competition density (Market Saturation, Min Competitor Distance, Avg Competitive Friction).

**Budget Allocation**

Allocated promotional spend, expected volume lift, and ROI for this outlet.

**3-Year Sales History Chart**

Monthly volume and bill value from 2023–2025 rendered as an area/line chart.

**🧠 XAI Narrative Panel**

Clicking **"Generate AI Explanation"** calls the `/api/xai/{id}/explanation` endpoint which:
1. Extracts SFA feature attributions and efficiency metrics
2. Sends a structured payload to **Google Gemini 2.5 Flash** (or Groq LLaMA as fallback)
3. Returns a **3-paragraph executive narrative** covering:
   - **The Score** — latent ceiling vs. actual baseline
   - **The Drivers** — geospatial and environmental signals
   - **The Bottlenecks & Action** — operational constraints + spend recommendations

Top feature drivers, local signals, and operational constraints are also displayed in structured tables.

---

### 🗺️ Geospatial Map — `/map`

> _"Visualise outlet density, opportunity hotspots, and POI gravity across the territory."_

Built on **Leaflet + OpenStreetMap** centered on Sri Lanka.

| Layer | Toggle | Description |
|-------|--------|-------------|
| **Outlets** | ✅ On by default | Circle markers sized by Predicted Potential; click for popup with province, distributor, potential, and link to detail page |
| **Opportunity Heatmap** | ✅ On by default | Gaussian density heatmap weighted by Opportunity Gap; gradient from green → amber → orange → dark red |
| **POI Gravity** | Off by default | Amber circles sized by total POI footfall impact score |

---

### 💰 Trade-Spend Optimiser — `/budget`

> _"Inspect the current allocation, run what-if scenarios, and see the recommended split."_

**Current Allocation KPIs**
- Total Budget, Expected Lift, Avg ROI
- Active Outlets count displayed as `funded / eligible` (e.g. `1,981 / 8,989`) with an interactive tooltip explanation.

**What-If Simulator**
- **Multi-Dimensional Filters**: Segment simulations by **Province**, **Outlet Type**, and **Outlet Size** in real-time.
- **Total Budget slider**: Adjusts the promotional budget envelope.
- **Solver elasticity (`b_param`)**: Adjusts optimizer sensitivity (concentration vs spreading).
- **Run Simulation button**: Live backend KKT dual-bisection solver runs with the selected segment constraints.

**Simulation Results**:
- **Key metrics comparison**: Shows the optimized budget split, projected lift, active outlets, and average ROI.
- **Top Allocations Table**: Shows the top 15 outlets receiving budget.
  - **Explainable AI Drilldown**: Click on any **Outlet ID** in this table to open a modal displaying real-time selection drivers: *Potential Gap*, *ROI Score*, *School Gravity*, *Competition*, and an automated text reason for its selection.
- **Spend by Distributor Table**: Full breakdown including total outlets, active outlets, spend share, lift, and ROI.
- **Create Campaign Action**: Once optimized, click **Create Campaign** to transition simulated budgets directly into an active pilot. It asks for a campaign name, sets it to `"Active"`, matches control groups, and seeds weekly performance snapshots.

---

### 📈 Pilot Campaign Monitoring — `/monitoring`

> _"Track active pilots, monitor weekly snapshots, and view composite campaign health."_

- **Campaign Selection**: Select from active and completed campaigns.
- **End Campaign Button**: Allows terminating an active pilot, updating its status to `"Completed"` and locking further updates.
- **Campaign Health Score Card**: A composite percentage score calculated dynamically from four key dimensions:
  - **Expected Lift Achievement**: Actual vs Expected volume lift.
  - **ROI Achievement**: Actual vs Expected ROI.
  - **Treatment vs Control Lift**: DiD relative performance difference.
  - **Outlet Participation**: Percent of treatment outlets meeting baseline targets.
- **Seeded Weekly Snapshot Timeline**: Line charts displaying cumulative volume, average ROI, active outlets, and lift over the weeks.

---

### 📊 Campaign Evaluation Console — `/evaluation`

> _"Deep-dive into treatment-control groups, pre-post metrics, and mid-campaign reallocation suggestions."_

- **Treatment & Control Group Explorer**: Review list of treatment and control outlets. Click on any outlet to open a details modal showing its ID, name, type, size, and status.
- **Pre-Post Analysis**: Standard comparison of pre-campaign vs. post-campaign sales volumes.
- **Difference-in-Differences (DiD) Analysis**: Calculates the true incremental impact (lift, ROI) by controlling for baseline differences and external factors using matched controls.
- **Mid-Campaign Reallocation**: Computes optimized recommendations to shift budget from underperforming treatment outlets to high-performing ones. Allows applying the reallocation in one click.

---

## 📡 API Reference

The backend exposes **34 REST endpoints** across 6 router groups.

### 📊 Dashboard
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/dashboard/summary` | KPI totals — outlets, budget, lift, ROI, efficiency |
| `GET` | `/api/dashboard/distributors` | Stats grouped by distributor |
| `GET` | `/api/dashboard/provinces` | Stats grouped by province |

### 🏪 Outlets
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/outlets` | Paginated, filtered, sorted outlet list |
| `GET` | `/api/outlets/{id}` | Full outlet profile (prediction + spatial + budget) |
| `GET` | `/api/outlets/{id}/spatial` | Spatial gravity features only |
| `GET` | `/api/outlets/{id}/history` | 3-year monthly transaction history |
| `GET` | `/api/outlets/export` | CSV download of entire prediction dataset |

### 💰 Budget & Simulation
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/budget/summary` | High-level spend summary |
| `GET` | `/api/budget/outlets` | Paginated per-outlet allocations |
| `GET` | `/api/budget/distributors` | Distributor-wise spend breakdown |
| `POST` | `/api/budget/simulate` | Run live KKT optimisation with custom filters, `budget` and `b_param` |

### 🗺️ Map
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/map/outlets` | Outlet markers with coordinates + predicted potential |
| `GET` | `/api/map/heatmap` | Coordinates + opportunity gap weights for heatmap |
| `GET` | `/api/map/competitors` | Competitor link coordinates (filterable) |
| `GET` | `/api/map/pois` | POI gravity scores per outlet |

### 🧠 Explainable AI
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/xai/{outlet_id}/explanation` | Generate AI narrative + feature attributions |
| `GET` | `/api/xai/{outlet_id}` | Quick fetch of local signals, features, and efficiency |

### 📢 Campaigns
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/campaigns` | List all created campaigns (Active/Completed) |
| `POST` | `/api/campaigns` | Create a new campaign manually |
| `POST` | `/api/campaigns/create-from-simulation` | Create campaign directly from simulated allocations |
| `GET` | `/api/campaigns/{id}` | Get single campaign metadata |
| `POST` | `/api/campaigns/{id}/end` | Terminate campaign (sets status to Completed) |
| `GET` | `/api/campaigns/{id}/monitoring` | Get timeline snapshots and Campaign Health Score |
| `GET` | `/api/campaigns/{id}/treatment` | Get treatment outlet list with weekly performance |
| `GET` | `/api/campaigns/{id}/control` | Get control outlet list with matched baseline data |
| `POST` | `/api/campaigns/{id}/reallocate` | Generate optimized mid-campaign reallocation recommendations |
| `POST` | `/api/campaigns/{id}/reallocate/apply` | Apply recommended reallocation budgets |

For full schemas, JSON examples, and query parameter details, see:
👉 [`backend/API_DOCUMENTATION.md`](backend/API_DOCUMENTATION.md)

**API Base URL** — configurable per environment:
```
# frontend/.env  (optional — defaults to http://localhost:8000)
VITE_API_BASE_URL=http://localhost:8000
```

---

## 📦 Key Dependencies

### Backend

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ≥ 0.115 | REST API framework |
| `uvicorn` | ≥ 0.30 | ASGI server |
| `sqlalchemy` | ≥ 2.0 | ORM + SQLite |
| `pydantic` | ≥ 2.0 | Request/response validation |
| `pandas` + `pyarrow` | ≥ 2.0 / 15.0 | Parquet ingestion during DB seeding |
| `scipy` + `numpy` | ≥ 1.12 / 1.26 | KKT dual-bisection optimisation solver |
| `google-genai` | ≥ 2.7 | Gemini 2.5 Flash LLM integration |
| `groq` | ≥ 1.4 | Groq LLaMA fallback |
| `python-dotenv` | ≥ 1.0 | `.env` file loading |

### Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| `react` + `react-dom` | ^19 | UI framework |
| `typescript` | ^5.8 | Type safety |
| `vite` | ^7 | Build tool + dev server |
| `@tanstack/react-router` | ^1.168 | File-based client routing |
| `@tanstack/react-query` | ^5.83 | Server state + caching |
| `recharts` | ^3.8 | Bar charts on Dashboard |
| `leaflet` + `react-leaflet` | ^1.9 / ^5.0 | Interactive map |
| `leaflet.heat` | ^0.2 | Heatmap layer plugin |
| `tailwindcss` | ^4.2 | Utility-first CSS |
| `@radix-ui/*` | various | Accessible headless UI primitives |
| `lucide-react` | ^0.575 | Icon library |
| `zod` | ^4.4 | Schema validation |

---

## 🧪 Backend Tests

```powershell
cd backend
uv run python test_backend.py
```

The test suite spins up an **in-memory SQLite** instance and verifies:
- All 5 router groups respond with correct status codes
- Database tables are populated and queries return expected shapes
- LLM service integration (XAI) initialises without errors

---

## 🔧 Troubleshooting

### Dashboard shows "Could not load dashboard data"

The frontend cannot reach the backend. Check:
1. Is the backend running? → `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
2. Visit http://127.0.0.1:8000/ — it should return `{"status": "online"}`
3. Ensure no firewall is blocking port 8000

### Backend fails to start — `ModuleNotFoundError`

```powershell
cd backend
uv sync   # reinstall all dependencies
```

### `FileNotFoundError` or empty responses from API

The database hasn't been seeded. Run:
```powershell
cd backend
uv run python db/ingest_db.py
```
This requires the ML pipeline to have produced outputs in `../outputs/` (relative to `datastorm-dashboard/`).

### XAI endpoint returns 500 — `No LLM API keys found`

Set at least one key in the root `.env`:
```dotenv
GEMINI_API_KEY=AIza...
```

### `npm install` fails

Ensure Node.js ≥ 18 is installed:
```powershell
node --version   # must be v18.x or higher
```

### Port 3000 already in use

Vite auto-selects the next available port. The correct URL will be printed in the terminal output.

### Map is blank / tiles not loading

The map uses OpenStreetMap tile servers which require internet access. Ensure you have an active network connection.

---

*DataStorm v7.0 · Outlet Intelligence · Beverage Distributor Track · Team Data Mavericks*
