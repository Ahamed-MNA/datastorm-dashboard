from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from db.models import Campaign, CampaignOutlet, MonitoringSnapshot, ImpactAnalysis, Outlet, Prediction
from app.services.monitoring_service import MonitoringService
import datetime
import math

class EvaluationService:
    @staticmethod
    def get_outlet_volumes(db: Session, campaign_id: int, outlet_id: str, start_date_str: str) -> Dict[str, float]:
        """
        Helper to get pre-volume (monthly average of last 3 months) 
        and post-volume (sum of monitoring snapshots volume).
        """
        # Monthly Pre Volume (from history)
        pre_volume = MonitoringService.get_pre_volume_baseline(db, outlet_id, start_date_str)
        
        # Monthly Post Volume (average of weekly snapshots * 4.0)
        avg_weekly_volume = db.query(func.avg(MonitoringSnapshot.actual_volume)).filter(
            MonitoringSnapshot.campaign_id == campaign_id,
            MonitoringSnapshot.outlet_id == outlet_id
        ).scalar() or 0.0
        post_volume = avg_weekly_volume * 4.0
        
        return {
            "pre_volume": round(pre_volume, 2),
            "post_volume": round(post_volume, 2),
            "lift": round(post_volume - pre_volume, 2)
        }

    @staticmethod
    def calculate_pre_post(db: Session, campaign_id: int) -> Dict[str, Any]:
        """
        Pre-Post impact analysis for the treatment group.
        """
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return {}

        treatment_outlets = db.query(CampaignOutlet).filter(
            CampaignOutlet.campaign_id == campaign_id,
            CampaignOutlet.group_type == "treatment"
        ).all()

        if not treatment_outlets:
            return {}

        total_pre = 0.0
        total_post = 0.0
        details = []

        for co in treatment_outlets:
            outlet = db.query(Outlet).filter(Outlet.Outlet_ID == co.outlet_id).first()
            vols = EvaluationService.get_outlet_volumes(db, campaign_id, co.outlet_id, campaign.start_date)
            
            total_pre += vols["pre_volume"]
            total_post += vols["post_volume"]
            
            details.append({
                "outlet_id": co.outlet_id,
                "outlet_name": outlet.Outlet_Name if outlet else f"Outlet {co.outlet_id}",
                "pre_volume": vols["pre_volume"],
                "post_volume": vols["post_volume"],
                "lift": vols["lift"],
                "lift_pct": round((vols["lift"] / vols["pre_volume"] * 100.0) if vols["pre_volume"] > 0 else 0.0, 2)
            })

        n = len(treatment_outlets)
        avg_pre = total_pre / n
        avg_post = total_post / n
        avg_lift = avg_post - avg_pre
        avg_lift_pct = (avg_lift / avg_pre * 100.0) if avg_pre > 0 else 0.0

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.campaign_name,
            "sample_size": n,
            "average_pre": round(avg_pre, 2),
            "average_post": round(avg_post, 2),
            "average_lift": round(avg_lift, 2),
            "average_lift_pct": round(avg_lift_pct, 2),
            "outlets": details
        }

    @staticmethod
    def calculate_did(db: Session, campaign_id: int) -> ImpactAnalysis:
        """
        Econometric Difference-in-Differences (DiD) impact calculation.
        Saves and returns the ImpactAnalysis record.
        """
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            raise ValueError("Campaign not found")

        treatment_outlets = db.query(CampaignOutlet).filter(
            CampaignOutlet.campaign_id == campaign_id,
            CampaignOutlet.group_type == "treatment"
        ).all()

        control_outlets = db.query(CampaignOutlet).filter(
            CampaignOutlet.campaign_id == campaign_id,
            CampaignOutlet.group_type == "control"
        ).all()

        if not treatment_outlets or not control_outlets:
            raise ValueError("Treatment and control groups must both be populated for DiD analysis")

        t_lifts = []
        c_lifts = []
        t_pre_sum = 0.0
        t_post_sum = 0.0
        c_pre_sum = 0.0
        c_post_sum = 0.0

        for co in treatment_outlets:
            vols = EvaluationService.get_outlet_volumes(db, campaign_id, co.outlet_id, campaign.start_date)
            t_lifts.append(vols["lift"])
            t_pre_sum += vols["pre_volume"]
            t_post_sum += vols["post_volume"]

        for co in control_outlets:
            vols = EvaluationService.get_outlet_volumes(db, campaign_id, co.outlet_id, campaign.start_date)
            c_lifts.append(vols["lift"])
            c_pre_sum += vols["pre_volume"]
            c_post_sum += vols["post_volume"]

        n_t = len(treatment_outlets)
        n_c = len(control_outlets)

        avg_t_lift = sum(t_lifts) / n_t
        avg_c_lift = sum(c_lifts) / n_c
        did_effect = avg_t_lift - avg_c_lift

        # Econometric Confidence Level estimation using t-statistic
        # Calculate variances
        var_t = sum((x - avg_t_lift) ** 2 for x in t_lifts) / (n_t - 1) if n_t > 1 else 0.1
        var_c = sum((x - avg_c_lift) ** 2 for x in c_lifts) / (n_c - 1) if n_c > 1 else 0.1
        
        # Standard error
        se = math.sqrt((var_t / n_t) + (var_c / n_c))
        
        if se > 0:
            t_stat = did_effect / se
            # Convert t-statistic to confidence level approximation (one-tailed)
            # Sigmoid approximation of t-distribution cumulative probability
            confidence_score = min(0.99, max(0.50, 1.0 - 0.5 * math.exp(-0.71 * abs(t_stat))))
        else:
            confidence_score = 0.95

        # Check for existing analysis
        analysis = db.query(ImpactAnalysis).filter(ImpactAnalysis.campaign_id == campaign_id).first()
        if not analysis:
            analysis = ImpactAnalysis(campaign_id=campaign_id)
            db.add(analysis)

        analysis.pre_volume = round(t_pre_sum / n_t, 2)
        analysis.post_volume = round(t_post_sum / n_t, 2)
        analysis.treatment_lift = round(avg_t_lift, 2)
        analysis.control_lift = round(avg_c_lift, 2)
        analysis.did_effect = round(did_effect, 2)
        analysis.confidence_score = round(confidence_score, 4)
        analysis.generated_at = datetime.datetime.utcnow().isoformat()

        db.commit()
        db.refresh(analysis)
        return analysis

    @staticmethod
    def get_did_evaluation_details(db: Session, campaign_id: int) -> Dict[str, Any]:
        """
        Get the difference-in-differences report, along with side-by-side treatment-control pairs.
        """
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return {}

        analysis = db.query(ImpactAnalysis).filter(ImpactAnalysis.campaign_id == campaign_id).first()
        if not analysis:
            # Calculate on-the-fly
            try:
                analysis = EvaluationService.calculate_did(db, campaign_id)
            except Exception:
                analysis = None

        # Gather matched pairs
        treatment_outlets = db.query(CampaignOutlet).filter(
            CampaignOutlet.campaign_id == campaign_id,
            CampaignOutlet.group_type == "treatment"
        ).all()

        control_outlets = db.query(CampaignOutlet).filter(
            CampaignOutlet.campaign_id == campaign_id,
            CampaignOutlet.group_type == "control"
        ).all()

        pairs = []
        for idx, t_co in enumerate(treatment_outlets):
            t_outlet = db.query(Outlet).filter(Outlet.Outlet_ID == t_co.outlet_id).first()
            t_vols = EvaluationService.get_outlet_volumes(db, campaign_id, t_co.outlet_id, campaign.start_date)

            # Match 1-to-1 index-wise or find matching control
            # Seeder matches control pool in order, so index-matching or nearest type-size matching works
            c_co = None
            if idx < len(control_outlets):
                c_co = control_outlets[idx]
            else:
                c_co = control_outlets[0] if control_outlets else None

            c_outlet = None
            c_vols = {"pre_volume": 0.0, "post_volume": 0.0, "lift": 0.0}
            if c_co:
                c_outlet = db.query(Outlet).filter(Outlet.Outlet_ID == c_co.outlet_id).first()
                c_vols = EvaluationService.get_outlet_volumes(db, campaign_id, c_co.outlet_id, campaign.start_date)

            pairs.append({
                "treatment_id": t_co.outlet_id,
                "treatment_name": t_outlet.Outlet_Name if t_outlet else f"Outlet {t_co.outlet_id}",
                "treatment_type": t_outlet.Outlet_Type if t_outlet else "Unknown",
                "treatment_size": t_outlet.Outlet_Size if t_outlet else "Unknown",
                "treatment_pre": t_vols["pre_volume"],
                "treatment_post": t_vols["post_volume"],
                "treatment_lift": t_vols["lift"],
                
                "control_id": c_co.outlet_id if c_co else "None",
                "control_name": c_outlet.Outlet_Name if c_outlet else "None",
                "control_pre": c_vols["pre_volume"],
                "control_post": c_vols["post_volume"],
                "control_lift": c_vols["lift"],
                "net_lift": round(t_vols["lift"] - c_vols["lift"], 2)
            })

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.campaign_name,
            "status": campaign.status,
            "pre_volume": analysis.pre_volume if analysis else 0.0,
            "post_volume": analysis.post_volume if analysis else 0.0,
            "treatment_lift": analysis.treatment_lift if analysis else 0.0,
            "control_lift": analysis.control_lift if analysis else 0.0,
            "did_effect": analysis.did_effect if analysis else 0.0,
            "confidence_score": analysis.confidence_score if analysis else 0.0,
            "generated_at": analysis.generated_at if analysis else None,
            "pairs": pairs
        }
