import os
import sys
import datetime

# Setup path to import backend modules
db_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(db_dir)
sys.path.insert(0, backend_dir)

from db.database import engine, Base, SessionLocal
from db.models import Campaign, CampaignOutlet, MonitoringSnapshot, ImpactAnalysis, Outlet, Prediction

def main():
    print("Initializing campaign tables in SQLite database...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if campaigns already exist
        existing_campaigns = db.query(Campaign).count()
        if existing_campaigns > 0:
            print("Campaigns already exist. Seeding skipped.")
            return

        print("Seeding campaigns...")
        
        # 1. Seed a Draft Campaign
        draft_campaign = Campaign(
            campaign_name="Western Province Pilot v1",
            province="Western",
            start_date="2026-06-01",
            end_date="2026-06-30",
            total_budget=1500000.0,
            status="Draft"
        )
        db.add(draft_campaign)
        
        # 2. Seed an Active Campaign (Southern Region pilot)
        active_campaign = Campaign(
            campaign_name="Southern Region Launch",
            province="Southern",
            start_date="2026-03-01",
            end_date="2026-03-31",
            total_budget=2000000.0,
            status="Active"
        )
        db.add(active_campaign)
        db.commit() # Commit to get IDs
        
        print(f"Created Campaign {draft_campaign.campaign_name} (ID: {draft_campaign.campaign_id})")
        print(f"Created Campaign {active_campaign.campaign_name} (ID: {active_campaign.campaign_id})")
        
        # Match treatment and control outlets for the active campaign
        # Query outlets in Southern province
        southern_outlets = db.query(Outlet).filter(Outlet.Province == "Southern").all()
        if not southern_outlets:
            # Fallback to Western if Southern not found
            southern_outlets = db.query(Outlet).filter(Outlet.Province == "Western").all()
            active_campaign.province = "Western"
            db.commit()
            
        print(f"Found {len(southern_outlets)} outlets in {active_campaign.province} province.")
        
        # Grab predictions to rank by opportunity gap
        outlet_ids = [o.Outlet_ID for o in southern_outlets]
        preds = db.query(Prediction).filter(Prediction.Outlet_ID.in_(outlet_ids)).order_by(Prediction.Opportunity_Gap.desc()).all()
        
        if len(preds) >= 10:
            treatment_preds = preds[:5]
            control_pool = preds[5:]
            
            # Create CampaignOutlet records
            campaign_outlets = []
            
            budget_per_outlet = active_campaign.total_budget / len(treatment_preds)
            
            for t_pred in treatment_preds:
                t_outlet = db.query(Outlet).filter(Outlet.Outlet_ID == t_pred.Outlet_ID).first()
                # Find matching control outlet: same type & size, nearest historical sales
                match_ctrl = None
                min_diff = float('inf')
                
                for c_pred in control_pool:
                    c_outlet = db.query(Outlet).filter(Outlet.Outlet_ID == c_pred.Outlet_ID).first()
                    if c_outlet.Outlet_Type == t_outlet.Outlet_Type and c_outlet.Outlet_Size == t_outlet.Outlet_Size:
                        diff = abs(c_pred.Historical_Sales - t_pred.Historical_Sales)
                        if diff < min_diff:
                            min_diff = diff
                            match_ctrl = c_pred
                
                if not match_ctrl and control_pool:
                    # Fallback to any control outlet
                    match_ctrl = control_pool[0]
                
                # Add treatment
                b_param = 0.0005
                a = max(t_pred.Historical_Sales, 1.0)
                expected_lift = a * (1.1 * (budget_per_outlet * b_param) / (1.0 + budget_per_outlet * b_param))
                expected_roi = expected_lift / budget_per_outlet
                
                treatment_entry = CampaignOutlet(
                    campaign_id=active_campaign.campaign_id,
                    outlet_id=t_pred.Outlet_ID,
                    allocated_budget=budget_per_outlet,
                    expected_lift_liters=round(expected_lift, 2),
                    expected_roi=round(expected_roi, 5),
                    group_type="treatment"
                )
                campaign_outlets.append(treatment_entry)
                
                # Add matched control
                if match_ctrl:
                    control_entry = CampaignOutlet(
                        campaign_id=active_campaign.campaign_id,
                        outlet_id=match_ctrl.Outlet_ID,
                        allocated_budget=0.0,
                        expected_lift_liters=0.0,
                        expected_roi=0.0,
                        group_type="control"
                    )
                    campaign_outlets.append(control_entry)
                    # remove from pool so it's not matched twice
                    control_pool = [c for c in control_pool if c.Outlet_ID != match_ctrl.Outlet_ID]
            
            db.bulk_save_objects(campaign_outlets)
            db.commit()
            print(f"Associated {len(campaign_outlets)} outlets (treatment and control) to campaign {active_campaign.campaign_name}")
            
            # Seed mock monitoring snapshots for the active campaign
            snapshots = []
            dates = ["2026-03-07", "2026-03-14", "2026-03-21", "2026-03-28"]
            
            # Requery loaded outlets to get details
            camp_outlets = db.query(CampaignOutlet).filter(CampaignOutlet.campaign_id == active_campaign.campaign_id).all()
            
            for co in camp_outlets:
                pred = db.query(Prediction).filter(Prediction.Outlet_ID == co.outlet_id).first()
                base_vol = pred.Historical_Sales / 4.0 # weekly slice
                
                for idx, dt in enumerate(dates):
                    # Treatment has lift, control is baseline
                    if co.group_type == "treatment":
                        # Introduce one underperformer (e.g. the 2nd treatment outlet)
                        is_underperformer = (co.outlet_id == camp_outlets[2].outlet_id)
                        if is_underperformer:
                            lift_factor = 0.1 # only 10% of expected lift
                            notes = "Refrigeration breakdown occurred."
                        else:
                            lift_factor = 1.05 + (0.05 * (idx % 2)) # slight overperformance
                            notes = "Normal campaign performance."
                        
                        actual_lift = (co.expected_lift_liters / 4.0) * lift_factor
                        actual_vol = base_vol + actual_lift
                    else:
                        actual_lift = 0.0
                        actual_vol = base_vol * (0.98 + 0.04 * (idx % 2)) # noise
                        notes = "Control outlet baseline."
                    
                    snapshots.append(MonitoringSnapshot(
                        campaign_id=active_campaign.campaign_id,
                        outlet_id=co.outlet_id,
                        snapshot_date=dt,
                        actual_volume=round(actual_vol, 2),
                        actual_revenue=round(actual_vol * 120.0, 2), # Rs 120 per liter
                        actual_lift=round(actual_lift, 2),
                        notes=notes
                    ))
            
            db.bulk_save_objects(snapshots)
            db.commit()
            print(f"Generated {len(snapshots)} monitoring snapshots for active campaign.")

        print("Database campaign seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding campaigns: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
