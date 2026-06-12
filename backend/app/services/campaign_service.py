from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from db.models import Campaign, CampaignOutlet, Outlet, Prediction, MonitoringSnapshot
from app.models.schemas import CampaignCreateSchema, CampaignSimulationCreateSchema
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
            outlet_type=campaign_in.outlet_type,
            outlet_size=campaign_in.outlet_size,
            b_param=campaign_in.b_param,
            status="Draft"
        )
        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)
        return db_campaign

    @staticmethod
    def create_campaign_from_simulation(db: Session, campaign_in: CampaignSimulationCreateSchema) -> Campaign:
        # 1. Create campaign in Active status directly since it is instantiated from optimization
        db_campaign = Campaign(
            campaign_name=campaign_in.campaign_name,
            province=campaign_in.province,
            start_date=campaign_in.start_date,
            end_date=campaign_in.end_date,
            total_budget=campaign_in.total_budget,
            outlet_type=campaign_in.outlet_type,
            outlet_size=campaign_in.outlet_size,
            b_param=campaign_in.b_param,
            status="Active"
        )
        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)

        # 2. Run KKT optimization solver on the specific subset using campaign settings
        from app.services.optimization_service import OptimizationService
        opt_res = OptimizationService.optimize_budget(
            db,
            budget=campaign_in.total_budget,
            b_param=campaign_in.b_param,
            province=campaign_in.province,
            outlet_type=campaign_in.outlet_type,
            outlet_size=campaign_in.outlet_size
        )

        allocations = opt_res.get("allocations", [])
        allocations.sort(key=lambda x: x.Allocated_Budget, reverse=True)

        # Filter out outlets that received 0 or very small budgets (<= 0.01)
        active_allocs = [a for a in allocations if a.Allocated_Budget > 0.01]
        
        top_n = campaign_in.top_n
        if len(active_allocs) < top_n:
            top_n = len(active_allocs)
            
        if top_n == 0:
            if len(allocations) > 0:
                active_allocs = allocations[:campaign_in.top_n]
                top_n = len(active_allocs)
            else:
                return db_campaign

        treatment_allocs = active_allocs[:top_n]
        treatment_ids = {a.Outlet_ID for a in treatment_allocs}

        # 3. Get control pool from same segment (province, type, size)
        query_outlets = db.query(Outlet).filter(Outlet.Province == campaign_in.province)
        if campaign_in.outlet_type:
            query_outlets = query_outlets.filter(Outlet.Outlet_Type == campaign_in.outlet_type)
        if campaign_in.outlet_size:
            query_outlets = query_outlets.filter(Outlet.Outlet_Size == campaign_in.outlet_size)
        outlets = query_outlets.all()
        outlet_ids = [o.Outlet_ID for o in outlets]

        # Prefetch outlets and predictions for treatment group
        treatment_outlets = db.query(Outlet).filter(Outlet.Outlet_ID.in_(list(treatment_ids))).all()
        treatment_preds = db.query(Prediction).filter(Prediction.Outlet_ID.in_(list(treatment_ids))).all()

        # Build in-memory lookup maps
        outlet_map = {o.Outlet_ID: o for o in outlets}
        for o in treatment_outlets:
            outlet_map[o.Outlet_ID] = o
            
        control_pool = db.query(Prediction).filter(
            Prediction.Outlet_ID.in_(outlet_ids),
            ~Prediction.Outlet_ID.in_(treatment_ids)
        ).all()

        pred_map = {p.Outlet_ID: p for p in control_pool}
        for p in treatment_preds:
            pred_map[p.Outlet_ID] = p

        campaign_outlets = []
        matched_control_ids = set()

        for alloc in treatment_allocs:
            t_outlet = outlet_map.get(alloc.Outlet_ID)
            t_pred = pred_map.get(alloc.Outlet_ID)
            if not t_outlet or not t_pred:
                continue

            treatment_entry = CampaignOutlet(
                campaign_id=db_campaign.campaign_id,
                outlet_id=alloc.Outlet_ID,
                allocated_budget=alloc.Allocated_Budget,
                expected_lift_liters=alloc.Expected_Lift,
                expected_roi=alloc.ROI,
                group_type="treatment"
            )
            campaign_outlets.append(treatment_entry)

            # Nearest Neighbor Control matching in same segment (using in-memory map lookup)
            match_ctrl = None
            min_diff = float('inf')

            for c_pred in control_pool:
                if c_pred.Outlet_ID in matched_control_ids:
                    continue

                c_outlet = outlet_map.get(c_pred.Outlet_ID)
                if c_outlet and c_outlet.Outlet_Type == t_outlet.Outlet_Type and c_outlet.Outlet_Size == t_outlet.Outlet_Size:
                    diff = abs(c_pred.Historical_Sales - t_pred.Historical_Sales)
                    if diff < min_diff:
                        min_diff = diff
                        match_ctrl = c_pred

            if not match_ctrl:
                for c_pred in control_pool:
                    if c_pred.Outlet_ID in matched_control_ids:
                        continue
                    c_outlet = outlet_map.get(c_pred.Outlet_ID)
                    if c_outlet and c_outlet.Outlet_Type == t_outlet.Outlet_Type:
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
                    campaign_id=db_campaign.campaign_id,
                    outlet_id=match_ctrl.Outlet_ID,
                    allocated_budget=0.0,
                    expected_lift_liters=0.0,
                    expected_roi=0.0,
                    group_type="control"
                )
                campaign_outlets.append(control_entry)

        db.bulk_save_objects(campaign_outlets)
        db.commit()

        # Seed monitoring snapshots for this campaign
        from app.services.monitoring_service import MonitoringService
        MonitoringService.generate_mock_snapshots(db, db_campaign.campaign_id)

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
        
        # Build maps for instant in-memory lookup
        outlet_map = {o.Outlet_ID: o for o in outlets}
        
        # Control pool contains all outlets in province except the treatment ones
        control_pool = db.query(Prediction).filter(
            Prediction.Outlet_ID.in_(outlet_ids),
            ~Prediction.Outlet_ID.in_(treatment_ids)
        ).all()
        
        treatment_preds = db.query(Prediction).filter(
            Prediction.Outlet_ID.in_(list(treatment_ids))
        ).all()
        
        pred_map = {p.Outlet_ID: p for p in control_pool}
        for p in treatment_preds:
            pred_map[p.Outlet_ID] = p
            
        campaign_outlets = []
        matched_control_ids = set()
        
        for alloc in treatment_allocs:
            t_outlet = outlet_map.get(alloc.Outlet_ID)
            t_pred = pred_map.get(alloc.Outlet_ID)
            if not t_outlet or not t_pred:
                continue
            
            treatment_entry = CampaignOutlet(
                campaign_id=campaign_id,
                outlet_id=alloc.Outlet_ID,
                allocated_budget=alloc.Allocated_Budget,
                expected_lift_liters=alloc.Expected_Lift,
                expected_roi=alloc.ROI,
                group_type="treatment"
            )
            campaign_outlets.append(treatment_entry)
            
            # Nearest Neighbor Control Outlet Matching (in-memory)
            match_ctrl = None
            min_diff = float('inf')
            
            for c_pred in control_pool:
                if c_pred.Outlet_ID in matched_control_ids:
                    continue
                    
                c_outlet = outlet_map.get(c_pred.Outlet_ID)
                if c_outlet and c_outlet.Outlet_Type == t_outlet.Outlet_Type and c_outlet.Outlet_Size == t_outlet.Outlet_Size:
                    diff = abs(c_pred.Historical_Sales - t_pred.Historical_Sales)
                    if diff < min_diff:
                        min_diff = diff
                        match_ctrl = c_pred
            
            if not match_ctrl:
                for c_pred in control_pool:
                    if c_pred.Outlet_ID in matched_control_ids:
                        continue
                    c_outlet = outlet_map.get(c_pred.Outlet_ID)
                    if c_outlet and c_outlet.Outlet_Type == t_outlet.Outlet_Type:
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

    @staticmethod
    def end_campaign(db: Session, campaign_id: int) -> Optional[Campaign]:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return None
        campaign.status = "Completed"
        db.commit()
        db.refresh(campaign)
        return campaign
