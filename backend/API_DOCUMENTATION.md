# 📖 Outlet Intelligence API Documentation

This document provides a comprehensive reference of all endpoints, parameters, and JSON payloads for the Outlet Intelligence FastAPI backend.

---

## 🏗️ Data Models (JSON Schemas)

### 1. Outlet Schema
Represents a retail outlet profile and its associated model outputs.
```json
{
  "Outlet_ID": "OUT_00001",
  "Outlet_Name": "Outlet OUT_00001",
  "Province": "Western",
  "Distributor": "DIST_W_03",
  "Latitude": 7.089846,
  "Longitude": 79.979055,
  "Outlet_Size": "Medium",
  "Outlet_Type": "Grocery",
  "Cooler_Count": 1,
  "prediction": {
    "Outlet_ID": "OUT_00001",
    "Historical_Sales": 654.0,
    "Predicted_Potential": 3946.3,
    "Opportunity_Gap": 3292.3,
    "Growth_Percent": 503.41,
    "Efficiency_Score": 0.1657,
    "CV_Volume": 0.6434,
    "Flatline_Score": 0.0435,
    "Round_Number_Bias": 0.0,
    "Price_Rigidity": 6017.29
  },
  "spatial_features": {
    "Outlet_ID": "OUT_00001",
    "School_Gravity": 75.47,
    "Hospital_Gravity": 71.66,
    "Transit_Gravity": 0.0,
    "Religious_Gravity": 758.3,
    "Commercial_Gravity": 0.0,
    "Residential_Gravity": 0.0,
    "Tourism_Gravity": 0.0,
    "POI_Total_Impact_Score": 905.43,
    "POI_Avg_Distance_Meters": 645.31,
    "Competition_Gravity": 26.22,
    "Market_Saturation": 366.0,
    "Min_Competitor_Distance_Meters": 303.86,
    "Average_Competitive_Friction": 0.0716
  },
  "budget_allocation": {
    "Outlet_ID": "OUT_00001",
    "Allocated_Budget": 0.0,
    "Expected_Lift": 0.0,
    "ROI": 0.0
  }
}
```

### 2. History Schema
```json
{
  "Year": 2023,
  "Month": 3,
  "Volume_Liters": 1390.92,
  "Total_Bill_Value": 398271.12
}
```

### 3. XAI Response Schema
```json
{
  "outlet_id": "OUT_00001",
  "actual_volume": 654.0,
  "predicted_potential": 3946.3,
  "opportunity_gap": 3292.3,
  "efficiency_score": 0.17,
  "inefficiency_pct": 83.43,
  "explanation": "Three paragraph commercial narrative text here...",
  "payload": {
    "outlet_id": "OUT_00001",
    "actual_volume": 654.0,
    "predicted_potential": 3946.3,
    "opportunity_gap": 3292.3,
    "efficiency_score": 0.17,
    "inefficiency_pct": 83.43,
    "top_drivers": [
      {
        "feature_name": "Province_Western",
        "coefficient": 0.8124,
        "percentage_impact": 125.31,
        "feature_value": 1.0,
        "local_driver_strength": 125.31
      }
    ],
    "local_signals": {
      "Competitor Count 5km": 366.0,
      "Religious Gravity": 758.3
    },
    "operational_constraints": {
      "Cooler Count": 1.0,
      "CV Volume": 0.6434
    }
  }
}
```

---

## 📡 API Endpoints Reference

### 📊 Dashboard Endpoints

#### `GET /api/dashboard/summary`
Returns high-level KPI stats.
* **Response Body**: `DashboardStats`
```json
{
  "total_outlets": 19960,
  "total_active_outlets": 1981,
  "total_budget_allocated": 4999999.97,
  "expected_total_lift": 1238686.62,
  "average_roi": 0.24774,
  "avg_efficiency_score": 0.5782
}
```

#### `GET /api/dashboard/distributors`
Prediction stats aggregated by distributor ID.
* **Response Body**: `List[DashboardGroupStats]`
```json
[
  {
    "name": "DIST_C_01",
    "total_outlets": 1383,
    "avg_potential": 832.52,
    "total_opportunity_gap": 841950.14,
    "avg_efficiency": 0.5719
  }
]
```

#### `GET /api/dashboard/provinces`
Prediction stats aggregated by province.
* **Response Body**: `List[DashboardGroupStats]`
```json
[
  {
    "name": "Central",
    "total_outlets": 3991,
    "avg_potential": 827.63,
    "total_opportunity_gap": 2413710.22,
    "avg_efficiency": 0.5722
  }
]
```

---

### 🏪 Outlets Endpoints

#### `GET /api/outlets`
Paginated, searchable, and sortable list of outlets.
* **Query Parameters**:
  - `province` (optional string): Filter by province.
  - `distributor` (optional string): Filter by distributor.
  - `search` (optional string): Search by Outlet_ID or Outlet_Name.
  - `skip` (optional int, default: 0): Offset.
  - `limit` (optional int, default: 50): Number of records.
  - `sort_by` (optional string, default: "Outlet_ID"): Field name.
  - `sort_order` (optional string, default: "asc"): "asc" or "desc".
* **Response Body**: `PaginatedOutlets`
```json
{
  "total": 19960,
  "items": [
    {
      "Outlet_ID": "OUT_00001",
      "Outlet_Name": "Outlet OUT_00001",
      "Province": "Western",
      "Distributor": "DIST_W_03",
      "Latitude": 7.089846,
      "Longitude": 79.979055,
      "Outlet_Size": "Medium",
      "Outlet_Type": "Grocery",
      "Cooler_Count": 1
    }
  ],
  "limit": 50,
  "offset": 0
}
```

