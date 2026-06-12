from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from db.models import Campaign, CampaignOutlet, Outlet, Prediction, MonitoringSnapshot
from app.models.schemas import CampaignCreateSchema
import math

class CampaignService:
    @staticmethod
    def get_campaigns(db: Session) -> List[Campaign]:
        return db.query(Campaign).all()

    @staticmethod
    def get_campaign_by_id(db: Session, campaign_id: int) -> Optional[Campaign]:
        return db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()

    @staticmethod
    def create_campaign(db: Session, campaign_in: CampaignCreateSchema) -> Campaign:
        db_campaign = Campaign(
            campaign_name=campaign_in.campaign_name,
            province=campaign_in.province,
            start_date=campaign_in.start_date,
            end_date=campaign_in.end_date,
            total_budget=campaign_in.total_budget,
            status="Draft"
        )
        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)
        return db_campaign

    @staticmethod
    def generate_pilot(db: Session, campaign_id: int, top_n: int = 20) -> Optional[Campaign]:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign or campaign.status != "Draft":
            return campaign

        # 1. Run optimization for all outlets in the province
        from app.services.optimization_service import OptimizationService
        opt_res = OptimizationService.optimize_budget(
            db, budget=campaign.total_budget, b_param=0.0005, province=campaign.province
        )
        
        if not opt_res or "allocations" not in opt_res:
            return campaign
            
        # 2. Extract and sort allocations by budget descending
        allocations = opt_res["allocations"]
        allocations.sort(key=lambda x: x.Allocated_Budget, reverse=True)
        
        # Filter out outlets that received 0 or very small budgets (<= 0.01)
        active_allocs = [a for a in allocations if a.Allocated_Budget > 0.01]
        
        if len(active_allocs) < top_n:
            top_n = len(active_allocs)
            
        if top_n == 0:
            if len(allocations) > 0:
                active_allocs = allocations[:top_n]
                top_n = len(active_allocs)
            else:
                return campaign
                
        treatment_allocs = active_allocs[:top_n]
        treatment_ids = {a.Outlet_ID for a in treatment_allocs}
        
        # Query all predictions in the province to get control pool
        outlets = db.query(Outlet).filter(Outlet.Province == campaign.province).all()
        outlet_ids = [o.Outlet_ID for o in outlets]
        
        # Control pool contains all outlets in province except the treatment ones
        control_pool = db.query(Prediction).filter(
            Prediction.Outlet_ID.in_(outlet_ids),
            ~Prediction.Outlet_ID.in_(treatment_ids)
        ).all()
        
        campaign_outlets = []
        matched_control_ids = set()
        
        for alloc in treatment_allocs:
            t_outlet = db.query(Outlet).filter(Outlet.Outlet_ID == alloc.Outlet_ID).first()
            t_pred = db.query(Prediction).filter(Prediction.Outlet_ID == alloc.Outlet_ID).first()
            
            treatment_entry = CampaignOutlet(
                campaign_id=campaign_id,
                outlet_id=alloc.Outlet_ID,
                allocated_budget=alloc.Allocated_Budget,
                expected_lift_liters=alloc.Expected_Lift,
                expected_roi=alloc.ROI,
                group_type="treatment"
            )
            campaign_outlets.append(treatment_entry)
            
            # Nearest Neighbor Control Outlet Matching
            match_ctrl = None
            min_diff = float('inf')
            
            for c_pred in control_pool:
                if c_pred.Outlet_ID in matched_control_ids:
                    continue
                    
                c_outlet = db.query(Outlet).filter(Outlet.Outlet_ID == c_pred.Outlet_ID).first()
                if c_outlet.Outlet_Type == t_outlet.Outlet_Type and c_outlet.Outlet_Size == t_outlet.Outlet_Size:
                    diff = abs(c_pred.Historical_Sales - t_pred.Historical_Sales)
                    if diff < min_diff:
                        min_diff = diff
                        match_ctrl = c_pred
            
            if not match_ctrl:
                for c_pred in control_pool:
                    if c_pred.Outlet_ID in matched_control_ids:
                        continue
                    c_outlet = db.query(Outlet).filter(Outlet.Outlet_ID == c_pred.Outlet_ID).first()
                    if c_outlet.Outlet_Type == t_outlet.Outlet_Type:
                        diff = abs(c_pred.Historical_Sales - t_pred.Historical_Sales)
                        if diff < min_diff:
                            min_diff = diff
                            match_ctrl = c_pred
                            
            if not match_ctrl and control_pool:
                for c_pred in control_pool:
                    if c_pred.Outlet_ID not in matched_control_ids:
                        match_ctrl = c_pred
                        break
                        
            if match_ctrl:
                matched_control_ids.add(match_ctrl.Outlet_ID)
                control_entry = CampaignOutlet(
                    campaign_id=campaign_id,
                    outlet_id=match_ctrl.Outlet_ID,
                    allocated_budget=0.0,
                    expected_lift_liters=0.0,
                    expected_roi=0.0,
                    group_type="control"
                )
                campaign_outlets.append(control_entry)
        
        # Clear any existing outlets for this campaign
        db.query(CampaignOutlet).filter(CampaignOutlet.campaign_id == campaign_id).delete()
        
        # Save campaign outlets
        db.bulk_save_objects(campaign_outlets)
        
        # Update campaign status
        campaign.status = "Active"
        db.commit()
        db.refresh(campaign)
        
        # Auto-generate snapshots for testing
        from app.services.monitoring_service import MonitoringService
        MonitoringService.generate_mock_snapshots(db, campaign_id)
        
        return campaign
