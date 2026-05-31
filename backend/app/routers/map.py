import os
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from db.session import get_db
from db.models import Outlet, Prediction, SpatialFeature
from app.models.schemas import HeatmapItem, CompetitorLink, POIMapItem, MapOutletItem

router = APIRouter(prefix="/api/map", tags=["map"])

@router.get("/outlets", response_model=List[MapOutletItem])
def get_map_outlets(
    province: Optional[str] = Query(None),
    distributor: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get outlets coordinates and metadata for drawing map markers.
    """
    query = db.query(
        Outlet.Outlet_ID,
        Outlet.Outlet_Name,
        Outlet.Latitude,
        Outlet.Longitude,
        Outlet.Outlet_Size,
        Outlet.Outlet_Type,
        Outlet.Province,
        Outlet.Distributor,
        Prediction.Predicted_Potential
    ).join(Prediction)
    
    if province:
        query = query.filter(Outlet.Province == province)
    if distributor:
        query = query.filter(Outlet.Distributor == distributor)
        
    results = query.all()
    return [
        MapOutletItem(
            Outlet_ID=r.Outlet_ID,
            Outlet_Name=r.Outlet_Name,
            Latitude=r.Latitude,
            Longitude=r.Longitude,
            Outlet_Size=r.Outlet_Size,
            Outlet_Type=r.Outlet_Type,
            Province=r.Province,
            Distributor=r.Distributor,
            Predicted_Potential=round(float(r.Predicted_Potential), 2)
        )
        for r in results
    ]

@router.get("/heatmap", response_model=List[HeatmapItem])
def get_map_heatmap(
    province: Optional[str] = Query(None),
    distributor: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get coordinates and weight metrics for drawing heatmaps.
    """
    query = db.query(
        Outlet.Outlet_ID,
        Outlet.Latitude,
        Outlet.Longitude,
        Prediction.Historical_Sales,
        Prediction.Predicted_Potential,
        Prediction.Opportunity_Gap
    ).join(Prediction)
    
    if province:
        query = query.filter(Outlet.Province == province)
    if distributor:
        query = query.filter(Outlet.Distributor == distributor)
        
    results = query.all()
    return [
        HeatmapItem(
            Outlet_ID=r.Outlet_ID,
            Latitude=r.Latitude,
            Longitude=r.Longitude,
            Historical_Sales=round(float(r.Historical_Sales), 2),
            Predicted_Potential=round(float(r.Predicted_Potential), 2),
            Opportunity_Gap=round(float(r.Opportunity_Gap), 2)
        )
        for r in results
    ]

@router.get("/competitors", response_model=List[CompetitorLink])
def get_map_competitors(
    province: Optional[str] = Query(None),
    distributor: Optional[str] = Query(None),
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """
    Get competitor edges with coordinates for drawing lines between competing outlets on maps.
    Queries the parquet graph directly.
    """
    # 1. Resolve competitor graph path
    router_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(router_dir)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)
    
    graph_local = os.path.join(backend_dir, "modeling", "silver_layer_competitor_graph.parquet")
    graph_parent = os.path.join(project_root, "data", "silver", "silver_layer_competitor_graph.parquet")
    
    if os.path.exists(graph_local):
        graph_path = graph_local
    elif os.path.exists(graph_parent):
        graph_path = graph_parent
    else:
        raise HTTPException(status_code=500, detail="Competitor graph parquet file not found.")

    # 2. Query outlets coordinates
    query = db.query(Outlet.Outlet_ID, Outlet.Latitude, Outlet.Longitude, Outlet.Province, Outlet.Distributor)
    if province:
        query = query.filter(Outlet.Province == province)
    if distributor:
        query = query.filter(Outlet.Distributor == distributor)
        
    outlets_list = query.all()
    if not outlets_list:
        return []
        
    outlets_df = pd.DataFrame(outlets_list, columns=["Outlet_ID", "Latitude", "Longitude", "Province", "Distributor"])
    outlet_ids_set = set(outlets_df["Outlet_ID"])
    
    # 3. Read graph
    # Read only required columns to save memory
    df_graph = pd.read_parquet(graph_path, columns=["Source_Outlet_ID", "Target_Competitor_ID", "Distance_Meters", "Competitive_Friction"])
    
    # Filter links where Source is in our outlets set
    df_graph_filtered = df_graph[
        df_graph["Source_Outlet_ID"].isin(outlet_ids_set) & 
        df_graph["Target_Competitor_ID"].isin(outlet_ids_set)
    ]
    
    # Limit number of links returned to prevent browser crash
    df_graph_filtered = df_graph_filtered.head(limit)
    
    # Merge coordinates
    df_merged = df_graph_filtered.merge(
        outlets_df[["Outlet_ID", "Latitude", "Longitude"]].rename(columns={"Outlet_ID": "Source_Outlet_ID", "Latitude": "Source_Lat", "Longitude": "Source_Lon"}),
        on="Source_Outlet_ID",
        how="inner"
    )
    df_merged = df_merged.merge(
        outlets_df[["Outlet_ID", "Latitude", "Longitude"]].rename(columns={"Outlet_ID": "Target_Competitor_ID", "Latitude": "Target_Lat", "Longitude": "Target_Lon"}),
        on="Target_Competitor_ID",
        how="inner"
    )
    
    links = []
    for _, row in df_merged.iterrows():
        links.append(CompetitorLink(
            Source_Outlet_ID=row["Source_Outlet_ID"],
            Source_Lat=float(row["Source_Lat"]),
            Source_Lon=float(row["Source_Lon"]),
            Target_Outlet_ID=row["Target_Competitor_ID"],
            Target_Lat=float(row["Target_Lat"]),
            Target_Lon=float(row["Target_Lon"]),
            Distance_Meters=float(row["Distance_Meters"]),
            Competitive_Friction=float(row["Competitive_Friction"])
        ))
        
    return links

@router.get("/pois", response_model=List[POIMapItem])
def get_map_pois(
    province: Optional[str] = Query(None),
    distributor: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get outlets coordinates and category-level POI gravity scores.
    """
    query = db.query(
        Outlet.Outlet_ID,
        Outlet.Latitude,
        Outlet.Longitude,
        SpatialFeature.POI_Total_Impact_Score,
        SpatialFeature.School_Gravity,
        SpatialFeature.Hospital_Gravity,
        SpatialFeature.Transit_Gravity,
        SpatialFeature.Religious_Gravity,
        SpatialFeature.Commercial_Gravity,
        SpatialFeature.Residential_Gravity,
        SpatialFeature.Tourism_Gravity
    ).join(SpatialFeature, Outlet.Outlet_ID == SpatialFeature.Outlet_ID)
    
    if province:
        query = query.filter(Outlet.Province == province)
    if distributor:
        query = query.filter(Outlet.Distributor == distributor)
        
    results = query.all()
    return [
        POIMapItem(
            Outlet_ID=r.Outlet_ID,
            Latitude=r.Latitude,
            Longitude=r.Longitude,
            POI_Total_Impact_Score=round(float(r.POI_Total_Impact_Score), 2),
            School_Gravity=round(float(r.School_Gravity), 2),
            Hospital_Gravity=round(float(r.Hospital_Gravity), 2),
            Transit_Gravity=round(float(r.Transit_Gravity), 2),
            Religious_Gravity=round(float(r.Religious_Gravity), 2),
            Commercial_Gravity=round(float(r.Commercial_Gravity), 2),
            Residential_Gravity=round(float(r.Residential_Gravity), 2),
            Tourism_Gravity=round(float(r.Tourism_Gravity), 2)
        )
        for r in results
    ]
