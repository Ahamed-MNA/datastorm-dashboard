import datetime
from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Outlet(Base):
    __tablename__ = "outlets"

    Outlet_ID = Column(String, primary_key=True, index=True)
    Outlet_Name = Column(String, nullable=False)
    Province = Column(String, nullable=False)
    Distributor = Column(String, nullable=False)
    Latitude = Column(Float, nullable=False)
    Longitude = Column(Float, nullable=False)
    Outlet_Size = Column(String, nullable=False)
    Outlet_Type = Column(String, nullable=False)
    Cooler_Count = Column(Integer, nullable=False)

    # Relationships
    prediction = relationship("Prediction", back_populates="outlet", uselist=False, cascade="all, delete-orphan")
    spatial_features = relationship("SpatialFeature", back_populates="outlet", uselist=False, cascade="all, delete-orphan")
    budget_allocation = relationship("BudgetAllocation", back_populates="outlet", uselist=False, cascade="all, delete-orphan")
    history = relationship("OutletHistory", back_populates="outlet", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    Outlet_ID = Column(String, ForeignKey("outlets.Outlet_ID"), primary_key=True)
    Historical_Sales = Column(Float, nullable=False)
    Predicted_Potential = Column(Float, nullable=False)
    Opportunity_Gap = Column(Float, nullable=False)
    Growth_Percent = Column(Float, nullable=False)
    Efficiency_Score = Column(Float, nullable=False)
    
    # Constraint Proxies
    CV_Volume = Column(Float, nullable=False)
    Flatline_Score = Column(Float, nullable=False)
    Round_Number_Bias = Column(Float, nullable=False)
    Price_Rigidity = Column(Float, nullable=False)

    # Relationships
    outlet = relationship("Outlet", back_populates="prediction")


class SpatialFeature(Base):
    __tablename__ = "spatial_features"

    Outlet_ID = Column(String, ForeignKey("outlets.Outlet_ID"), primary_key=True)
    School_Gravity = Column(Float, nullable=False)
    Hospital_Gravity = Column(Float, nullable=False)
    Transit_Gravity = Column(Float, nullable=False)
    Religious_Gravity = Column(Float, nullable=False)
    Commercial_Gravity = Column(Float, nullable=False)
    Residential_Gravity = Column(Float, nullable=False)
    Tourism_Gravity = Column(Float, nullable=False)
    POI_Total_Impact_Score = Column(Float, nullable=False)
    POI_Avg_Distance_Meters = Column(Float, nullable=False)
    
    # Competition Graph Features
    Competition_Gravity = Column(Float, nullable=False)
    Market_Saturation = Column(Float, nullable=False)
    Min_Competitor_Distance_Meters = Column(Float, nullable=False)
    Average_Competitive_Friction = Column(Float, nullable=False)

    # Relationships
    outlet = relationship("Outlet", back_populates="spatial_features")


class BudgetAllocation(Base):
    __tablename__ = "budget_allocations"

    Outlet_ID = Column(String, ForeignKey("outlets.Outlet_ID"), primary_key=True)
    Allocated_Budget = Column(Float, nullable=False)
    Expected_Lift = Column(Float, nullable=False)
    ROI = Column(Float, nullable=False)
    Y_historical = Column(Float, nullable=False)
    Upper_Bound = Column(Float, nullable=False)

    # Relationships
    outlet = relationship("Outlet", back_populates="budget_allocation")


class OutletHistory(Base):
    __tablename__ = "outlet_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    Outlet_ID = Column(String, ForeignKey("outlets.Outlet_ID"), nullable=False)
    Year = Column(Integer, nullable=False)
    Month = Column(Integer, nullable=False)
    Volume_Liters = Column(Float, nullable=False)
    Total_Bill_Value = Column(Float, nullable=False)

    # Relationships
    outlet = relationship("Outlet", back_populates="history")


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_name = Column(String, nullable=False)
    province = Column(String, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    total_budget = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="Draft")  # Draft, Active, Completed
    created_at = Column(String, default=lambda: datetime.datetime.utcnow().isoformat())

    # Relationships
    outlets = relationship("CampaignOutlet", back_populates="campaign", cascade="all, delete-orphan")
    snapshots = relationship("MonitoringSnapshot", back_populates="campaign", cascade="all, delete-orphan")
    impact_analysis = relationship("ImpactAnalysis", back_populates="campaign", cascade="all, delete-orphan")
    recommendations = relationship("ReallocationRecommendation", back_populates="campaign", cascade="all, delete-orphan")


class CampaignOutlet(Base):
    __tablename__ = "campaign_outlets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id"), nullable=False)
    outlet_id = Column(String, ForeignKey("outlets.Outlet_ID"), nullable=False)
    allocated_budget = Column(Float, nullable=False, default=0.0)
    expected_lift_liters = Column(Float, nullable=False, default=0.0)
    expected_roi = Column(Float, nullable=False, default=0.0)
    group_type = Column(String, nullable=False)  # treatment, control

    # Relationships
    campaign = relationship("Campaign", back_populates="outlets")
    outlet = relationship("Outlet")


class MonitoringSnapshot(Base):
    __tablename__ = "monitoring_snapshots"

    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id"), nullable=False)
    outlet_id = Column(String, ForeignKey("outlets.Outlet_ID"), nullable=False)
    snapshot_date = Column(String, nullable=False)
    actual_volume = Column(Float, nullable=False)
    actual_revenue = Column(Float, nullable=False)
    actual_lift = Column(Float, nullable=False)
    notes = Column(String, nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="snapshots")
    outlet = relationship("Outlet")


class ImpactAnalysis(Base):
    __tablename__ = "impact_analysis"

    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id"), nullable=False)
    pre_volume = Column(Float, nullable=False)
    post_volume = Column(Float, nullable=False)
    treatment_lift = Column(Float, nullable=False)
    control_lift = Column(Float, nullable=False)
    did_effect = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    generated_at = Column(String, default=lambda: datetime.datetime.utcnow().isoformat())

    # Relationships
    campaign = relationship("Campaign", back_populates="impact_analysis")


class ReallocationRecommendation(Base):
    __tablename__ = "reallocation_recommendations"

    recommendation_id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id"), nullable=False)
    outlet_id = Column(String, ForeignKey("outlets.Outlet_ID"), nullable=False)
    current_budget = Column(Float, nullable=False)
    recommended_budget = Column(Float, nullable=False)
    expected_improvement = Column(Float, nullable=False)
    recommendation_reason = Column(String, nullable=False)
    created_at = Column(String, default=lambda: datetime.datetime.utcnow().isoformat())

    # Relationships
    campaign = relationship("Campaign", back_populates="recommendations")
    outlet = relationship("Outlet")

