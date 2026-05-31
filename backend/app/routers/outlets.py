import io
import csv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from db.session import get_db
from app.models.schemas import PaginatedOutlets, OutletSchema, SpatialFeatureSchema, OutletHistorySchema
from app.services.prediction_service import PredictionService
from app.services.spatial_service import SpatialService

router = APIRouter(prefix="/api/outlets", tags=["outlets"])

@router.get("/export")
def export_outlets_csv(db: Session = Depends(get_db)):
    """
    Export all outlets predictions to a CSV file.
    """
    data = PredictionService.get_export_data(db)
    
    output = io.StringIO()
    fieldnames = [
        "Outlet_ID", "Outlet_Name", "Province", "Distributor", "Latitude", "Longitude",
        "Outlet_Size", "Outlet_Type", "Cooler_Count", "Historical_Sales",
        "Predicted_Potential", "Opportunity_Gap", "Growth_Percent", "Efficiency_Score"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    writer.writerows(data)
    
    # Return streaming response
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=outlet_predictions_export.csv"}
    )

@router.get("/", response_model=PaginatedOutlets)
def list_outlets(
    province: Optional[str] = Query(None, description="Filter by province"),
    distributor: Optional[str] = Query(None, description="Filter by distributor"),
    search: Optional[str] = Query(None, description="Search by ID or Name"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max number of items to return"),
    sort_by: str = Query("Outlet_ID", description="Field to sort by"),
    sort_order: str = Query("asc", description="Sort order (asc, desc)"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of outlets with filters, searching, and sorting.
    """
    outlets, total = PredictionService.get_outlets(
        db=db,
        province=province,
        distributor=distributor,
        search=search,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return PaginatedOutlets(
        total=total,
        items=outlets,
        limit=limit,
        offset=skip
    )

@router.get("/{outlet_id}", response_model=OutletSchema)
def get_outlet(outlet_id: str, db: Session = Depends(get_db)):
    """
    Retrieve full profile and model outputs for a specific outlet.
    """
    outlet = PredictionService.get_outlet_by_id(db, outlet_id)
    if not outlet:
        raise HTTPException(status_code=404, detail=f"Outlet with ID {outlet_id} not found.")
    return outlet

@router.get("/{id}/spatial", response_model=SpatialFeatureSchema)
def get_outlet_spatial(id: str, db: Session = Depends(get_db)):
    """
    Get detailed spatial and competitor gravity scores for a specific outlet.
    """
    spatial = SpatialService.get_spatial_features(db, id)
    if not spatial:
        raise HTTPException(status_code=404, detail=f"Spatial features for outlet {id} not found.")
    return spatial

@router.get("/{id}/history", response_model=List[OutletHistorySchema])
def get_outlet_history(id: str, db: Session = Depends(get_db)):
    """
    Get historical monthly transactions for an outlet.
    """
    history = PredictionService.get_outlet_history(db, id)
    return history
