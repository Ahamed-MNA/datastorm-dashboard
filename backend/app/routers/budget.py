from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.session import get_db
from app.models.schemas import BudgetAllocationSchema, OptimizeRequest, OptimizeResponse
from app.services.optimization_service import OptimizationService
from typing import List, Dict, Any

router = APIRouter(prefix="/api/budget", tags=["budget"])

@router.get("/outlets", response_model=List[BudgetAllocationSchema])
def list_budget_outlets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get the list of budget allocations per outlet.
    """
    return OptimizationService.get_budget_allocations(db, skip, limit)

@router.get("/", response_model=List[BudgetAllocationSchema])
def list_budget_allocations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    return list_budget_outlets(skip, limit, db)

@router.get("/distributors", response_model=List[Dict[str, Any]])
def get_budget_distributors(db: Session = Depends(get_db)):
    """
    Get distributor-wise budget allocation summaries.
    """
    summary = OptimizationService.get_budget_summary(db)
    if not summary or "by_distributor" not in summary:
        raise HTTPException(status_code=404, detail="Distributor budget breakdowns not found.")
    return summary["by_distributor"]

@router.get("/summary", response_model=Dict[str, Any])
def get_budget_summary(db: Session = Depends(get_db)):
    """
    Get the overall budget allocation statistics summary.
    """
    summary = OptimizationService.get_budget_summary(db)
    if not summary:
        raise HTTPException(status_code=404, detail="Budget allocation summary not found.")
    
    # Return overall stats only (exclude groupings to keep it a simple summary object)
    return {
        "total_budget": summary["total_budget"],
        "total_allocated": summary["total_allocated"],
        "expected_total_lift": summary["expected_total_lift"],
        "average_roi": summary["average_roi"],
        "active_outlets": summary["active_outlets"],
        "total_outlets": summary["total_outlets"]
    }

@router.post("/simulate", response_model=OptimizeResponse)
def simulate_budget(req: OptimizeRequest, db: Session = Depends(get_db)):
    """
    Simulate budget optimization with custom total budget (LKR)
    and optional b_param (diminishing return scaling factor).
    """
    if req.budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than 0.")
    if req.b_param <= 0:
        raise HTTPException(status_code=400, detail="Diminishing returns parameter b_param must be greater than 0.")
        
    result = OptimizationService.optimize_budget(db, req.budget, req.b_param)
    if not result:
        raise HTTPException(status_code=500, detail="Simulated optimization failed.")
    return result

@router.post("/optimize", response_model=OptimizeResponse)
def optimize_budget(req: OptimizeRequest, db: Session = Depends(get_db)):
    return simulate_budget(req, db)
