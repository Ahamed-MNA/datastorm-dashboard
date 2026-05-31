from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Tuple, Optional, Dict, Any
from db.models import Outlet, Prediction, SpatialFeature, BudgetAllocation, OutletHistory

class PredictionService:
    @staticmethod
    def get_outlets(
        db: Session,
        province: Optional[str] = None,
        distributor: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "Outlet_ID",
        sort_order: str = "asc"
    ) -> Tuple[List[Outlet], int]:
        """
        Query outlets with filters, pagination, and sorting.
        """
        query = db.query(Outlet)

        # Filters
        if province:
            query = query.filter(Outlet.Province == province)
        if distributor:
            query = query.filter(Outlet.Distributor == distributor)
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    Outlet.Outlet_ID.like(search_filter),
                    Outlet.Outlet_Name.like(search_filter)
                )
            )

        # Total Count
        total_count = query.count()

        # Sorting
        if sort_by == "Predicted_Potential":
            query = query.join(Prediction)
            sort_column = Prediction.Predicted_Potential
        elif sort_by == "Historical_Sales":
            query = query.join(Prediction)
            sort_column = Prediction.Historical_Sales
        elif sort_by == "Opportunity_Gap":
            query = query.join(Prediction)
            sort_column = Prediction.Opportunity_Gap
        elif sort_by == "Growth_Percent":
            query = query.join(Prediction)
            sort_column = Prediction.Growth_Percent
        elif sort_by == "Allocated_Budget":
            query = query.join(BudgetAllocation)
            sort_column = BudgetAllocation.Allocated_Budget
        else:
            sort_column = getattr(Outlet, sort_by, Outlet.Outlet_ID)

        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Pagination
        outlets = query.offset(skip).limit(limit).all()
        return outlets, total_count

    @staticmethod
    def get_outlet_by_id(db: Session, outlet_id: str) -> Optional[Outlet]:
        """
        Retrieve an outlet by ID.
        """
        return db.query(Outlet).filter(Outlet.Outlet_ID == outlet_id).first()

    @staticmethod
    def get_outlet_history(db: Session, outlet_id: str) -> List[OutletHistory]:
        """
        Get the historical transaction logs of an outlet.
        """
        return db.query(OutletHistory).filter(OutletHistory.Outlet_ID == outlet_id).order_by(OutletHistory.Year, OutletHistory.Month).all()

    @staticmethod
    def get_export_data(db: Session) -> List[Dict[str, Any]]:
        """
        Retrieve prediction data for exporting to CSV.
        """
        results = db.query(Outlet).join(Prediction).all()
        data = []
        for o in results:
            data.append({
                "Outlet_ID": o.Outlet_ID,
                "Outlet_Name": o.Outlet_Name,
                "Province": o.Province,
                "Distributor": o.Distributor,
                "Latitude": o.Latitude,
                "Longitude": o.Longitude,
                "Outlet_Size": o.Outlet_Size,
                "Outlet_Type": o.Outlet_Type,
                "Cooler_Count": o.Cooler_Count,
                "Historical_Sales": o.prediction.Historical_Sales if o.prediction else 0.0,
                "Predicted_Potential": o.prediction.Predicted_Potential if o.prediction else 0.0,
                "Opportunity_Gap": o.prediction.Opportunity_Gap if o.prediction else 0.0,
                "Growth_Percent": o.prediction.Growth_Percent if o.prediction else 0.0,
                "Efficiency_Score": o.prediction.Efficiency_Score if o.prediction else 0.0,
            })
        return data
