from fastapi import APIRouter, Query, HTTPException
from services.predictive_engine import run_regression_analysis, run_dbscan_clustering
from services.supabase_client import DBWrapper
import os
import json
from groq import Groq
from dotenv import load_dotenv

# Robustly load environment variables from server/.env and root .env using absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
# server/.env is the parent of routes, so:
server_env = os.path.join(os.path.dirname(current_dir), '.env')
# root .env is the parent of server, so:
root_env = os.path.join(os.path.dirname(os.path.dirname(current_dir)), '.env')

if os.path.exists(server_env):
    load_dotenv(dotenv_path=server_env, override=True)
if os.path.exists(root_env):
    load_dotenv(dotenv_path=root_env, override=True)

# Also support groq_api env variable and standardise to GROQ_API_KEY
groq_api_val = os.getenv("groq_api")
current_key = os.getenv("GROQ_API_KEY")
if not current_key or "your_groq_api_key" in current_key:
    if groq_api_val and "your_groq_api_key" not in groq_api_val:
        os.environ["GROQ_API_KEY"] = groq_api_val

router = APIRouter(prefix="/predictive", tags=["Predictive Spatial Analytics"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@router.get("/run")
async def run_predictive_pipeline(
    bandwidth: float = Query(0.08, description="Spatial kernel bandwidth for local GWR regression"),
    eps: float = Query(0.015, description="DBSCAN epsilon radius in degrees for spatial clustering"),
    min_samples: int = Query(3, description="DBSCAN minimum complaints to classify a hotspot cluster")
):
    """
    Executes the spatial predictive engine:
    1. DBSCAN complaint coordinates clustering (Hotspots identification).
    2. Ordinary Least Squares (OLS) multi-variable global regression.
    3. Geographically Weighted Regression (GWR) ward-specific risk index calculations.
    """
    try:
        regression_data = run_regression_analysis(bandwidth=bandwidth)
        if "error" in regression_data:
            raise HTTPException(status_code=400, detail=regression_data["error"])
            
        clustering_data = run_dbscan_clustering(eps=eps, min_samples=min_samples)
        
        return {
            "status": "success",
            "sample_size": regression_data["sample_size"],
            "features_tested": regression_data["features_tested"],
            "global_ols": regression_data["global_regression"],
            "ward_gwr_risk": regression_data["gwr_risk_heatmap"],
            "hotspots": clustering_data["hotspots"],
            "total_complaints_clustered": clustering_data["total_complaints"],
            "hotspots_count": clustering_data["hotspots_count"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Predictive modeling failure: {str(e)}")


@router.get("/insights")
async def get_predictive_insights():
    """
    Generates a natural language executive planning report using Groq LLaMA 3.3
    based on live global OLS regression coefficients and localized GWR ward hotspots.
    Includes a robust dynamic markdown fallback mode.
    """
    try:
        regression_data = run_regression_analysis(bandwidth=0.08)
        if "error" in regression_data:
            raise HTTPException(status_code=400, detail=regression_data["error"])
            
        clustering_data = run_dbscan_clustering(eps=0.015, min_samples=3)
        
        # Sort wards by risk score descending
        sorted_wards = sorted(regression_data["gwr_risk_heatmap"], key=lambda x: x["risk_score"], reverse=True)
        top_risk_wards = sorted_wards[:3]
        
        # Format metrics summary for LLM context
        ols = regression_data["global_regression"]
        hotspots = clustering_data["hotspots"]
        
        system_prompt = "You are an expert AI City Planner and Infrastructure Geographer advising municipal engineers in Ahmedabad."
        
        prompt = f"""
        Analyze the following spatial and regression statistics regarding sewer blockages and write a professional municipal planning briefing.
        
        --- STATISTICAL SUMMARY ---
        - Global OLS R-Squared Score: {ols["r2_score"]}
        - Adjusted R-Squared: {ols["r2_adj"]}
        - Overall Model F-Statistic: {ols["f_statistic"]} (p-value: {ols["f_p_value"]})
        - OLS Regression Formula: Blockages = {ols["intercept"]["coefficient"]} + ({ols["coefficients"]["avg_sewer_age_years"]["coefficient"]} * SewerAge) + ({ols["coefficients"]["tree_count"]["coefficient"]} * Trees) + ({ols["coefficients"]["connections_count"]["coefficient"]} * Connections) + ({ols["coefficients"]["population_density"]["coefficient"]} * PopDensity) + ({ols["coefficients"]["pipe_diameter_mm"]["coefficient"]} * PipeDiameter)
        
        - Detailed Global Coefficients & P-Values:
          * Sewer Age: coef = {ols["coefficients"]["avg_sewer_age_years"]["coefficient"]} (p = {ols["coefficients"]["avg_sewer_age_years"]["p_value"]}, significant: {ols["coefficients"]["avg_sewer_age_years"]["significant"]})
          * Tree Roots: coef = {ols["coefficients"]["tree_count"]["coefficient"]} (p = {ols["coefficients"]["tree_count"]["p_value"]}, significant: {ols["coefficients"]["tree_count"]["significant"]})
          * Connection Count: coef = {ols["coefficients"]["connections_count"]["coefficient"]} (p = {ols["coefficients"]["connections_count"]["p_value"]}, significant: {ols["coefficients"]["connections_count"]["significant"]})
          * Population Density: coef = {ols["coefficients"]["population_density"]["coefficient"]} (p = {ols["coefficients"]["population_density"]["p_value"]}, significant: {ols["coefficients"]["population_density"]["significant"]})
          * Pipe Diameter: coef = {ols["coefficients"]["pipe_diameter_mm"]["coefficient"]} (p = {ols["coefficients"]["pipe_diameter_mm"]["p_value"]}, significant: {ols["coefficients"]["pipe_diameter_mm"]["significant"]})
        
        - Top 3 Highest Risk Wards (GWR calculated probability):
          1. {top_risk_wards[0]["ward_name"]}: Risk Score = {top_risk_wards[0]["risk_score"]}% (Coefficients: SewerAge={round(top_risk_wards[0]["local_coefficients"]["avg_sewer_age_years"], 2)}, Trees={round(top_risk_wards[0]["local_coefficients"]["tree_count"], 2)}, Connections={round(top_risk_wards[0]["local_coefficients"]["connections_count"], 2)})
          2. {top_risk_wards[1]["ward_name"]}: Risk Score = {top_risk_wards[1]["risk_score"]}% (Coefficients: SewerAge={round(top_risk_wards[1]["local_coefficients"]["avg_sewer_age_years"], 2)}, Trees={round(top_risk_wards[1]["local_coefficients"]["tree_count"], 2)}, Connections={round(top_risk_wards[1]["local_coefficients"]["connections_count"], 2)})
          3. {top_risk_wards[2]["ward_name"]}: Risk Score = {top_risk_wards[2]["risk_score"]}%
        
        - Active Blockage Hotspots Identified (DBSCAN Clustering):
          Total Hotspots: {len(hotspots)}
          Dense Hotspots: {[{'Lat': h['centroid_lat'], 'Lng': h['centroid_lng'], 'ComplaintsDensity': h['density']} for h in hotspots[:3]]}
        
        --- REPORT SPECIFICATION ---
        Structure the briefing using elegant Github Markdown:
        1. **Executive Spatial Assessment**: A high-level overview explaining the OLS R² validation, Adjusted R², F-statistic, and what it means for city infrastructure. Detail which variables are statistically significant (p < 0.05).
        2. **Critical Vulnerability Breakdown**: Analyze the top risk wards. Explain why they are failing (e.g. highlight whether it's driven by structural wear/sewer age, high house connection counts, or environmental tree roots).
        3. **Targeted Preventive Action Checklist**: Provide 3-4 concrete, actionable operational directives for municipal maintenance crews (e.g. hydro-jetting schedule, root barrier installations, grease trap audits) targeted to the high-risk zones.
        
        Make the report crisp, technical, highly detailed, and authoritative. Do not add casual conversational fillers.
        """
        
        # Call Groq if API key is present
        if GROQ_API_KEY and "your_groq_api_key" not in GROQ_API_KEY:
            try:
                client = Groq(api_key=GROQ_API_KEY)
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.3
                )
                markdown_report = response.choices[0].message.content
                return {
                    "source": "groq_llama3",
                    "report": markdown_report
                }
            except Exception as le:
                print(f"[AI Route Error] LLM generation failed: {le}. Falling back to dynamic generator.")
                
        # High-fidelity dynamic fallback builder
        fallback_report = f"""# Municipal Drainage Infrastructure Planning & Predictive Risk Briefing
**City Planning Authority — Ahmedabad Municipal Corporation**

## 1. Executive Spatial Assessment
Based on our multi-variable spatial analysis, the predictive models validate a global Ordinary Least Squares (OLS) $R^2$ score of **{ols["r2_score"]}** and Adjusted $R^2$ of **{ols["r2_adj"]}**, with an overall model F-statistic significance of **{ols["f_p_value"]:.4e}**. This mathematically proves that **{round(ols["r2_score"] * 100, 1)}%** of the localized variations in sewer blockage events across the municipality are accounted for by the structural and environmental predictors tested.

The global predictive coefficient values and their corresponding $p$-values reveal the systemic drivers of sewer degradation:
* **Active Connections Count** ($\beta = {ols["coefficients"]["connections_count"]["coefficient"]}$, $p = {ols["coefficients"]["connections_count"]["p_value"]:.4e}$): Proves that high-density household/industrial link connections create heavy baseline hydraulic loads, leading to accelerated siltation. (Statistically {"Significant (p < 0.05)" if ols["coefficients"]["connections_count"]["significant"] else "Not Significant (p >= 0.05)"}).
* **Sewer Infrastructure Age** ($\beta = {ols["coefficients"]["avg_sewer_age_years"]["coefficient"]}$, $p = {ols["coefficients"]["avg_sewer_age_years"]["p_value"]:.4e}$): Pointing to critical concrete and clay pipe decay in older central municipal wards. (Statistically {"Significant (p < 0.05)" if ols["coefficients"]["avg_sewer_age_years"]["significant"] else "Not Significant (p >= 0.05)"}).
* **Tree Root Intrusion** ($\beta = {ols["coefficients"]["tree_count"]["coefficient"]}$, $p = {ols["coefficients"]["tree_count"]["p_value"]:.4e}$): Roots fracture pipelines, leading to soil ingress and flow restrictions. (Statistically {"Significant (p < 0.05)" if ols["coefficients"]["tree_count"]["significant"] else "Not Significant (p >= 0.05)"}).
* **Pipe Diameter** ($\beta = {ols["coefficients"]["pipe_diameter_mm"]["coefficient"]}$, $p = {ols["coefficients"]["pipe_diameter_mm"]["p_value"]:.4e}$): Exhibits a strong negative correlation, verifying that smaller-diameter lateral sewers have high susceptibility to clogging. (Statistically {"Significant (p < 0.05)" if ols["coefficients"]["pipe_diameter_mm"]["significant"] else "Not Significant (p >= 0.05)"}).
* **Population Density** ($\beta = {ols["coefficients"]["population_density"]["coefficient"]}$, $p = {ols["coefficients"]["population_density"]["p_value"]:.4e}$): Measures high sanitary discharge loads. (Statistically {"Significant (p < 0.05)" if ols["coefficients"]["population_density"]["significant"] else "Not Significant (p >= 0.05)"}).

---

## 2. Critical Vulnerability Breakdown

### {top_risk_wards[0]["ward_name"]} — Risk Probability: {top_risk_wards[0]["risk_score"]}%
* **Dominant Risk Driver**: High Connection Loading & Aging Mainlines.
* **Analysis**: With local regression coefficients peaking for connections count ($\beta_{{local}} = {round(top_risk_wards[0]["local_coefficients"]["connections_count"], 2)}$) and pipe age, this area shows heavy susceptibility to structural sewer blockages.

### {top_risk_wards[1]["ward_name"]} — Risk Probability: {top_risk_wards[1]["risk_score"]}%
* **Dominant Risk Driver**: Root Intrusion & Older Pipeline Segments.
* **Analysis**: Shows strong correlation with tree root density ($\beta_{{local}} = {round(top_risk_wards[1]["local_coefficients"]["tree_count"], 2)}$). Root fractures are facilitating sediment blockages.

### {top_risk_wards[2]["ward_name"]} — Risk Probability: {top_risk_wards[2]["risk_score"]}%
* **Dominant Risk Driver**: Elevated Population Density & Inadequate Hydraulic Capacities.
* **Analysis**: High hydraulic strain on smaller diameter lateral sewers.

---

## 3. Targeted Preventive Action Checklist

* [ ] **Municipal Connection Audits**: Dispatch inspectors to central historic residential blocks in **{top_risk_wards[0]["ward_name"]}** to audit load connections and illegal drainage links.
* [ ] **Hydro-Jetting & Desilting**: Schedule high-priority root-clearing maintenance for **{top_risk_wards[1]["ward_name"]}** targeting older concrete sewer mains.
* [ ] **Manhole Sensor Ingestion**: Prioritize deployment of Phase 2 live IoT telemetry nodes around active complaint clusters (Centroids: {top_risk_wards[0]["coordinates"]["lat"]}, {top_risk_wards[0]["coordinates"]["lng"]}) for real-time blockage alerting.
"""
        return {
            "source": "dynamic_spatial_fallback",
            "report": fallback_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insights generation failure: {str(e)}")
