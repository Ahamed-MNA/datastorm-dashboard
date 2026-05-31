from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class PredictionSchema(BaseModel):
    Outlet_ID: str
    Historical_Sales: float
    Predicted_Potential: float
    Opportunity_Gap: float
    Growth_Percent: float
    Efficiency_Score: float
    CV_Volume: float
    Flatline_Score: float
    Round_Number_Bias: float
    Price_Rigidity: float

    class Config:
        from_attributes = True


class SpatialFeatureSchema(BaseModel):
    Outlet_ID: str
    School_Gravity: float
    Hospital_Gravity: float
    Transit_Gravity: float
    Religious_Gravity: float
    Commercial_Gravity: float
    Residential_Gravity: float
    Tourism_Gravity: float
    POI_Total_Impact_Score: float
    POI_Avg_Distance_Meters: float
    Competition_Gravity: float
    Market_Saturation: float
    Min_Competitor_Distance_Meters: float
    Average_Competitive_Friction: float

    class Config:
        from_attributes = True


class BudgetAllocationSchema(BaseModel):
    Outlet_ID: str
    Allocated_Budget: float
    Expected_Lift: float
    ROI: float

    class Config:
        from_attributes = True


class OutletHistorySchema(BaseModel):
    Year: int
    Month: int
    Volume_Liters: float
    Total_Bill_Value: float

    class Config:
        from_attributes = True


class OutletSchema(BaseModel):
    Outlet_ID: str
    Outlet_Name: str
    Province: str
    Distributor: str
    Latitude: float
    Longitude: float
    Outlet_Size: str
    Outlet_Type: str
    Cooler_Count: int

    prediction: Optional[PredictionSchema] = None
    spatial_features: Optional[SpatialFeatureSchema] = None
    budget_allocation: Optional[BudgetAllocationSchema] = None

    class Config:
        from_attributes = True


class PaginatedOutlets(BaseModel):
    total: int
    items: List[OutletSchema]
    limit: int
    offset: int


class DashboardStats(BaseModel):
    total_outlets: int
    total_active_outlets: int
    total_budget_allocated: float
    expected_total_lift: float
    average_roi: float
    avg_efficiency_score: float


class ChartItem(BaseModel):
    name: str
    value: float


class DashboardCharts(BaseModel):
    province_distribution: List[ChartItem]
    distributor_distribution: List[ChartItem]
    size_distribution: List[ChartItem]
    type_distribution: List[ChartItem]


class DashboardGroupStats(BaseModel):
    name: str
    total_outlets: int
    avg_potential: float
    total_opportunity_gap: float
    avg_efficiency: float


class OptimizeRequest(BaseModel):
    budget: float
    b_param: float = 0.0005


class OptimizeResponse(BaseModel):
    total_allocated: float
    expected_lift: float
    active_outlets: int
    avg_roi: float
    allocations: List[BudgetAllocationSchema]


# XAI schemas
class FeatureImpactSchema(BaseModel):
    feature_name: str
    coefficient: float
    percentage_impact: float
    feature_value: float
    local_driver_strength: float


class OutletXAIPayloadSchema(BaseModel):
    outlet_id: str
    actual_volume: float
    predicted_potential: float
    opportunity_gap: float
    efficiency_score: float
    inefficiency_pct: float
    top_drivers: List[FeatureImpactSchema]
    local_signals: Dict[str, float]
    operational_constraints: Dict[str, float]


class OutletXAIResponseSchema(BaseModel):
    outlet_id: str
    actual_volume: float
    predicted_potential: float
    opportunity_gap: float
    efficiency_score: float
    inefficiency_pct: float
    explanation: str
    payload: OutletXAIPayloadSchema


# Map endpoints schemas
class HeatmapItem(BaseModel):
    Outlet_ID: str
    Latitude: float
    Longitude: float
    Historical_Sales: float
    Predicted_Potential: float
    Opportunity_Gap: float


class CompetitorLink(BaseModel):
    Source_Outlet_ID: str
    Source_Lat: float
    Source_Lon: float
    Target_Outlet_ID: str
    Target_Lat: float
    Target_Lon: float
    Distance_Meters: float
    Competitive_Friction: float


class POIMapItem(BaseModel):
    Outlet_ID: str
    Latitude: float
    Longitude: float
    POI_Total_Impact_Score: float
    School_Gravity: float
    Hospital_Gravity: float
    Transit_Gravity: float
    Religious_Gravity: float
    Commercial_Gravity: float
    Residential_Gravity: float
    Tourism_Gravity: float


class MapOutletItem(BaseModel):
    Outlet_ID: str
    Outlet_Name: str
    Latitude: float
    Longitude: float
    Outlet_Size: str
    Outlet_Type: str
    Province: str
    Distributor: str
    Predicted_Potential: float
