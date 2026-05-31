from sqlalchemy.orm import Session
from typing import Optional, Dict
from db.models import SpatialFeature, Outlet

class SpatialService:
    @staticmethod
    def get_spatial_features(db: Session, outlet_id: str) -> Optional[SpatialFeature]:
        """
        Retrieve spatial features for a specific outlet.
        """
        return db.query(SpatialFeature).filter(SpatialFeature.Outlet_ID == outlet_id).first()

    @staticmethod
    def get_spatial_summary(db: Session) -> Dict[str, float]:
        """
        Retrieve spatial feature aggregates.
        """
        # Calculate overall averages
        from sqlalchemy import func
        stats = db.query(
            func.avg(SpatialFeature.POI_Total_Impact_Score).label("avg_poi_impact"),
            func.avg(SpatialFeature.Market_Saturation).label("avg_competitors"),
            func.avg(SpatialFeature.Min_Competitor_Distance_Meters).label("avg_min_comp_dist")
        ).first()
        
        return {
            "avg_poi_impact": round(float(stats.avg_poi_impact or 0.0), 2),
            "avg_competitors": round(float(stats.avg_competitors or 0.0), 2),
            "avg_min_competitor_distance": round(float(stats.avg_min_comp_dist or 0.0), 2)
        }