#### `GET /api/outlets/{id}`
Returns details for a single outlet.
* **Path Parameters**:
  - `id` (string): Outlet ID.
* **Response Body**: `OutletSchema`

#### `GET /api/outlets/{id}/spatial`
Returns spatial features for an outlet.
* **Path Parameters**:
  - `id` (string): Outlet ID.
* **Response Body**: `SpatialFeatureSchema`

#### `GET /api/outlets/{id}/history`
Returns 3-year historical monthly transaction logs.
* **Path Parameters**:
  - `id` (string): Outlet ID.
* **Response Body**: `List[OutletHistorySchema]`

#### `GET /api/outlets/export`
Generates a downloadable CSV containing the entire prediction dataset.
* **Response Headers**:
  - `Content-Type`: `text/csv; charset=utf-8`
  - `Content-Disposition`: `attachment; filename=outlet_predictions_export.csv`

---

### 💰 Budget & Simulation Endpoints

#### `GET /api/budget/outlets`
Retrieve the list of baseline budget allocations.
* **Query Parameters**:
  - `skip` (optional int, default: 0)
  - `limit` (optional int, default: 50)
* **Response Body**: `List[BudgetAllocationSchema]`

#### `GET /api/budget/distributors`
Distributor-wise spend summaries.
* **Response Body**: `List[Dict]`
```json
[
  {
    "name": "DIST_W_01",
    "total_outlets": 3016,
    "active_outlets": 663,
    "total_spend": 1704035.15,
    "share_of_spend": 34.08,
    "volume_lift": 424558.34,
    "avg_roi": 0.24915
  }
]
```

#### `GET /api/budget/summary`
High level overall promotional spend stats.
* **Response Body**: `Dict`
```json
{
  "total_budget": 4999999.97,
  "total_allocated": 4999999.97,
  "expected_total_lift": 1238686.62,
  "average_roi": 0.24774,
  "active_outlets": 1981,
  "total_outlets": 8989
}
```

#### `POST /api/budget/simulate`
Re-runs budget optimization solver dynamically.
* **Request Body**: `OptimizeRequest`
```json
{
  "budget": 10000000.0,
  "b_param": 0.0005
}
```
* **Response Body**: `OptimizeResponse`
```json
{
  "total_allocated": 10000000.0,
  "expected_lift": 1842667.8,
  "active_outlets": 2276,
  "avg_roi": 0.18427,
  "allocations": [
    {
      "Outlet_ID": "OUT_00837",
      "Allocated_Budget": 1856.92,
      "Expected_Lift": 384.64,
      "ROI": 0.20714
    }
  ]
}
```

---

### 🗺️ Map Endpoints

#### `GET /api/map/outlets`
Returns outlets markers.
* **Response Body**: `List[MapOutletItem]`
```json
[
  {
    "Outlet_ID": "OUT_00001",
    "Outlet_Name": "Outlet OUT_00001",
    "Latitude": 7.089846,
    "Longitude": 79.979055,
    "Outlet_Size": "Medium",
    "Outlet_Type": "Grocery",
    "Province": "Western",
    "Distributor": "DIST_W_03",
    "Predicted_Potential": 3946.3
  }
]
```

#### `GET /api/map/heatmap`
Returns coordinates and weights for heatmaps.
* **Response Body**: `List[HeatmapItem]`
```json
[
  {
    "Outlet_ID": "OUT_00001",
    "Latitude": 7.089846,
    "Longitude": 79.979055,
    "Historical_Sales": 654.0,
    "Predicted_Potential": 3946.3,
    "Opportunity_Gap": 3292.3
  }
]
```

#### `GET /api/map/competitors`
Competitor links with source and target coordinates.
* **Query Parameters**:
  - `province` (optional string): Filter.
  - `distributor` (optional string): Filter.
  - `limit` (optional int, default: 2000): Limit counts to prevent frontend lags.
* **Response Body**: `List[CompetitorLink]`
```json
[
  {
    "Source_Outlet_ID": "OUT_00001",
    "Source_Lat": 7.089846,
    "Source_Lon": 79.979055,
    "Target_Outlet_ID": "OUT_00052",
    "Target_Lat": 7.048015,
    "Target_Lon": 79.971018,
    "Distance_Meters": 4709.44,
    "Competitive_Friction": 0.0
  }
]
```

#### `GET /api/map/pois`
Returns categories-wise POI gravity scores.
* **Response Body**: `List[POIMapItem]`
```json
[
  {
    "Outlet_ID": "OUT_00001",
    "Latitude": 7.089846,
    "Longitude": 79.979055,
    "POI_Total_Impact_Score": 905.43,
    "School_Gravity": 75.47,
    "Hospital_Gravity": 71.66,
    "Transit_Gravity": 0.0,
    "Religious_Gravity": 758.3,
    "Commercial_Gravity": 0.0,
    "Residential_Gravity": 0.0,
    "Tourism_Gravity": 0.0
  }
]
```

---

### 🧠 Explainable AI Endpoints

#### `GET /api/xai/{outlet_id}/explanation`
Generates SFA metrics and routes request to Google Gemini or Groq models.
* **Path Parameters**:
  - `outlet_id` (string): Outlet ID.
* **Response Body**: `OutletXAIResponseSchema`
