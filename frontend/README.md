# 🌩️ Outlet Intelligence Frontend

React + TypeScript single-page application for the **Outlet Intelligence Web Dashboard**. Built with Vite, TanStack Router, TanStack Query, shadcn/ui, Recharts, and Leaflet.

---

## 🚀 Key Features

1. **Executive Dashboard** (`/`) — KPI cards, province/distributor opportunity charts, efficiency breakdowns.
2. **Outlet Explorer** (`/outlets`) — Paginated, filterable, sortable data table of 19,960 outlets with CSV export.
3. **Outlet Detail** (`/outlets/:id`) — Deep-dive predictions, spatial gravity radar chart, 3-year sales history, XAI AI-generated narrative, competitor links.
4. **Geospatial Map** (`/map`) — Interactive Leaflet map with outlet markers, opportunity heatmap, and POI gravity overlays.
5. **Trade-Spend Optimiser** (`/budget`) — What-if budget simulator with province/type/size filters, outlet selection explainability pop-ups, and direct campaign launch.
6. **Campaign Monitoring** (`/monitoring`) _(NEW)_ — Campaign lifecycle management with real-time KPIs, health score dashboard, traffic-light per-outlet status, Expected vs Actual charts, Budget vs ROI scatter, distributor performance, budget reallocation.
7. **Pilot Evaluation** (`/evaluation`) _(NEW)_ — Pre vs Post lift analysis, Difference-in-Differences econometric impact, matched treatment-control pairs table, confidence scoring.

---

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── routes/                        # TanStack file-based routes
│   │   ├── __root.tsx                 # Root layout (sidebar shell)
│   │   ├── index.tsx                  # / → Executive Dashboard
│   │   ├── outlets.tsx                # /outlets → Layout wrapper
│   │   ├── outlets.index.tsx          # /outlets → Outlet Explorer table
│   │   ├── outlets.$id.tsx            # /outlets/:id → Outlet Detail
│   │   ├── map.tsx                    # /map → Geospatial Map
│   │   ├── budget.tsx                 # /budget → Trade-Spend Optimiser
│   │   ├── monitoring.tsx             # /monitoring → Campaign Monitoring (NEW)
│   │   └── evaluation.tsx             # /evaluation → Pilot Evaluation (NEW)
│   ├── components/
│   │   ├── app-sidebar.tsx            # Navigation sidebar
│   │   ├── kpi-card.tsx               # Reusable KPI display card
│   │   ├── metric-tooltip.tsx         # Glossary tooltip for metrics
│   │   └── ui/                        # shadcn/ui component library
│   ├── lib/
│   │   ├── api.ts                     # Typed fetch client for all 34 endpoints
│   │   ├── format.ts                  # Number, currency, percentage formatters
│   │   ├── utils.ts                   # Utility helpers (cn)
│   │   ├── config.server.ts           # Server configuration
│   │   ├── error-capture.ts           # Error capture utilities
│   │   ├── error-page.ts             # Error page component
│   │   └── lovable-error-reporting.ts # Error reporting integration
│   ├── hooks/
│   │   └── use-mobile.tsx             # Mobile detection hook
│   ├── types/
│   │   └── leaflet.heat.d.ts          # TypeScript definitions for leaflet.heat
│   ├── App.tsx                        # App component
│   ├── App.css                        # App styles
│   ├── main.tsx                       # Entry point
│   ├── router.tsx                     # Router configuration
│   ├── routeTree.gen.ts               # Auto-generated route tree
│   ├── index.css                      # Base CSS
│   └── styles.css                     # Global Tailwind + CSS variables
├── public/                            # Static assets
├── index.html                         # HTML entry point
├── package.json                       # Dependencies
├── vite.config.ts                     # Vite configuration
├── tsconfig.json                      # TypeScript config
├── tsconfig.app.json                  # App-specific TS config
├── tsconfig.node.json                 # Node TS config
└── eslint.config.js                   # ESLint configuration
```

---

## 🛠️ Setup & Development

### Prerequisites
- **Node.js**: ≥ 18
- **npm**: ≥ 9

### Install Dependencies
```powershell
npm install
```

### Start Development Server
```powershell
npm run dev
```
Open: **http://localhost:3000**

> The frontend expects the backend API to be running at `http://localhost:8000`. Configure via environment variable:
> ```
> VITE_API_BASE_URL=http://localhost:8000
> ```

### Build for Production
```powershell
npm run build
```

### Preview Production Build
```powershell
npm run preview
```

### Lint
```powershell
npm run lint
```

---

## 📡 API Client

All backend communication is centralized in [`src/lib/api.ts`](src/lib/api.ts). The API client provides typed functions for all 34 endpoints across 6 groups:

| Group | Functions |
|-------|----------|
| Dashboard | `dashboardSummary`, `dashboardDistributors`, `dashboardProvinces` |
| Outlets | `outlets`, `outlet`, `outletHistory`, `outletSpatial`, `outletExportUrl` |
| Budget | `budgetSummary`, `budgetDistributors`, `budgetOutlets`, `budgetSimulate` |
| Map | `mapOutlets`, `mapHeatmap`, `mapCompetitors`, `mapPois` |
| XAI | `xai` |
| Campaigns _(NEW)_ | `createCampaign`, `createCampaignFromSimulation`, `listCampaigns`, `campaignDetails`, `startPilot`, `getTreatmentGroup`, `getControlGroup`, `getCampaignMonitoring`, `getOutletMonitoring`, `runEvaluationPrePost`, `getEvaluationPrePost`, `runEvaluationDiD`, `getEvaluationDiD`, `getReallocations`, `applyReallocations`, `endCampaign` |

---

## 🎨 Tech Stack

| Technology | Purpose |
|------------|--------|
| React 19 + TypeScript 5.8 | UI framework |
| Vite 7 | Build tool + dev server |
| TanStack Router | File-based client routing |
| TanStack Query | Server state management + caching |
| shadcn/ui + Radix UI | Accessible component primitives |
| Tailwind CSS 4.2 | Utility-first styling |
| Recharts 3.8 | Bar, line, scatter, and radar charts |
| Leaflet + react-leaflet | Interactive geospatial map |
| leaflet.heat | Heatmap layer plugin |
| Lucide React | Icon library |
| Sonner | Toast notifications |
| Zod 4.4 | Schema validation |

---

## 🖥️ Pages Reference

| Route | Page | Description |
|-------|------|-------------|
| `/` | Executive Dashboard | KPI cards, province/distributor charts, efficiency breakdowns |
| `/outlets` | Outlet Explorer | Searchable, filterable, sortable data table with CSV export |
| `/outlets/:id` | Outlet Detail | Predictions, spatial features, sales history, XAI narrative |
| `/map` | Geospatial Map | Leaflet map with outlets, heatmap, and POI layers |
| `/budget` | Trade-Spend Optimiser | What-if simulator, outlet explainability, campaign launch |
| `/monitoring` | Campaign Monitoring _(NEW)_ | Campaign lifecycle, real-time KPIs, health scores, reallocation |
| `/evaluation` | Pilot Evaluation _(NEW)_ | Pre-Post analysis, DiD impact, matched pairs |

---

*DataStorm v7.0 · Outlet Intelligence · Team Data Mavericks*
