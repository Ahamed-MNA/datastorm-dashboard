// API client for the Outlet Intelligence FastAPI backend.
export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export type DashboardStats = {
  total_outlets: number;
  total_active_outlets: number;
  total_budget_allocated: number;
  expected_total_lift: number;
  average_roi: number;
  avg_efficiency_score: number;
};

export type GroupStats = {
  name: string;
  total_outlets: number;
  avg_potential: number;
  total_opportunity_gap: number;
  avg_efficiency: number;
};

export type OutletListItem = {
  Outlet_ID: string;
  Outlet_Name: string;
  Province: string;
  Distributor: string;
  Latitude: number;
  Longitude: number;
  Outlet_Size: string;
  Outlet_Type: string;
  Cooler_Count: number;
};

export type PaginatedOutlets = {
  total: number;
  items: OutletListItem[];
  limit: number;
  offset: number;
};

export type PredictionSchema = {
  Outlet_ID: string;
  Historical_Sales: number;
  Predicted_Potential: number;
  Opportunity_Gap: number;
  Growth_Percent: number;
  Efficiency_Score: number;
  CV_Volume: number;
  Flatline_Score: number;
  Round_Number_Bias: number;
  Price_Rigidity: number;
};

export type SpatialFeatureSchema = {
  Outlet_ID: string;
  School_Gravity: number;
  Hospital_Gravity: number;
  Transit_Gravity: number;
  Religious_Gravity: number;
  Commercial_Gravity: number;
  Residential_Gravity: number;
  Tourism_Gravity: number;
  POI_Total_Impact_Score: number;
  POI_Avg_Distance_Meters: number;
  Competition_Gravity: number;
  Market_Saturation: number;
  Min_Competitor_Distance_Meters: number;
  Average_Competitive_Friction: number;
};

export type BudgetAllocationSchema = {
  Outlet_ID: string;
  Allocated_Budget: number;
  Expected_Lift: number;
  ROI: number;
};

export type OutletSchema = OutletListItem & {
  prediction: PredictionSchema;
  spatial_features: SpatialFeatureSchema;
  budget_allocation: BudgetAllocationSchema;
};

export type OutletHistory = {
  Year: number;
  Month: number;
  Volume_Liters: number;
  Total_Bill_Value: number;
};

export type XAITopDriver = {
  feature_name: string;
  coefficient: number;
  percentage_impact: number;
  feature_value: number;
  local_driver_strength: number;
};

export type XAIResponse = {
  outlet_id: string;
  actual_volume: number;
  predicted_potential: number;
  opportunity_gap: number;
  efficiency_score: number;
  inefficiency_pct: number;
  explanation: string;
  payload: {
    outlet_id: string;
    actual_volume: number;
    predicted_potential: number;
    opportunity_gap: number;
    efficiency_score: number;
    inefficiency_pct: number;
    top_drivers: XAITopDriver[];
    local_signals: Record<string, number>;
    operational_constraints: Record<string, number>;
  };
};

export type MapOutletItem = {
  Outlet_ID: string;
  Outlet_Name: string;
  Latitude: number;
  Longitude: number;
  Outlet_Size: string;
  Outlet_Type: string;
  Province: string;
  Distributor: string;
  Predicted_Potential: number;
};

export type HeatmapItem = {
  Outlet_ID: string;
  Latitude: number;
  Longitude: number;
  Historical_Sales: number;
  Predicted_Potential: number;
  Opportunity_Gap: number;
};

export type CompetitorLink = {
  Source_Outlet_ID: string;
  Source_Lat: number;
  Source_Lon: number;
  Target_Outlet_ID: string;
  Target_Lat: number;
  Target_Lon: number;
  Distance_Meters: number;
  Competitive_Friction: number;
};

export type POIMapItem = {
  Outlet_ID: string;
  Latitude: number;
  Longitude: number;
  POI_Total_Impact_Score: number;
  School_Gravity: number;
  Hospital_Gravity: number;
  Transit_Gravity: number;
  Religious_Gravity: number;
  Commercial_Gravity: number;
  Residential_Gravity: number;
  Tourism_Gravity: number;
};

export type DistributorSpend = {
  name: string;
  total_outlets: number;
  active_outlets: number;
  total_spend: number;
  share_of_spend: number;
  volume_lift: number;
  avg_roi: number;
};

export type BudgetSummary = {
  total_budget: number;
  total_allocated: number;
  expected_total_lift: number;
  average_roi: number;
  active_outlets: number;
  total_outlets: number;
};

