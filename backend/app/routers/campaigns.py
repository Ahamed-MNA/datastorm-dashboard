from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Campaign, CampaignOutlet, Outlet, ReallocationRecommendation, ImpactAnalysis
from app.models.schemas import (
    CampaignSchema,
    CampaignCreateSchema,
    CampaignOutletSchema,
    MonitoringSnapshotSchema,
    ImpactAnalysisSchema,
    ReallocationRecommendationSchema,
    CampaignSimulationCreateSchema
)
from app.services.campaign_service import CampaignService
from app.services.monitoring_service import MonitoringService
from app.services.evaluation_service import EvaluationService
from app.services.reallocation_service import ReallocationService
from typing import List, Dict, Any

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

@router.post("", response_model=CampaignSchema)
def create_campaign(campaign_in: CampaignCreateSchema, db: Session = Depends(get_db)):
    """
    Create a new marketing campaign in Draft status.
    """
    return CampaignService.create_campaign(db, campaign_in)

@router.post("/create-from-simulation", response_model=CampaignSchema)
def create_campaign_from_simulation(campaign_in: CampaignSimulationCreateSchema, db: Session = Depends(get_db)):
    """
    Create an active campaign directly from a simulated budget optimization.
    """
    return CampaignService.create_campaign_from_simulation(db, campaign_in)

@router.get("", response_model=List[CampaignSchema])
def list_campaigns(db: Session = Depends(get_db)):
    """
    List all campaigns.
    """
    return CampaignService.get_campaigns(db)

@router.get("/{campaign_id}", response_model=CampaignSchema)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """
    Get campaign details.
    """
    campaign = CampaignService.get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.post("/{campaign_id}/generate-pilot", response_model=CampaignSchema)
