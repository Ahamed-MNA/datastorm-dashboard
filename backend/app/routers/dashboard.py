from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from db.session import get_db
from db.models import Outlet, Prediction, BudgetAllocation
from app.models.schemas import DashboardStats, DashboardCharts, ChartItem, DashboardGroupStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/summary", response_model=DashboardStats)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Get high-level dashboard KPIs summary.
    """
    total_outlets = db.query(Outlet).count()
    total_active_outlets = db.query(BudgetAllocation).filter(BudgetAllocation.Allocated_Budget > 0.01).count()
    
    budget_stats = db.query(
        func.sum(BudgetAllocation.Allocated_Budget).label("total_budget"),
        func.sum(BudgetAllocation.Expected_Lift).label("total_lift")
    ).first()
    
    total_budget_allocated = float(budget_stats.total_budget or 0.0)
    expected_total_lift = float(budget_stats.total_lift or 0.0)
    average_roi = expected_total_lift / total_budget_allocated if total_budget_allocated > 0 else 0.0
    
    pred_stats = db.query(func.avg(Prediction.Efficiency_Score)).first()
    avg_efficiency_score = float(pred_stats[0] or 0.0)

    return DashboardStats(
        total_outlets=total_outlets,
        total_active_outlets=total_active_outlets,
        total_budget_allocated=round(total_budget_allocated, 2),
        expected_total_lift=round(expected_total_lift, 2),
        average_roi=round(average_roi, 5),
        avg_efficiency_score=round(avg_efficiency_score, 4)
    )

# Keeping stats as alias for backwards compatibility
@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    return get_dashboard_summary(db)

@router.get("/distributors", response_model=List[DashboardGroupStats])
def get_dashboard_distributors(db: Session = Depends(get_db)):
    """
    Get summary prediction details grouped by distributor.
    """
    results = db.query(
        Outlet.Distributor,
        func.count(Outlet.Outlet_ID).label("count"),
        func.avg(Prediction.Predicted_Potential).label("avg_pot"),
        func.sum(Prediction.Opportunity_Gap).label("sum_gap"),
        func.avg(Prediction.Efficiency_Score).label("avg_eff")
    ).join(Prediction).group_by(Outlet.Distributor).all()

    return [
        DashboardGroupStats(
            name=str(r.Distributor),
            total_outlets=int(r.count),
            avg_potential=round(float(r.avg_pot or 0.0), 2),
            total_opportunity_gap=round(float(r.sum_gap or 0.0), 2),
            avg_efficiency=round(float(r.avg_eff or 0.0), 4)
        )
        for r in results
    ]

@router.get("/provinces", response_model=List[DashboardGroupStats])
def get_dashboard_provinces(db: Session = Depends(get_db)):
    """
    Get summary prediction details grouped by province.
    """
    results = db.query(
        Outlet.Province,
        func.count(Outlet.Outlet_ID).label("count"),
        func.avg(Prediction.Predicted_Potential).label("avg_pot"),
        func.sum(Prediction.Opportunity_Gap).label("sum_gap"),
        func.avg(Prediction.Efficiency_Score).label("avg_eff")
    ).join(Prediction).group_by(Outlet.Province).all()

    return [
        DashboardGroupStats(
            name=str(r.Province),
            total_outlets=int(r.count),
            avg_potential=round(float(r.avg_pot or 0.0), 2),
            total_opportunity_gap=round(float(r.sum_gap or 0.0), 2),
            avg_efficiency=round(float(r.avg_eff or 0.0), 4)
        )
        for r in results
    ]

@router.get("/charts", response_model=DashboardCharts)
def get_dashboard_charts(db: Session = Depends(get_db)):
    """
    Get aggregated charts metrics.
    """
    def get_distribution(column):
        results = db.query(column, func.count(Outlet.Outlet_ID)).group_by(column).all()
        return [ChartItem(name=str(r[0]), value=float(r[1])) for r in results if r[0] is not None]

    province_dist = get_distribution(Outlet.Province)
    distributor_dist = get_distribution(Outlet.Distributor)
    size_dist = get_distribution(Outlet.Outlet_Size)
    type_dist = get_distribution(Outlet.Outlet_Type)

    return DashboardCharts(
        province_distribution=province_dist,
        distributor_distribution=distributor_dist,
        size_distribution=size_dist,
        type_distribution=type_dist
    )
