import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from typing import Tuple, Dict, List, Optional, Any

# Load env variables
load_dotenv()

logger = logging.getLogger(__name__)

# System instructions for FMCG consultant style
SYSTEM_PROMPT = """
You are an expert FMCG (Fast-Moving Consumer Goods) commercial consultant and data translator.
Your task is to analyze the provided JSON payload containing a retail outlet's sales potential metrics, physical attributes, geospatial signals, and operational constraints, and translate them into a clear, human-readable business narrative.

Strictly adhere to the following Structural Guidelines:
- Write exactly a 3-paragraph narrative. Do not include titles, labels, or greetings (such as "Dear Regional Sales Manager" or "Paragraph 1:"). Start directly with the narrative.
- Paragraph 1 (The Score): Explain the latent ceiling (predicted maximum potential) vs. historical reality (actual baseline sales). Frame this opportunity gap as a clear investment/revenue opportunity. If the actual sales exceed the predicted potential (resulting in a technical efficiency score greater than 100% / 1.0), explain that the outlet is an extraordinary success story and outlier that outperforms its model-predicted frontier.
- Paragraph 2 (The Drivers): Explain what environmental or local factors naturally elevate this store (e.g., presence of commercial centers, educational institutions, or residential density based on the geospatial and POI signals).
- Paragraph 3 (The Bottlenecks & Action): Explain how operational bottlenecks (such as lack of cooler space, high flatline score, or demand volatility) are choking potential, and explicitly suggest how to allocate the marketing/promotional or operational budget to unlock this performance (e.g., deploying extra coolers, easing credit lines, or localized promotional support). Even if the outlet is already performing above its predicted frontier, suggest how resolving bottlenecks can help sustain or further elevate this success.

Guardrails & Style:
- Use professional, executive-ready, and persuasive business language.
- Do NOT use mathematical jargon (such as beta, coefficients, log-space, SFA, frontier, stochastic, etc.).
- Never hallucinate features, attributes, or numbers not present in the JSON payload.
- Focus on translating the metrics into actionable business context.
"""

