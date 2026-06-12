from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from db.models import Campaign, CampaignOutlet, ReallocationRecommendation, Outlet, Prediction, MonitoringSnapshot
from app.services.monitoring_service import MonitoringService
import math
import datetime

class ReallocationService:
    @staticmethod
    def generate_recommendations(db: Session, campaign_id: int) -> List[ReallocationRecommendation]:
        """
        Scan treatment outlets, identify underperformers, retract budgets, 
        and re-optimize campaign budget over active and alternative outlets.
        """
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return []

        # Clear existing recommendations
        db.query(ReallocationRecommendation).filter(ReallocationRecommendation.campaign_id == campaign_id).delete()
        db.commit()

        # Fetch treatment outlets
        treatment_outlets = db.query(CampaignOutlet).filter(
            CampaignOutlet.campaign_id == campaign_id,
            CampaignOutlet.group_type == "treatment"
        ).all()

        recommendations = []
        underperforming_ids = set()
        active_treatment_outlets = []

        # 1. Identify underperformers (actual lift < 40% of expected lift)
        for co in treatment_outlets:
            actual_lift = db.query(func.sum(MonitoringSnapshot.actual_lift)).filter(
                MonitoringSnapshot.campaign_id == campaign_id,
                MonitoringSnapshot.outlet_id == co.outlet_id
            ).scalar() or 0.0

            expected_lift = co.expected_lift_liters
            
            # Underperformer threshold: < 40% of expected lift
            if co.allocated_budget > 0.01 and actual_lift < (expected_lift * 0.40):
                underperforming_ids.add(co.outlet_id)
                perf_pct = (actual_lift / expected_lift * 100.0) if expected_lift > 0 else 0.0
                
                # Recommend retracting budget
                rec = ReallocationRecommendation(
                    campaign_id=campaign_id,
                    outlet_id=co.outlet_id,
                    current_budget=co.allocated_budget,
                    recommended_budget=0.0,
                    expected_improvement=0.0,
                    recommendation_reason=f"Retract budget: Outlet severely underperforming (achieved only {perf_pct:.1f}% of expected lift)."
                )
                recommendations.append(rec)
            else:
                active_treatment_outlets.append(co)

        # Only run reallocation/re-optimization if we actually retracted some budget from underperformers
        if len(underperforming_ids) > 0:
            # 2. Find top 2 alternative outlets in the province/type/size that are NOT in the campaign
            campaign_outlet_ids = [o.outlet_id for o in db.query(CampaignOutlet).filter(CampaignOutlet.campaign_id == campaign_id).all()]
            
            query_alts = db.query(Outlet).filter(
                Outlet.Province == campaign.province,
                ~Outlet.Outlet_ID.in_(campaign_outlet_ids)
            )
            if campaign.outlet_type:
                query_alts = query_alts.filter(Outlet.Outlet_Type == campaign.outlet_type)
            if campaign.outlet_size:
                query_alts = query_alts.filter(Outlet.Outlet_Size == campaign.outlet_size)
                
            province_outlets = query_alts.all()
            province_outlet_ids = [o.Outlet_ID for o in province_outlets]

            # Query predictions for alternative outlets, order by Opportunity Gap descending
            alternative_preds = db.query(Prediction).filter(
                Prediction.Outlet_ID.in_(province_outlet_ids)
            ).order_by(Prediction.Opportunity_Gap.desc()).limit(2).all()

            # 3. Combine active treatment outlets and alternative outlets for re-optimization
            outlet_ids_to_optimize = [co.outlet_id for co in active_treatment_outlets] + [alt.Outlet_ID for alt in alternative_preds]
            
            if len(outlet_ids_to_optimize) > 0:
                # Query predictions for y_hist and recompute Upper Bounds
                preds = db.query(Prediction).filter(Prediction.Outlet_ID.in_(outlet_ids_to_optimize)).all()
                pred_map = {p.Outlet_ID: p for p in preds}
                
                ordered_ids = []
                y_hist_list = []
                upper_bounds_list = []
                b_param = campaign.b_param if campaign.b_param else 0.0005

                for oid in outlet_ids_to_optimize:
                    if oid in pred_map:
                        p = pred_map[oid]
                        ordered_ids.append(oid)
                        y_hist_list.append(p.Historical_Sales)
                        
                        a_i = max(p.Historical_Sales, 1.0)
                        headroom = max(p.Predicted_Potential - p.Historical_Sales, 0.0)
                        ratio = min(headroom / a_i, 50.0)
                        ub = (math.exp(ratio) - 1.0) / b_param
                        upper_bounds_list.append(ub)

                import numpy as np
                y_hist = np.array(y_hist_list)
                upper_bounds = np.array(upper_bounds_list)

                # Re-run KKT optimizer with campaign total budget
                from app.services.optimization_service import OptimizationService
                opt_res = OptimizationService.solve_kkt(ordered_ids, y_hist, upper_bounds, budget=campaign.total_budget, b_param=b_param)
                
                # Build maps of current budgets
                current_budgets = {co.outlet_id: co.allocated_budget for co in active_treatment_outlets}
                for alt in alternative_preds:
                    current_budgets[alt.Outlet_ID] = 0.0
                
                # Check allocations
                for alloc in opt_res.get("allocations", []):
                    oid = alloc.Outlet_ID
                    curr_b = current_budgets.get(oid, 0.0)
                    recom_b = alloc.Allocated_Budget
                    
                    if abs(recom_b - curr_b) > 1.0: # threshold of LKR 1 difference
                        is_alt = (oid in [alt.Outlet_ID for alt in alternative_preds])
                        
                        if is_alt and recom_b > 0.01:
                            rec = ReallocationRecommendation(
                                campaign_id=campaign_id,
                                outlet_id=oid,
                                current_budget=0.0,
                                recommended_budget=recom_b,
                                expected_improvement=alloc.Expected_Lift,
                                recommendation_reason=f"Reallocate budget: High-potential alternative in {campaign.province} Province selected by KKT optimization."
                            )
                            recommendations.append(rec)
                        elif not is_alt:
                            co_record = next(c for c in active_treatment_outlets if c.outlet_id == oid)
                            lift_diff = alloc.Expected_Lift - co_record.expected_lift_liters
                            
                            if recom_b > curr_b:
                                reason = f"Reallocate budget: Boost spend by KKT optimization solver to maximize campaign ROI."
                            else:
                                reason = f"Reallocate budget: Scale down spend by KKT optimization solver to prioritize better opportunities."
                                
                            rec = ReallocationRecommendation(
                                campaign_id=campaign_id,
                                outlet_id=oid,
                                current_budget=curr_b,
                                recommended_budget=recom_b,
                                expected_improvement=round(lift_diff, 2),
                                recommendation_reason=reason
                            )
                            recommendations.append(rec)

        if recommendations:
            db.bulk_save_objects(recommendations)
            db.commit()

        # Re-fetch with relationships loaded
        return db.query(ReallocationRecommendation).filter(ReallocationRecommendation.campaign_id == campaign_id).all()

    @staticmethod
    def apply_recommendations(db: Session, campaign_id: int):
        """
        Apply budget recommendations: retract spend, add alternative treatment outlets, 
        match control groups for new entries, clear recommendations, and regenerate snapshots.
        """
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return

        recs = db.query(ReallocationRecommendation).filter(ReallocationRecommendation.campaign_id == campaign_id).all()
        if not recs:
            return

        for r in recs:
            # Case 1: Retracting budget from underperformer
            if r.recommended_budget == 0.0:
                co = db.query(CampaignOutlet).filter(
                    CampaignOutlet.campaign_id == campaign_id,
                    CampaignOutlet.outlet_id == r.outlet_id
                ).first()
                if co:
                    co.allocated_budget = 0.0
                    co.expected_lift_liters = 0.0
                    co.expected_roi = 0.0
                    # We can mark it as control or keep it as treatment with 0 budget
                    
            # Case 2: Shifting budget to alternative outlet
            elif r.current_budget == 0.0:
                # Add alternative outlet as a treatment outlet
                new_co = CampaignOutlet(
                    campaign_id=campaign_id,
                    outlet_id=r.outlet_id,
                    allocated_budget=r.recommended_budget,
                    expected_lift_liters=r.expected_improvement,
                    expected_roi=round(r.expected_improvement / r.recommended_budget, 5) if r.recommended_budget > 0 else 0.0,
                    group_type="treatment"
                )
                db.add(new_co)
                
                # Match a control outlet for this new treatment outlet
                t_outlet = db.query(Outlet).filter(Outlet.Outlet_ID == r.outlet_id).first()
                t_pred = db.query(Prediction).filter(Prediction.Outlet_ID == r.outlet_id).first()
                
                campaign_outlet_ids = [o.outlet_id for o in db.query(CampaignOutlet).filter(CampaignOutlet.campaign_id == campaign_id).all()]
                campaign_outlet_ids.append(r.outlet_id) # exclude self
                
                control_pool_outlets = db.query(Outlet).filter(
                    Outlet.Province == campaign.province,
                    ~Outlet.Outlet_ID.in_(campaign_outlet_ids)
                ).all()
                
                control_outlet_map = {o.Outlet_ID: o for o in control_pool_outlets}
                control_pool_ids = [o.Outlet_ID for o in control_pool_outlets]
                control_pool = db.query(Prediction).filter(Prediction.Outlet_ID.in_(control_pool_ids)).all()
                
                match_ctrl = None
                min_diff = float('inf')
                for c_pred in control_pool:
                    c_outlet = control_outlet_map.get(c_pred.Outlet_ID)
                    if c_outlet and c_outlet.Outlet_Type == t_outlet.Outlet_Type and c_outlet.Outlet_Size == t_outlet.Outlet_Size:
                        diff = abs(c_pred.Historical_Sales - t_pred.Historical_Sales)
                        if diff < min_diff:
                            min_diff = diff
                            match_ctrl = c_pred
                
                if not match_ctrl and control_pool:
                    match_ctrl = control_pool[0]
                    
                if match_ctrl:
                    control_entry = CampaignOutlet(
                        campaign_id=campaign_id,
                        outlet_id=match_ctrl.Outlet_ID,
                        allocated_budget=0.0,
                        expected_lift_liters=0.0,
                        expected_roi=0.0,
                        group_type="control"
                    )
                    db.add(control_entry)

        # Clear recommendations
        db.query(ReallocationRecommendation).filter(ReallocationRecommendation.campaign_id == campaign_id).delete()
        db.commit()

        # Regenerate simulated monitoring snapshots for the updated campaign outlet allocations
        MonitoringService.generate_mock_snapshots(db, campaign_id)
        
        # Recalculate impact analysis (DiD) if it was already evaluated
        from app.services.evaluation_service import EvaluationService
        try:
            EvaluationService.calculate_did(db, campaign_id)
        except Exception:
            pass
            
        db.commit()
