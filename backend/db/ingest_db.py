import os
import sys
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

# Setup path to import backend modules
db_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(db_dir)
sys.path.insert(0, backend_dir)

# Resolve project root path (containing data/ and outputs/ directories)
project_root = os.path.abspath(os.path.join(backend_dir, "..", ".."))

from db.database import engine, Base, SessionLocal
from db.models import Outlet, Prediction, SpatialFeature, BudgetAllocation, OutletHistory

def main():
    print("Creating tables in SQLite database...")
    Base.metadata.create_all(bind=engine)

    print("Resolving input file paths...")
    silver_outlets_path = os.path.join(project_root, "data", "silver", "dim_outlets.parquet")
    silver_trans_path = os.path.join(project_root, "data", "silver", "fact_transactions.parquet")
    gold_sfa_path = os.path.join(project_root, "data", "gold", "sfa_refined.parquet")
    predictions_csv_path = os.path.join(project_root, "outputs", "data_mavericks_predictions.csv")
    sfa_report_path = os.path.join(project_root, "outputs", "outlet_potential_report_refined.parquet")
    budget_csv_path = os.path.join(project_root, "outputs", "data_mavericks_budget_allocations.csv")

    # Load dataframes
    print("Loading datasets...")
    df_outlets = pd.read_parquet(silver_outlets_path)
    df_trans = pd.read_parquet(silver_trans_path)
    df_gold = pd.read_parquet(gold_sfa_path)
    df_preds = pd.read_csv(predictions_csv_path)
    df_report = pd.read_parquet(sfa_report_path)
    df_budget = pd.read_csv(budget_csv_path)

    # 1. Resolve distributor maps and provinces
    print("Mapping distributors and provinces...")
    # Find mapping from Outlet_ID to Distributor_ID
    outlet_dist = df_trans.groupby("Outlet_ID")["Distributor_ID"].first().reset_index()
    
    province_map = {
        'W': 'Western', 'C': 'Central', 'S': 'Southern', 'NW': 'North Western',
        'E': 'Eastern', 'NC': 'North Central', 'U': 'Uva', 'SG': 'Sabaragamuwa', 'N': 'Northern'
    }
    
    def get_province(dist_id):
        if not dist_id:
            return 'Unknown'
        parts = dist_id.split('_')
        if len(parts) > 1:
            return province_map.get(parts[1], 'Other')
        return 'Unknown'

    # Create master outlet records
    print("Processing outlet dimension records...")
    df_outlet_master = df_outlets.merge(outlet_dist, on="Outlet_ID", how="left")
    df_outlet_master["Distributor_ID"] = df_outlet_master["Distributor_ID"].fillna("Unknown")
    df_outlet_master["Province"] = df_outlet_master["Distributor_ID"].apply(get_province)

    # Resolve spelling issues for type
    type_spelling_map = {
        'Grocry': 'Grocery',
        'Bakry': 'Bakery',
        'Pharmacy': 'Pharmacy',
        'Eatery': 'Eatery',
        'Hotel': 'Hotel',
        'Kiosk': 'Kiosk',
        'SMMT': 'SMMT'
    }
    df_outlet_master["Outlet_Type"] = df_outlet_master["Outlet_Type"].map(type_spelling_map).fillna(df_outlet_master["Outlet_Type"])

    # 2. Process Predictions
    print("Processing prediction records...")
    df_pred_merge = df_report.merge(df_preds, on="Outlet_ID", how="inner")
    df_pred_merge["Historical_Sales"] = df_pred_merge["Avg_Monthly_Volume"]
    df_pred_merge["Predicted_Potential"] = df_pred_merge["Maximum_Monthly_Liters"]
    df_pred_merge["Opportunity_Gap"] = (df_pred_merge["Predicted_Potential"] - df_pred_merge["Historical_Sales"]).clip(lower=0.0)
    df_pred_merge["Growth_Percent"] = np.where(
        df_pred_merge["Historical_Sales"] > 0,
        (df_pred_merge["Opportunity_Gap"] / df_pred_merge["Historical_Sales"]) * 100.0,
        0.0
    )

    # 3. Process Spatial Features
    print("Processing spatial features...")
    spatial_cols = [
        'Outlet_ID', 'POI_Impact_Education', 'POI_Impact_Health', 'POI_Impact_Transport',
        'POI_Impact_Social', 'POI_Impact_Commercial', 'POI_Impact_Residential', 'POI_Impact_Tourism',
        'POI_Total_Impact_Score', 'POI_Avg_Distance_Meters', 'Total_Competitive_Friction',
        'Competitor_Count_5km', 'Min_Competitor_Distance_Meters', 'Average_Competitive_Friction'
    ]
    df_spatial_src = df_gold[[c for c in spatial_cols if c in df_gold.columns]].groupby('Outlet_ID').first().reset_index()

    # 4. Process Budget Allocations
    print("Processing budget allocations...")
    # Replicate Y_historical computation
    df_trans_wp = df_trans[df_trans['Distributor_ID'].str.contains('_W_', na=False)]
    df_jan = df_trans_wp[df_trans_wp['Month'] == 1]
    jan_sales = df_jan.groupby(['Outlet_ID', 'Year'])['Volume_Liters'].sum().reset_index()
    avg_jan_sales = jan_sales.groupby('Outlet_ID')['Volume_Liters'].mean().reset_index(name='Y_historical')
    
    overall_sales = df_trans_wp.groupby(['Outlet_ID', 'Year', 'Month'])['Volume_Liters'].sum().reset_index()
    avg_overall_sales = overall_sales.groupby('Outlet_ID')['Volume_Liters'].mean().reset_index(name='Y_historical_fallback')
    
    df_y_hist = pd.DataFrame({'Outlet_ID': df_trans_wp['Outlet_ID'].unique()})
    df_y_hist = df_y_hist.merge(avg_jan_sales, on='Outlet_ID', how='left')
    df_y_hist = df_y_hist.merge(avg_overall_sales, on='Outlet_ID', how='left')
    df_y_hist['Y_historical'] = df_y_hist['Y_historical'].fillna(df_y_hist['Y_historical_fallback']).fillna(0.0)
    
    df_budget_calc = df_budget.merge(df_y_hist[['Outlet_ID', 'Y_historical']], on='Outlet_ID', how='left')
    df_budget_calc['Y_historical'] = df_budget_calc['Y_historical'].fillna(0.0)
    df_budget_calc['a'] = df_budget_calc['Y_historical'].clip(lower=1.0)
    
    # Calculate expected lift and ROI
    b_param = 0.0005
    df_budget_calc['Allocated_Budget'] = df_budget_calc['Trade_Spend_Allocation_LKR']
    df_budget_calc['Expected_Lift'] = df_budget_calc['a'] * np.log(1.0 + b_param * df_budget_calc['Allocated_Budget'])
    df_budget_calc['ROI'] = np.where(
        df_budget_calc['Allocated_Budget'] > 0.01,
        df_budget_calc['Expected_Lift'] / df_budget_calc['Allocated_Budget'],
        0.0
    )

    # Re-calculate Upper Bound (U_i) based on headroom
    df_pred_rename = df_preds.rename(columns={'Maximum_Monthly_Liters': 'Y_frontier'})
    df_budget_calc = df_budget_calc.merge(df_pred_rename, on='Outlet_ID', how='left')
    df_budget_calc['Y_frontier'] = df_budget_calc['Y_frontier'].fillna(df_budget_calc['Y_historical'])
    df_budget_calc['Headroom'] = (df_budget_calc['Y_frontier'] - df_budget_calc['Y_historical']).clip(lower=0.0)
    ratio = (df_budget_calc['Headroom'] / df_budget_calc['a']).clip(upper=50.0)
    df_budget_calc['Upper_Bound'] = (np.exp(ratio) - 1.0) / b_param

    # 5. Populate SQLite
    db: Session = SessionLocal()
    try:
        # Clear existing data and drop tables to re-create with new schema
        print("Dropping tables and recreating...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        # Ingest Outlets
        print(f"Inserting {len(df_outlet_master)} outlets...")
        outlets_to_insert = []
        for idx, row in df_outlet_master.iterrows():
            outlets_to_insert.append(Outlet(
                Outlet_ID=row["Outlet_ID"],
                Outlet_Name=f"Outlet {row['Outlet_ID']}",
                Province=row["Province"],
                Distributor=row["Distributor_ID"],
                Latitude=float(row["Latitude"]),
                Longitude=float(row["Longitude"]),
                Outlet_Size=row["Outlet_Size"],
                Outlet_Type=row["Outlet_Type"],
                Cooler_Count=int(row["Cooler_Count"])
            ))
        db.bulk_save_objects(outlets_to_insert)
        db.commit()

        # Ingest Predictions
        print(f"Inserting {len(df_pred_merge)} predictions...")
        predictions_to_insert = []
        for idx, row in df_pred_merge.iterrows():
            predictions_to_insert.append(Prediction(
                Outlet_ID=row["Outlet_ID"],
                Historical_Sales=float(row["Historical_Sales"]),
                Predicted_Potential=float(row["Predicted_Potential"]),
                Opportunity_Gap=float(row["Opportunity_Gap"]),
                Growth_Percent=float(row["Growth_Percent"]),
                Efficiency_Score=float(row["Efficiency_Score"]),
                CV_Volume=float(row["CV_Volume"]),
                Flatline_Score=float(row["Flatline_Score"]),
                Round_Number_Bias=float(row["Round_Number_Bias"]),
                Price_Rigidity=float(row["Price_Rigidity"])
            ))
        db.bulk_save_objects(predictions_to_insert)
        db.commit()

        # Ingest Spatial Features
        print(f"Inserting {len(df_spatial_src)} spatial features...")
        spatial_to_insert = []
        for idx, row in df_spatial_src.iterrows():
            spatial_to_insert.append(SpatialFeature(
                Outlet_ID=row["Outlet_ID"],
                School_Gravity=float(row.get("POI_Impact_Education", 0.0)),
                Hospital_Gravity=float(row.get("POI_Impact_Health", 0.0)),
                Transit_Gravity=float(row.get("POI_Impact_Transport", 0.0)),
                Religious_Gravity=float(row.get("POI_Impact_Social", 0.0)),
                Commercial_Gravity=float(row.get("POI_Impact_Commercial", 0.0)),
                Residential_Gravity=float(row.get("POI_Impact_Residential", 0.0)),
                Tourism_Gravity=float(row.get("POI_Impact_Tourism", 0.0)),
                POI_Total_Impact_Score=float(row.get("POI_Total_Impact_Score", 0.0)),
                POI_Avg_Distance_Meters=float(row.get("POI_Avg_Distance_Meters", 1000.0)),
                Competition_Gravity=float(row.get("Total_Competitive_Friction", 0.0)),
                Market_Saturation=float(row.get("Competitor_Count_5km", 0.0)),
                Min_Competitor_Distance_Meters=float(row.get("Min_Competitor_Distance_Meters", 5000.0)),
                Average_Competitive_Friction=float(row.get("Average_Competitive_Friction", 0.0))
            ))
        db.bulk_save_objects(spatial_to_insert)
        db.commit()

        # Ingest Budget Allocations
        print(f"Inserting {len(df_budget_calc)} budget allocations...")
        budget_to_insert = []
        for idx, row in df_budget_calc.iterrows():
            budget_to_insert.append(BudgetAllocation(
                Outlet_ID=row["Outlet_ID"],
                Allocated_Budget=float(row["Allocated_Budget"]),
                Expected_Lift=float(row["Expected_Lift"]),
                ROI=float(row["ROI"]),
                Y_historical=float(row["Y_historical"]),
                Upper_Bound=float(row["Upper_Bound"])
            ))
        db.bulk_save_objects(budget_to_insert)
        db.commit()

        # Ingest Outlet History using pandas to_sql for speed
        print(f"Inserting {len(df_gold)} historical monthly records...")
        df_history = df_gold[['Outlet_ID', 'Year', 'Month', 'Volume_Liters', 'Total_Bill_Value']].copy()
        df_history.to_sql("outlet_history", con=engine, if_exists="append", index=False)

        print("Database ingestion completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error during ingestion: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