export type OptimizeResponse = {
  total_allocated: number;
  expected_lift: number;
  active_outlets: number;
  avg_roi: number;
  allocations: BudgetAllocationSchema[];
};

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(API_BASE_URL + path);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "" && v !== null) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(API_BASE_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  dashboardSummary: () => get<DashboardStats>("/api/dashboard/summary"),
  dashboardDistributors: () => get<GroupStats[]>("/api/dashboard/distributors"),
  dashboardProvinces: () => get<GroupStats[]>("/api/dashboard/provinces"),

  outlets: (params: {
    province?: string;
    distributor?: string;
    search?: string;
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }) => get<PaginatedOutlets>("/api/outlets", params),

  outlet: (id: string) => get<OutletSchema>(`/api/outlets/${id}`),
  outletHistory: (id: string) => get<OutletHistory[]>(`/api/outlets/${id}/history`),
  outletSpatial: (id: string) => get<SpatialFeatureSchema>(`/api/outlets/${id}/spatial`),
  outletExportUrl: () => `${API_BASE_URL}/api/outlets/export`,

  xai: (id: string) => get<XAIResponse>(`/api/xai/${id}/explanation`),

  mapOutlets: () => get<MapOutletItem[]>("/api/map/outlets"),
  mapHeatmap: () => get<HeatmapItem[]>("/api/map/heatmap"),
  mapCompetitors: (params: { province?: string; distributor?: string; limit?: number }) =>
    get<CompetitorLink[]>("/api/map/competitors", params),
  mapPois: () => get<POIMapItem[]>("/api/map/pois"),

  budgetSummary: () => get<BudgetSummary>("/api/budget/summary"),
  budgetDistributors: () => get<DistributorSpend[]>("/api/budget/distributors"),
  budgetOutlets: (params: { skip?: number; limit?: number }) =>
    get<BudgetAllocationSchema[]>("/api/budget/outlets", params),
  budgetSimulate: (body: { budget: number; b_param: number }) =>
    post<OptimizeResponse>("/api/budget/simulate", body),

  // Campaigns API endpoints
  createCampaign: (body: CampaignCreateInput) => post<Campaign>("/api/campaigns", body),
  listCampaigns: () => get<Campaign[]>("/api/campaigns"),
  campaignDetails: (id: number) => get<Campaign>(`/api/campaigns/${id}`),
  startPilot: (id: number, topN = 20) => post<Campaign>(`/api/campaigns/${id}/generate-pilot?top_n=${topN}`, {}),
  getTreatmentGroup: (id: number) => get<CampaignOutlet[]>(`/api/campaigns/${id}/treatment`),
  getControlGroup: (id: number) => get<CampaignOutlet[]>(`/api/campaigns/${id}/control`),
  getCampaignMonitoring: (id: number) => get<CampaignMonitoringSummary>(`/api/campaigns/${id}/monitoring`),
  getOutletMonitoring: (id: number, outletId: string) => get<MonitoringSnapshot[]>(`/api/campaigns/${id}/monitoring/${outletId}`),
  runEvaluationPrePost: (id: number) => post<Record<string, any>>(`/api/campaigns/${id}/evaluate/pre-post`, {}),
  getEvaluationPrePost: (id: number) => get<Record<string, any>>(`/api/campaigns/${id}/evaluate/pre-post`),
  runEvaluationDiD: (id: number) => post<ImpactAnalysis>(`/api/campaigns/${id}/evaluate/did`, {}),
  getEvaluationDiD: (id: number) => get<DiDEvaluationDetails>(`/api/campaigns/${id}/evaluate/did`),
  getReallocations: (id: number) => post<ReallocationRecommendation[]>(`/api/campaigns/${id}/reallocate`, {}),
  applyReallocations: (id: number) => post<{ status: string; message: string }>(`/api/campaigns/${id}/reallocate/apply`, {}),
};

// Campaign interfaces
export type Campaign = {
  campaign_id: number;
  campaign_name: string;
  province: string;
  start_date: string;
  end_date: string;
  total_budget: number;
  status: string;
  created_at: string;
};

export type CampaignCreateInput = {
  campaign_name: string;
  province: string;
  start_date: string;
  end_date: string;
  total_budget: number;
};

export type CampaignOutlet = {
  id: number;
  campaign_id: number;
  outlet_id: string;
  allocated_budget: number;
  expected_lift_liters: number;
  expected_roi: number;
  group_type: string;
  outlet_name?: string;
  outlet_type?: string;
  outlet_size?: string;
};

export type MonitoringSnapshot = {
  snapshot_id: number;
  campaign_id: number;
  outlet_id: string;
  snapshot_date: string;
  actual_volume: number;
  actual_revenue: number;
  actual_lift: number;
  notes?: string;
};

export type CampaignMonitoringSummary = {
  campaign_id: number;
  campaign_name: string;
  status: string;
  allocated_budget: number;
  expected_lift: number;
  actual_lift: number;
  roi: number;
  actual_revenue: number;
  underperforming_outlets: number;
  outlets_performance: Array<{
    outlet_id: string;
    outlet_name: string;
    distributor: string;
    allocated_budget: number;
    expected_lift: number;
    actual_lift: number;
    roi: number;
    performance_pct: number;
    status: "Green" | "Yellow" | "Red";
    notes: string;
  }>;
  charts: {
    expected_vs_actual: Array<{
      outlet_id: string;
      expected_lift: number;
      actual_lift: number;
    }>;
    budget_vs_roi: Array<{
      outlet_id: string;
      budget: number;
      roi: number;
    }>;
    province_performance: Array<{
      distributor: string;
      budget: number;
      actual_lift: number;
      roi: number;
    }>;
  };
};

export type ImpactAnalysis = {
  analysis_id: number;
  campaign_id: number;
  pre_volume: number;
  post_volume: number;
  treatment_lift: number;
  control_lift: number;
  did_effect: number;
  confidence_score: number;
  generated_at: string;
};

export type DiDEvaluationDetails = {
  campaign_id: number;
  campaign_name: string;
  status: string;
  pre_volume: number;
  post_volume: number;
  treatment_lift: number;
  control_lift: number;
  did_effect: number;
  confidence_score: number;
  generated_at: string | null;
  pairs: Array<{
    treatment_id: string;
    treatment_name: string;
    treatment_type: string;
    treatment_size: string;
    treatment_pre: number;
    treatment_post: number;
    treatment_lift: number;
    control_id: string;
    control_name: string;
    control_pre: number;
    control_post: number;
    control_lift: number;
    net_lift: number;
  }>;
};

export type ReallocationRecommendation = {
  recommendation_id: number;
  campaign_id: number;
  outlet_id: string;
  current_budget: number;
  recommended_budget: number;
  expected_improvement: number;
  recommendation_reason: string;
  created_at: string;
  outlet_name?: string;
};