class XaiService:
    @staticmethod
    def _resolve_paths() -> Tuple[Path, Path]:
        """
        Locate the SFA model pickle and gold parquet dataset.
        Checks local paths first (self-contained mode) and then parent paths.
        """
        app_dir = Path(__file__).resolve().parent
        backend_dir = app_dir.parent.parent
        project_root = backend_dir.parent

        # 1. Look for Model
        model_local = backend_dir / "modeling" / "sfa_model.pkl"
        model_parent = project_root / "outputs" / "sfa_model.pkl"
        if model_local.exists():
            model_path = model_local
        elif model_parent.exists():
            model_path = model_parent
        else:
            raise FileNotFoundError("SFA model file (sfa_model.pkl) not found in backend/modeling/ or outputs/")

        # 2. Look for Parquet Data
        data_local = backend_dir / "modeling" / "sfa_refined.parquet"
        data_parent = project_root / "data" / "gold" / "sfa_refined.parquet"
        if data_local.exists():
            data_path = data_local
        elif data_parent.exists():
            data_path = data_parent
        else:
            # Check if there is another location we can query
            raise FileNotFoundError("Gold dataset (sfa_refined.parquet) not found in backend/modeling/ or data/gold/")

        return model_path, data_path

    @classmethod
    def get_outlet_explanation(cls, outlet_id: str) -> Dict[str, Any]:
        """
        Orchestrate XAI calculation and LLM generation.
        """
        from modeling.sfa_model import SFAModel
        from app.models.schemas import FeatureImpactSchema, OutletXAIPayloadSchema, OutletXAIResponseSchema

        # 1. Load SFA model and features row
        model_path, data_path = cls._resolve_paths()
        
        # Load model using classloader
        model = SFAModel.load(str(model_path))

        # Load Parquet and locate outlet
        df = pd.read_parquet(str(data_path))
        id_col = [c for c in df.columns if 'id' in c.lower()][0]
        outlet_rows = df[df[id_col] == outlet_id]
        if outlet_rows.empty:
            raise ValueError(f"Outlet ID {outlet_id} not found in the gold dataset.")

        # Get latest record
        if 'Year' in outlet_rows.columns and 'Month' in outlet_rows.columns:
            outlet_rows = outlet_rows.sort_values(by=['Year', 'Month'], ascending=False)
        outlet_row = outlet_rows.iloc[0]

        # 2. Compute local SFA drivers and constraints
        outlet_features = {}
        for feat in model.feature_names:
            if feat == "Intercept":
                outlet_features[feat] = 1.0
            elif feat not in outlet_row:
                outlet_features[feat] = 0.0
            else:
                outlet_features[feat] = float(outlet_row[feat])

        # Predict potential
        X_df = pd.DataFrame([outlet_features])
        predicted_potential = float(model.predict_potential(X_df)[0])

        vol_col = [c for c in outlet_row.index if 'vol' in c.lower() or 'sales' in c.lower()][0]
        actual_volume = float(outlet_row[vol_col])

        efficiency_score = actual_volume / predicted_potential
        opportunity_gap = max(0.0, predicted_potential - actual_volume)
        inefficiency_pct = 0.0 if actual_volume > predicted_potential else (1.0 - efficiency_score) * 100.0

        # Calculate feature contributions
        feature_impacts = []
        for feat, beta in zip(model.feature_names, model.beta):
            if feat == "Intercept":
                continue
            feat_val = outlet_features[feat]
            percentage_impact = (np.exp(beta) - 1.0) * 100.0
            local_driver_strength = feat_val * percentage_impact

            feature_impacts.append(FeatureImpactSchema(
                feature_name=feat,
                coefficient=float(beta),
                percentage_impact=float(percentage_impact),
                feature_value=float(feat_val),
                local_driver_strength=float(local_driver_strength)
            ))

        feature_impacts.sort(key=lambda x: x.local_driver_strength, reverse=True)

        # Separate environments vs constraints
        local_signals = {}
        operational_constraints = {}
        
        env_keywords = ["competitor", "poi", "distance", "friction", "province", "holiday"]
        constraint_keywords = ["cooler", "flatline", "bias", "rigidity", "cv_"]
        
        for imp in feature_impacts:
            name_lower = imp.feature_name.lower()
            if any(kw in name_lower for kw in env_keywords):
                local_signals[imp.feature_name] = imp.feature_value
            elif any(kw in name_lower for kw in constraint_keywords):
                operational_constraints[imp.feature_name] = imp.feature_value

        if "Cooler_Count" not in operational_constraints and "Cooler_Count" in outlet_row:
            operational_constraints["Cooler_Count"] = float(outlet_row["Cooler_Count"])

        payload = OutletXAIPayloadSchema(
            outlet_id=outlet_id,
            actual_volume=actual_volume,
            predicted_potential=predicted_potential,
            opportunity_gap=opportunity_gap,
            efficiency_score=efficiency_score,
            inefficiency_pct=inefficiency_pct,
            top_drivers=feature_impacts,
            local_signals=local_signals,
            operational_constraints=operational_constraints
        )

        # 3. Call LLM to generate narrative
        explanation = cls._generate_llm_explanation(payload)

        return {
            "outlet_id": outlet_id,
            "actual_volume": round(actual_volume, 2),
            "predicted_potential": round(predicted_potential, 2),
            "opportunity_gap": round(opportunity_gap, 2),
            "efficiency_score": round(efficiency_score, 2),
            "inefficiency_pct": round(inefficiency_pct, 2),
            "explanation": explanation,
            "payload": payload
        }

    @classmethod
    def _generate_llm_explanation(cls, payload) -> str:
        """
        Formats the payload and invokes Gemini or Groq based on environment keys.
        """
        # Filter drivers to top 3 positive and top 2 negative for prompt token efficiency
        pos_drivers = [d for d in payload.top_drivers if d.local_driver_strength > 0][:3]
        neg_drivers = [d for d in payload.top_drivers if d.local_driver_strength < 0][:2]
        
        drivers_summary = []
        for d in pos_drivers:
            drivers_summary.append({
                "feature": d.feature_name.replace("_", " "),
                "value": d.feature_value,
                "direction": "Positive Impact",
                "compounding_lift": f"+{d.local_driver_strength:.2f}%"
            })
        for d in neg_drivers:
            drivers_summary.append({
                "feature": d.feature_name.replace("_", " "),
                "value": d.feature_value,
                "direction": "Negative Impact",
                "compounding_lift": f"{d.local_driver_strength:.2f}%"
            })

        payload_dict = {
            "outlet_id": payload.outlet_id,
            "historical_actual_sales_liters": round(payload.actual_volume, 2),
            "predicted_maximum_potential_liters": round(payload.predicted_potential, 2),
            "opportunity_gap_liters": round(payload.opportunity_gap, 2),
            "technical_efficiency_score": round(payload.efficiency_score, 2),
            "inefficiency_percentage": round(payload.inefficiency_pct, 2),
            "key_compounding_drivers": drivers_summary,
            "local_environmental_signals": {k.replace("_", " "): round(v, 4) for k, v in payload.local_signals.items() if v != 0},
            "operational_constraints": {k.replace("_", " "): round(v, 4) for k, v in payload.operational_constraints.items()}
        }

        prompt = f"""
        Please generate the 3-paragraph executive narrative for the following outlet:
        
        JSON Payload:
        {json.dumps(payload_dict, indent=2)}
        
        Remember:
        - Write exactly a 3-paragraph narrative. No markdown header tags for paragraphs.
        - No statistical jargon. Keep it completely in FMCG/business terms.
        - Ground all claims and numbers strictly in the provided JSON payload.
        """

        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        if gemini_key:
            try:
                from google import genai
                from google.genai import types
                
                logger.info("Invoking Gemini 2.5 Flash from backend...")
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.5,
                    )
                )
                return response.text.strip()
            except Exception as e:
                logger.error(f"Backend Gemini call failed: {e}. Trying fallback...")

        if groq_key:
            try:
                from groq import Groq
                logger.info("Invoking Groq LLaMA from backend...")
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-specdec",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Backend Groq call failed: {e}. Trying fallback...")

        # If no keys, return mock explanation for local development/offline testing
        logger.warning("No LLM API keys found in env. Returning fallback placeholder explanation.")
        return (
            f"Outlet {payload.outlet_id} shows a predicted latent ceiling of {payload.predicted_potential:.2f} liters, "
            f"compared to its historical sales of {payload.actual_volume:.2f} liters. This leaves a clear opportunity gap of "
            f"{payload.opportunity_gap:.2f} liters to be captured through targeted trade spend and marketing support.\n\n"
            f"The primary driver elevating this store's potential is its local commercial activity and competitive positioning. "
            f"It operates in a dense environment that presents high natural traffic and customer availability.\n\n"
            f"To unlock this potential, operational bottlenecks must be addressed. Specifically, upgrading the outlet's "
            f"cooling capacity (currently at {payload.operational_constraints.get('Cooler_Count', 0.0):.0f} coolers) and "
            f"reducing delivery flatlining will help capture latent demand and drive efficiency."
        )