def generate_pilot(campaign_id: int, top_n: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """
    Generate pilot campaign treatment and control outlets, allocate budgets, 
    initialize monitoring snapshots, and transition status to Active.
    """
    campaign = CampaignService.get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != "Draft":
        raise HTTPException(status_code=400, detail="Campaign must be in Draft status to start pilot")
    
    updated_campaign = CampaignService.generate_pilot(db, campaign_id, top_n)
    return updated_campaign

@router.get("/{campaign_id}/treatment", response_model=List[CampaignOutletSchema])
def get_treatment_outlets(campaign_id: int, db: Session = Depends(get_db)):
    """
    Get the treatment group outlets for this campaign.
    """
    outlets = db.query(CampaignOutlet).filter(
        CampaignOutlet.campaign_id == campaign_id,
        CampaignOutlet.group_type == "treatment"
    ).all()
    
    result = []
    for co in outlets:
        o = db.query(Outlet).filter(Outlet.Outlet_ID == co.outlet_id).first()
        result.append(CampaignOutletSchema(
            id=co.id,
            campaign_id=co.campaign_id,
            outlet_id=co.outlet_id,
            allocated_budget=co.allocated_budget,
            expected_lift_liters=co.expected_lift_liters,
            expected_roi=co.expected_roi,
            group_type=co.group_type,
            outlet_name=o.Outlet_Name if o else f"Outlet {co.outlet_id}",
            outlet_type=o.Outlet_Type if o else "Unknown",
            outlet_size=o.Outlet_Size if o else "Unknown"
        ))
    return result

@router.get("/{campaign_id}/control", response_model=List[CampaignOutletSchema])
def get_control_outlets(campaign_id: int, db: Session = Depends(get_db)):
    """
    Get the matched control group outlets for this campaign.
    """
    outlets = db.query(CampaignOutlet).filter(
        CampaignOutlet.campaign_id == campaign_id,
        CampaignOutlet.group_type == "control"
    ).all()
    
    result = []
    for co in outlets:
        o = db.query(Outlet).filter(Outlet.Outlet_ID == co.outlet_id).first()
        result.append(CampaignOutletSchema(
            id=co.id,
            campaign_id=co.campaign_id,
            outlet_id=co.outlet_id,
            allocated_budget=co.allocated_budget,
            expected_lift_liters=co.expected_lift_liters,
            expected_roi=co.expected_roi,
            group_type=co.group_type,
            outlet_name=o.Outlet_Name if o else f"Outlet {co.outlet_id}",
            outlet_type=o.Outlet_Type if o else "Unknown",
            outlet_size=o.Outlet_Size if o else "Unknown"
        ))
    return result

@router.get("/{campaign_id}/monitoring", response_model=Dict[str, Any])
def get_campaign_monitoring(campaign_id: int, db: Session = Depends(get_db)):
    """
    Get the real-time performance tracking aggregates and charts for the campaign.
    """
    summary = MonitoringService.get_monitoring_summary(db, campaign_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Campaign monitoring data not found")
    return summary

@router.get("/{campaign_id}/monitoring/{outlet_id}", response_model=List[MonitoringSnapshotSchema])
def get_outlet_snapshots(campaign_id: int, outlet_id: str, db: Session = Depends(get_db)):
    """
    Get weekly snapshots for a specific outlet within a campaign.
    """
    return MonitoringService.get_outlet_snapshots(db, campaign_id, outlet_id)

@router.post("/{campaign_id}/evaluate/pre-post", response_model=Dict[str, Any])
def evaluate_pre_post(campaign_id: int, db: Session = Depends(get_db)):
    """
    Execute Pre vs Post sales intervention lift calculations for treatment outlets.
    """
    result = EvaluationService.calculate_pre_post(db, campaign_id)
    if not result:
        raise HTTPException(status_code=404, detail="Unable to run Pre-Post evaluation")
    return result

@router.get("/{campaign_id}/evaluate/pre-post", response_model=Dict[str, Any])
def get_pre_post_evaluation(campaign_id: int, db: Session = Depends(get_db)):
    """
    Retrieve Pre vs Post sales intervention lift results.
    """
    result = EvaluationService.calculate_pre_post(db, campaign_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pre-Post evaluation not found")
    return result

@router.post("/{campaign_id}/evaluate/did", response_model=ImpactAnalysisSchema)
def evaluate_did(campaign_id: int, db: Session = Depends(get_db)):
    """
    Compute difference-in-differences impact evaluation and confidence score.
    """
    try:
        return EvaluationService.calculate_did(db, campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}/evaluate/did", response_model=Dict[str, Any])
def get_did_evaluation(campaign_id: int, db: Session = Depends(get_db)):
    """
    Get Difference-in-Differences evaluation report and matched outlet pairs.
    """
    result = EvaluationService.get_did_evaluation_details(db, campaign_id)
    if not result:
        raise HTTPException(status_code=404, detail="DiD evaluation not found")
    return result

@router.post("/{campaign_id}/reallocate", response_model=List[ReallocationRecommendationSchema])
def generate_reallocations(campaign_id: int, db: Session = Depends(get_db)):
    """
    Run the reallocation model to flag underperforming outlets and recommend budget shift.
    """
    recs = ReallocationService.generate_recommendations(db, campaign_id)
    result = []
    for r in recs:
        o = db.query(Outlet).filter(Outlet.Outlet_ID == r.outlet_id).first()
        result.append(ReallocationRecommendationSchema(
            recommendation_id=r.recommendation_id,
            campaign_id=r.campaign_id,
            outlet_id=r.outlet_id,
            current_budget=r.current_budget,
            recommended_budget=r.recommended_budget,
            expected_improvement=r.expected_improvement,
            recommendation_reason=r.recommendation_reason,
            created_at=r.created_at,
            outlet_name=o.Outlet_Name if o else f"Outlet {r.outlet_id}"
        ))
    return result

@router.post("/{campaign_id}/reallocate/apply")
def apply_reallocations(campaign_id: int, db: Session = Depends(get_db)):
    """
    Apply budget retraction and reallocation recommendations.
    """
    ReallocationService.apply_recommendations(db, campaign_id)
    return {"status": "applied", "message": "Recommendations applied successfully, budget shifted, and monitoring refreshed."}

@router.post("/{campaign_id}/end", response_model=CampaignSchema)
def end_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """
    Transition campaign status from Active to Completed.
    """
    campaign = CampaignService.end_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign
