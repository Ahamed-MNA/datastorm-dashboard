import numpy as np
import scipy.optimize as opt
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from db.models import BudgetAllocation, Outlet, Prediction
from app.models.schemas import BudgetAllocationSchema

class OptimizationService:
    @staticmethod
    def get_budget_allocations(db: Session, skip: int = 0, limit: int = 50) -> List[BudgetAllocation]:
        """
        Fetch budget allocations.
        """
        return db.query(BudgetAllocation).offset(skip).limit(limit).all()

    @staticmethod
    def get_budget_summary(db: Session) -> Dict[str, Any]:
        """
        Calculate budget statistics grouped by distributor, size, and type.
        """
        allocations = db.query(BudgetAllocation).join(Outlet).all()
        if not allocations:
            return {}

        total_spend = sum(a.Allocated_Budget for a in allocations)
        total_lift = sum(a.Expected_Lift for a in allocations)
        active_outlets = sum(1 for a in allocations if a.Allocated_Budget > 0.01)

        # Helper to group and aggregate
        def aggregate_by(attribute_name: str):
            groups = {}
            for a in allocations:
                val = getattr(a.outlet, attribute_name, "Unknown")
                if val not in groups:
                    groups[val] = {"count": 0, "active": 0, "spend": 0.0, "lift": 0.0}
                
                groups[val]["count"] += 1
                if a.Allocated_Budget > 0.01:
                    groups[val]["active"] += 1
                groups[val]["spend"] += a.Allocated_Budget
                groups[val]["lift"] += a.Expected_Lift

            result = []
            for name, stats in groups.items():
                spend_share = (stats["spend"] / total_spend * 100) if total_spend > 0 else 0
                avg_roi = (stats["lift"] / stats["spend"]) if stats["spend"] > 0 else 0
                result.append({
                    "name": name,
                    "total_outlets": stats["count"],
                    "active_outlets": stats["active"],
                    "total_spend": round(stats["spend"], 2),
                    "share_of_spend": round(spend_share, 2),
                    "volume_lift": round(stats["lift"], 2),
                    "avg_roi": round(avg_roi, 5)
                })
            # Sort by spend descending
            result.sort(key=lambda x: x["total_spend"], reverse=True)
            return result

        return {
            "total_budget": round(total_spend, 2),
            "total_allocated": round(total_spend, 2),
            "expected_total_lift": round(total_lift, 2),
            "average_roi": round(total_lift / total_spend if total_spend > 0 else 0.0, 5),
            "active_outlets": active_outlets,
            "total_outlets": len(allocations),
            "by_distributor": aggregate_by("Distributor"),
            "by_size": aggregate_by("Outlet_Size"),
            "by_type": aggregate_by("Outlet_Type")
        }

    @staticmethod
    def solve_kkt(outlet_ids: List[str], y_hist: np.ndarray, upper_bounds: np.ndarray, budget: float, b_param: float = 0.0005) -> Dict[str, Any]:
        """
        Core KKT bisection optimizer solver.
        """
        if len(outlet_ids) == 0:
            return {
                "total_allocated": 0.0,
                "expected_lift": 0.0,
                "active_outlets": 0,
                "avg_roi": 0.0,
                "allocations": []
            }

        a_arr = np.clip(y_hist, 1.0, None)
        U_arr = upper_bounds

        # Closed-form KKT allocation helper
        def get_spend(lam):
            spend = a_arr / lam - 1.0 / b_param
            return np.clip(spend, 0, U_arr)

        if np.sum(U_arr) <= budget:
            spend_arr = U_arr
        else:
            def budget_excess(lam):
                return np.sum(get_spend(lam)) - budget

            lam_min = 1e-15
            lam_max = np.max(a_arr * b_param) + 1.0
            
            try:
                lam_opt = opt.bisect(budget_excess, lam_min, lam_max, xtol=1e-12)
                spend_arr = get_spend(lam_opt)
            except Exception:
                # Fallback to SLSQP if bisection fails
                def neg_obj(x):
                    return -np.sum(a_arr * np.log(1.0 + b_param * x))
                
                cons = ({'type': 'ineq', 'fun': lambda x: budget - np.sum(x)})
                bounds = [(0, u) for u in U_arr]
                res = opt.minimize(neg_obj, x0=np.zeros_like(U_arr), method='SLSQP', bounds=bounds, constraints=cons)
                spend_arr = res.x

        # Calculate Lift and ROI
        lift_arr = a_arr * np.log(1.0 + b_param * spend_arr)
        roi_arr = np.zeros_like(spend_arr)
        mask = spend_arr > 0.01
        roi_arr[mask] = lift_arr[mask] / spend_arr[mask]

        # Assemble schemas response
        allocations = []
        for i, oid in enumerate(outlet_ids):
            allocations.append(BudgetAllocationSchema(
                Outlet_ID=oid,
                Allocated_Budget=round(float(spend_arr[i]), 2),
                Expected_Lift=round(float(lift_arr[i]), 2),
                ROI=round(float(roi_arr[i]), 5)
            ))

        total_allocated = float(np.sum(spend_arr))
        expected_lift = float(np.sum(lift_arr))
        active_count = int(np.sum(spend_arr > 0.01))
        avg_roi = expected_lift / total_allocated if total_allocated > 0 else 0.0

        return {
            "total_allocated": round(total_allocated, 2),
            "expected_lift": round(expected_lift, 2),
            "active_outlets": active_count,
            "avg_roi": round(avg_roi, 5),
            "allocations": allocations
        }

    @staticmethod
    def optimize_budget(db: Session, budget: float, b_param: float = 0.0005, province: Optional[str] = None) -> Dict[str, Any]:
        """
        Dynamically run the non-linear KKT dual-bisection optimization solver
        over outlets, optionally filtered by province.
        """
        query = db.query(BudgetAllocation)
        if province:
            query = query.join(Outlet).filter(Outlet.Province == province)
        records = query.all()

        # Fallback: if records are empty and province is specified, dynamically construct them from predictions
        if not records and province:
            outlets = db.query(Outlet).filter(Outlet.Province == province).all()
            if not outlets:
                return {}
            outlet_ids = [o.Outlet_ID for o in outlets]
            preds = db.query(Prediction).filter(Prediction.Outlet_ID.in_(outlet_ids)).all()
            if not preds:
                return {}
            
            y_hist = np.array([p.Historical_Sales for p in preds])
            
            # Recompute Upper Bounds
            upper_bounds = []
            for p in preds:
                a_i = max(p.Historical_Sales, 1.0)
                headroom = max(p.Predicted_Potential - p.Historical_Sales, 0.0)
                ratio = min(headroom / a_i, 50.0)
                ub = (np.exp(ratio) - 1.0) / b_param
                upper_bounds.append(ub)
            upper_bounds = np.array(upper_bounds)
            
            return OptimizationService.solve_kkt([p.Outlet_ID for p in preds], y_hist, upper_bounds, budget, b_param)

        if not records:
            return {}

        outlet_ids = [r.Outlet_ID for r in records]
        y_hist = np.array([r.Y_historical for r in records])
        
        # Scale Upper Bounds if b_param is different from database default (0.0005)
        db_default_b = 0.0005
        upper_bounds = np.array([r.Upper_Bound for r in records])
        if abs(b_param - db_default_b) > 1e-9:
            upper_bounds = upper_bounds * (db_default_b / b_param)

        return OptimizationService.solve_kkt(outlet_ids, y_hist, upper_bounds, budget, b_param)
