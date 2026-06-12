from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from db.models import Campaign, CampaignOutlet, MonitoringSnapshot, Outlet, Prediction, OutletHistory
import datetime

class MonitoringService:
    @staticmethod
    def get_pre_volume_baseline(db: Session, outlet_id: str, campaign_start_date_str: str) -> float:
        """
        Dynamically calculate the Pre Volume by querying the database 
        for the volume of the last 3 months from the campaign start date.
        """
        try:
            parts = campaign_start_date_str.split("-")
            year = int(parts[0])
            month = int(parts[1])
        except (IndexError, ValueError):
            year = 2026
            month = 3

        # Resolve year & month for the last 3 months
        prev_months = []
        cy, cm = year, month
        for _ in range(3):
            cm -= 1
            if cm == 0:
                cm = 12
                cy -= 1
            prev_months.append((cy, cm))

        # Query history
        history_records = db.query(OutletHistory).filter(
            OutletHistory.Outlet_ID == outlet_id,
            (
                ((OutletHistory.Year == prev_months[0][0]) & (OutletHistory.Month == prev_months[0][1])) |
                ((OutletHistory.Year == prev_months[1][0]) & (OutletHistory.Month == prev_months[1][1])) |
                ((OutletHistory.Year == prev_months[2][0]) & (OutletHistory.Month == prev_months[2][1]))
            )
        ).all()

        if history_records:
            return sum(r.Volume_Liters for r in history_records) / len(history_records)

        # Fallback 1: Get latest 3 historical months available
        fallback_records = db.query(OutletHistory).filter(
            OutletHistory.Outlet_ID == outlet_id
        ).order_by(OutletHistory.Year.desc(), OutletHistory.Month.desc()).limit(3).all()
        if fallback_records:
            return sum(r.Volume_Liters for r in fallback_records) / len(fallback_records)

        # Fallback 2: Prediction Historical_Sales
        pred = db.query(Prediction).filter(Prediction.Outlet_ID == outlet_id).first()
        if pred:
            return pred.Historical_Sales
            
        return 100.0

    @staticmethod
    def generate_mock_snapshots(db: Session, campaign_id: int):
        """
        Generate mock weekly performance snapshots for treatment and control outlets.
        """
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return

        camp_outlets = db.query(CampaignOutlet).filter(CampaignOutlet.campaign_id == campaign_id).all()
        if not camp_outlets:
            return

        # Clear any existing snapshots
        db.query(MonitoringSnapshot).filter(MonitoringSnapshot.campaign_id == campaign_id).delete()

        snapshots = []
        
        # Parse campaign start date
        try:
            start_dt = datetime.datetime.strptime(campaign.start_date, "%Y-%m-%d")
        except ValueError:
            start_dt = datetime.datetime.now()

        dates = [(start_dt + datetime.timedelta(days=7 * (i + 1))).strftime("%Y-%m-%d") for i in range(4)]

        for idx_co, co in enumerate(camp_outlets):
            # Dynamic calculation of pre-intervention baseline volume (monthly)
            monthly_pre_vol = MonitoringService.get_pre_volume_baseline(db, co.outlet_id, campaign.start_date)
            # Weekly base volume
            weekly_base_vol = monthly_pre_vol / 4.0

            for idx_date, dt in enumerate(dates):
                if co.group_type == "treatment":
                    # Mark one outlet as underperforming to test reallocation (e.g. index 2 or 3)
                    is_underperforming = (idx_co % 5 == 2)
                    
                    if is_underperforming:
                        lift_factor = 0.15  # 15% of expected lift
                        notes = "Underperforming: supply chain stockout and chiller downtime."
                    else:
                        lift_factor = 1.05 + (0.05 * (idx_date % 2))  # Performs slightly better than expected
                        notes = "Good performance: active customer engagement and proper merchandising."
                    
                    # expected lift is monthly, slice it weekly
                    weekly_expected_lift = co.expected_lift_liters / 4.0
                    actual_lift = weekly_expected_lift * lift_factor
                    actual_vol = weekly_base_vol + actual_lift
                else:
                    # Control outlets receive no budget, hover around baseline with noise
                    actual_lift = 0.0
                    noise = 0.98 + (0.04 * ((idx_co + idx_date) % 2))
                    actual_vol = weekly_base_vol * noise
                    notes = "Control matched baseline."

                snapshots.append(MonitoringSnapshot(
                    campaign_id=campaign_id,
                    outlet_id=co.outlet_id,
                    snapshot_date=dt,
                    actual_volume=round(actual_vol, 2),
                    actual_revenue=round(actual_vol * 120.0, 2),  # Estimated price of Rs 120 per liter
                    actual_lift=round(actual_lift, 2),
                    notes=notes
                ))

        db.bulk_save_objects(snapshots)
        db.commit()

    @staticmethod
    def get_monitoring_summary(db: Session, campaign_id: int) -> Dict[str, Any]:
        """
        Compute campaign monitoring summary, status, and chart datasets.
        """
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return {}

        treatment_outlets = db.query(CampaignOutlet).filter(
            CampaignOutlet.campaign_id == campaign_id,
            CampaignOutlet.group_type == "treatment"
        ).all()
        
        allocated_budget = sum(co.allocated_budget for co in treatment_outlets)
        expected_lift = sum(co.expected_lift_liters for co in treatment_outlets)

        # Query actual volumes and actual lifts from snapshots for treatment outlets
        treatment_ids = [co.outlet_id for co in treatment_outlets]
        
        actual_lift_sum = db.query(func.sum(MonitoringSnapshot.actual_lift)).filter(
            MonitoringSnapshot.campaign_id == campaign_id,
            MonitoringSnapshot.outlet_id.in_(treatment_ids)
        ).scalar() or 0.0

        actual_revenue_sum = db.query(func.sum(MonitoringSnapshot.actual_revenue)).filter(
            MonitoringSnapshot.campaign_id == campaign_id,
            MonitoringSnapshot.outlet_id.in_(treatment_ids)
        ).scalar() or 0.0

        roi = actual_lift_sum / allocated_budget if allocated_budget > 0 else 0.0

        # Build outlet-wise list for traffic lights and tables
        outlet_performance = []
        underperforming_count = 0

        for co in treatment_outlets:
            outlet = db.query(Outlet).filter(Outlet.Outlet_ID == co.outlet_id).first()
            
            # Sum actual lift from snapshots
            outlet_actual_lift = db.query(func.sum(MonitoringSnapshot.actual_lift)).filter(
                MonitoringSnapshot.campaign_id == campaign_id,
                MonitoringSnapshot.outlet_id == co.outlet_id
            ).scalar() or 0.0
            
            # Fetch latest snapshot note
            latest_snap = db.query(MonitoringSnapshot).filter(
                MonitoringSnapshot.campaign_id == campaign_id,
                MonitoringSnapshot.outlet_id == co.outlet_id
            ).order_by(MonitoringSnapshot.snapshot_date.desc()).first()
            
            notes = latest_snap.notes if latest_snap else ""
            
            # Performance status (Traffic Lights: Green, Yellow, Red)
            perf_pct = (outlet_actual_lift / co.expected_lift_liters) if co.expected_lift_liters > 0 else 1.0
            if perf_pct >= 0.8:
                status = "Green"
            elif perf_pct >= 0.4:
                status = "Yellow"
            else:
                status = "Red"
                underperforming_count += 1

            outlet_performance.append({
                "outlet_id": co.outlet_id,
                "outlet_name": outlet.Outlet_Name if outlet else f"Outlet {co.outlet_id}",
                "distributor": outlet.Distributor if outlet else "Unknown",
                "allocated_budget": co.allocated_budget,
                "expected_lift": co.expected_lift_liters,
                "actual_lift": round(outlet_actual_lift, 2),
                "roi": round(outlet_actual_lift / co.allocated_budget, 5) if co.allocated_budget > 0 else 0.0,
                "performance_pct": round(perf_pct * 100.0, 1),
                "status": status,
                "notes": notes
            })

        # Chart 1: Expected vs Actual Lift
        expected_vs_actual_chart = [
            {
                "outlet_id": op["outlet_id"],
                "expected_lift": op["expected_lift"],
                "actual_lift": op["actual_lift"]
            }
            for op in outlet_performance
        ]

        # Chart 2: Budget vs ROI
        budget_vs_roi_chart = [
            {
                "outlet_id": op["outlet_id"],
                "budget": op["allocated_budget"],
                "roi": op["roi"]
            }
            for op in outlet_performance
        ]

        # Chart 3: Province Performance (Distributor breakdowns for this campaign)
        distributor_map = {}
        for op in outlet_performance:
            dist = op["distributor"]
            if dist not in distributor_map:
                distributor_map[dist] = {"budget": 0.0, "actual_lift": 0.0}
            distributor_map[dist]["budget"] += op["allocated_budget"]
            distributor_map[dist]["actual_lift"] += op["actual_lift"]

        province_perf_chart = [
            {
                "distributor": dist,
                "budget": round(stats["budget"], 2),
                "actual_lift": round(stats["actual_lift"], 2),
                "roi": round(stats["actual_lift"] / stats["budget"], 5) if stats["budget"] > 0 else 0.0
            }
            for dist, stats in distributor_map.items()
        ]

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.campaign_name,
            "status": campaign.status,
            "allocated_budget": round(allocated_budget, 2),
            "expected_lift": round(expected_lift, 2),
            "actual_lift": round(actual_lift_sum, 2),
            "roi": round(roi, 5),
            "actual_revenue": round(actual_revenue_sum, 2),
            "underperforming_outlets": underperforming_count,
            "outlets_performance": outlet_performance,
            "charts": {
                "expected_vs_actual": expected_vs_actual_chart,
                "budget_vs_roi": budget_vs_roi_chart,
                "province_performance": province_perf_chart
            }
        }

    @staticmethod
    def get_outlet_snapshots(db: Session, campaign_id: int, outlet_id: str) -> List[MonitoringSnapshot]:
        return db.query(MonitoringSnapshot).filter(
            MonitoringSnapshot.campaign_id == campaign_id,
            MonitoringSnapshot.outlet_id == outlet_id
        ).order_by(MonitoringSnapshot.snapshot_date).all()
