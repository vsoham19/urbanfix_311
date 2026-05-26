from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
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

from generators.iot_sewer_data import AHMEDABAD_SEWER_WARDS, generate_iot_sewer_readings
from services.predictive_engine import run_regression_analysis

router = APIRouter(prefix="/iot", tags=["IoT Sewer Drainage"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    ward_a: Optional[str] = None
    ward_b: Optional[str] = None
    message: Optional[str] = ""
    history: Optional[List[ChatMessage]] = None
    mode: Optional[str] = "compare"  # "compare", "general", "predictive", or "anomaly"


def find_shortest_path(start_name: str, end_name: str, wards: list) -> Optional[list]:
    """
    Breadth-First Search (BFS) to identify shortest directed flow path 
    between two municipal wards based on the simulated ring & loop topology.
    """
    N = len(wards)
    ward_indices = {w["ward"]: i for i, w in enumerate(wards)}
    if start_name not in ward_indices or end_name not in ward_indices:
        return None
        
    start_idx = ward_indices[start_name]
    end_idx = ward_indices[end_name]
    
    if start_idx == end_idx:
        return [start_name]
        
    queue = [[start_idx]]
    visited = {start_idx}
    
    while queue:
        path = queue.pop(0)
        curr = path[-1]
        
        # Adjacent directed connections: neighbor (curr + 1) % N
        # And loop connection: (curr + 4) % N when curr % 3 == 0
        neighbors = [(curr + 1) % N]
        if curr % 3 == 0:
            neighbors.append((curr + 4) % N)
            
        for nxt in neighbors:
            if nxt == end_idx:
                full_path_indices = path + [nxt]
                return [wards[idx]["ward"] for idx in full_path_indices]
            if nxt not in visited:
                visited.add(nxt)
                queue.append(path + [nxt])
                
    return None


def _detect_mentioned_wards(message: str, selected_wards: set[str]) -> list[str]:
    if not message:
        return []

    message_lower = message.lower()
    mentioned = []
    for ward in AHMEDABAD_SEWER_WARDS:
        ward_name = ward["ward"]
        if ward_name in selected_wards:
            continue
        if ward_name.lower() in message_lower:
            mentioned.append(ward_name)
    return mentioned


def _hops(path: Optional[list]) -> Optional[int]:
    return len(path) - 1 if path else None


def _third_ward_analysis(third_ward: str, targets: list[str], readings_map: dict) -> dict:
    target_impacts = []
    impact_verdicts = []

    for target in targets:
        path_to_target = find_shortest_path(third_ward, target, AHMEDABAD_SEWER_WARDS)
        path_from_target = find_shortest_path(target, third_ward, AHMEDABAD_SEWER_WARDS)
        hops_to_target = _hops(path_to_target)
        hops_from_target = _hops(path_from_target)

        if hops_to_target is None:
            verdict = "invalid"
            explanation = f"No directed sewer path from {third_ward} to {target} was detected."
            is_upstream = False
        else:
            is_upstream = hops_from_target is None or hops_to_target < hops_from_target
            if is_upstream and hops_to_target <= 5:
                verdict = "significant"
                explanation = f"{third_ward} is upstream of {target} with a short {hops_to_target}-hop route."
            elif is_upstream and hops_to_target <= 10:
                verdict = "moderate"
                explanation = f"{third_ward} is upstream of {target}, but the {hops_to_target}-hop route weakens immediate impact."
            elif is_upstream:
                verdict = "weak"
                explanation = f"{third_ward} can hydraulically reach {target}, but the {hops_to_target}-hop path is too long for a strong direct effect."
            else:
                verdict = "not_significant"
                explanation = f"{third_ward} is not upstream of {target}; routine gravity-flow impact is unlikely except during severe backflow/surcharging."

        impact_verdicts.append(verdict)
        target_impacts.append({
            "target_ward": target,
            "path_to_target": path_to_target,
            "path_from_target": path_from_target,
            "hops_to_target": hops_to_target,
            "hops_from_target": hops_from_target,
            "is_upstream": is_upstream,
            "verdict": verdict,
            "explanation": explanation
        })

    if all(v in {"significant", "moderate"} for v in impact_verdicts):
        combined_verdict = "valid"
        combined_summary = f"{third_ward} can plausibly affect both selected wards at the same time through upstream sewer flow, though urgency depends on hop distance and current telemetry."
    elif any(v in {"significant", "moderate"} for v in impact_verdicts):
        combined_verdict = "partially_valid"
        combined_summary = f"{third_ward} has a valid hydraulic relationship with one selected ward, but not both at a meaningful level."
    elif all(v == "weak" for v in impact_verdicts):
        combined_verdict = "weak"
        combined_summary = f"{third_ward} is technically connected to both selected wards, but the paths are long, so a direct simultaneous effect is weak."
    else:
        combined_verdict = "not_valid"
        combined_summary = f"{third_ward} is not a strong upstream driver for both selected wards in this topology."

    reading = readings_map.get(third_ward, {})
    return {
        "third_ward": third_ward,
        "combined_verdict": combined_verdict,
        "combined_summary": combined_summary,
        "telemetry": {
            "device_id": reading.get("device_id"),
            "state_of_sewage": reading.get("state_of_sewage"),
            "state_reason": reading.get("state_reason"),
            "nitrogen mg/L": reading.get("nitrogen mg/L"),
            "phosphorous mg/L": reading.get("phosphorous mg/L"),
            "is_blocked": reading.get("is_blocked"),
            "maintenance_required": reading.get("maintenance_required")
        },
        "target_impacts": target_impacts
    }


@router.get("/sewer-readings")
async def get_live_sewer_readings():
    """
    System-generated mock stream that represents one IoT drainage sensor
    installed per Ahmedabad ward.
    """
    readings = generate_iot_sewer_readings()
    return {
        "source": "system_generated_iot_mock",
        "city": "Ahmedabad",
        "device_count": len(AHMEDABAD_SEWER_WARDS),
        "readings": readings,
    }


def is_relevant_to_infrastructure(message: str) -> bool:
    if not message:
        return False
    
    import re
    
    # 1. Standard infrastructure terms
    infra_keywords = [
        "drainage", "sewer", "sewage", "blockage", "manning", "pipe", "flooding", "flood", "clog",
        "nitrogen", "phosphorous", "phosphorus", "ahmedabad", "ward", "infrastructure", "pump", "flow",
        "hydraulic", "gwr", "regression", "hotspot", "civic", "complaint", "water", "conduit", "surcharge",
        "backflow", "sso", "treatment", "plant", "sensor", "telemetry", "diameter", "depth", "amc"
    ]
    message_lower = message.lower()
    if any(kw in message_lower for kw in infra_keywords):
        return True
        
    # 2. Friendly greetings or meta-questions (exact word matches or specific phrases)
    # This avoids matching arbitrary off-topic questions (like "What is the capital of France?")
    words = set(re.findall(r'\b\w+\b', message_lower))
    greetings = {"hi", "hello", "hey", "greetings", "welcome", "help", "who"}
    if words & greetings:
        return True
        
    # Meta phrases about the bot/system itself
    meta_phrases = [
        "what is this", "what do you do", "how to use", "what are the modes", 
        "how does this work", "tell me about this", "what can you do"
    ]
    if any(phrase in message_lower for phrase in meta_phrases):
        return True
        
    return False

async def _general_chat_impl(message: str, history: list):
    # Check local relevance first
    if not is_relevant_to_infrastructure(message):
        return {
            "status": "success",
            "source": "rejection_filter",
            "message": "This question is not valid or appropriate for the Ahmedabad Municipal Sewerage and Drainage system. Please ask an infrastructure-related query.",
            "topology": None
        }

    system_prompt = (
        "You are an expert AI City Planner, Civil Engineer, and Sewerage Systems Analyst "
        "for the Ahmedabad Municipal Corporation (AMC). Your job is to answer questions about the municipal "
        "sewage, drainage, pipeline networks, fluid dynamics, environmental impacts (nitrogen/phosphorus loads), "
        "civic complaint sorting, or other infrastructure systems related to Ahmedabad.\n\n"
        "CORE RULES:\n"
        "- You ONLY answer questions about the municipal sewage/drainage/infrastructure systems of Ahmedabad, fluid dynamics, "
        "civic complaints, or general questions about this chatbot's features, dashboard, and analytical capabilities.\n"
        "- You are explicitly allowed and encouraged to respond politely to greetings (e.g., 'hello', 'hi') and clearly explain what you can do (your 4 modes: Compare Wards, General Q&A, Predictive Forecast, and Warning Radar).\n"
        "- If the user asks a general question completely unrelated to Ahmedabad's sewers, drainage, civic infrastructure, or this dashboard (e.g. 'tell me a joke', "
        "'what is the capital of France', general coding, cooking, recipes, or other unrelated topics), you MUST refuse to answer. "
        "You should reply exactly with:\n"
        "'This question is not valid or appropriate for the Ahmedabad Municipal Sewerage and Drainage system. Please ask an infrastructure-related query.'\n"
        "- Be highly technical, crisp, authoritative, and precise when discussing sewerage topics. Avoid conversational filler except for introductory greetings."
    )

    context_prompt = f"""
    [AMC GENERAL MUNICIPAL QUERY]
    The user is asking a general municipal infrastructure/sewerage query under AMC jurisdiction:
    
    [USER INPUT QUESTION]
    {message}
    
    [OUTPUT INSTRUCTION]
    Provide a professional engineering response. If the query is vague or unrelated, refuse to answer per the system rules. Use professional LaTeX formatting and markdown elements where relevant.
    """

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if GROQ_API_KEY and "your_groq_api_key" not in GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            payload_messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                payload_messages.append({"role": msg.role, "content": msg.content})
            payload_messages.append({"role": "user", "content": context_prompt})
            
            response = client.chat.completions.create(
                messages=payload_messages,
                model="llama-3.3-70b-versatile",
                temperature=0.3
            )
            chat_reply = response.choices[0].message.content
            
            # Additional safety check on LLM's response
            if "not valid or appropriate" in chat_reply.lower() or "not valid" in chat_reply.lower() or "appropriate" in chat_reply.lower():
                if "please ask" in chat_reply.lower() or len(chat_reply) < 150:
                    chat_reply = "This question is not valid or appropriate for the Ahmedabad Municipal Sewerage and Drainage system. Please ask an infrastructure-related query."

            return {
                "status": "success",
                "source": "groq_llama3",
                "message": chat_reply,
                "topology": None
            }
        except Exception as err:
            print(f"[Groq Chat API Error] General LLaMA query failed: {err}. Triggering local fallback.")

    # High-Fidelity Local Fallback for general questions
    msg_lower = message.lower()
    
    if "manning" in msg_lower:
        fallback_message = """### Ahmedabad Municipal Sewerage Authority — Hydrological Engineering Brief

#### 1. Manning's Equation & Gravity Conduit Flow
Gravity sewer systems in Ahmedabad are designed and analyzed using the classic Manning's Equation for uniform flow:
$$V = \\frac{{1}}{{n}} R^{{2/3}} S^{{1/2}}$$
$$Q = A \\cdot V = A \\cdot \\frac{{1}}{{n}} R^{{2/3}} S^{{1/2}}$$

Where:
* $V$ is the average flow velocity (m/s).
* $Q$ is the volumetric flow rate ($m^3/s$).
* $n$ is the Manning's roughness coefficient (concrete pipes: $0.013$, PVC/smooth conduits: $0.009$).
* $R$ is the hydraulic radius ($R = A/P$, where $A$ is flow cross-section and $P$ is wetted perimeter; $R = D/4$ for full-pipe flow).
* $S$ is the energy slope / slope of the pipe conduit.

#### 2. Hydraulic Design Standards
* **Minimum Self-Cleansing Velocity**: To prevent silt deposition and solid accumulation, AMC guidelines mandate a minimum velocity of $0.6 \\text{ m/s}$ during peak daily flow.
* **Maximum Non-Erosive Velocity**: To prevent abrasive wear of concrete pipe linings, the velocity is capped at $2.5 \\text{ m/s}$.
* **Design Depth Ratio ($d/D$)**: Pipes are designed to flow at $0.75$ to $0.80$ full depth at peak flow to maintain a safe headspace for ventilation and air flow, preventing hydrogen sulfide ($H_2S$) gas buildup.
"""
    elif "gwr" in msg_lower or "regression" in msg_lower or "ols" in msg_lower:
        fallback_message = """### Ahmedabad Municipal Sewerage Authority — Spatial Predictive Engine Brief

#### 1. Ordinary Least Squares (OLS) Global Baseline
The predictive pipeline uses Ordinary Least Squares regression to establish a global baseline model for civic drainage blockages across all 54 wards:
$$\\text{Blockages} = \\beta_0 + \\beta_1 (\\text{SewerAge}) + \\beta_2 (\\text{TreeCount}) + \\beta_3 (\\text{Connections}) + \\beta_4 (\\text{PopDensity}) - \\beta_5 (\\text{PipeDiameter})$$

* **Key Statistical Drivers**:
  - **Sewer Age (Years)**: Strongest positive coefficient. Corresponds directly to physical conduit degradation and silt buildup.
  - **Tree Count (Roots)**: Positive coefficient representing root intrusion in structural joints.
  - **Pipe Diameter (mm)**: Negative coefficient, as larger diameters significantly decrease blockage probabilities.

#### 2. Geographically Weighted Regression (GWR) Localized Drift
While OLS provides a global average, sewerage dynamics exhibit massive spatial non-stationarity. GWR accounts for this by using spatial kernel weights:
$$y_i = \\beta_0(u_i, v_i) + \\sum_j \\beta_j(u_i, v_i) x_{ij} + \\varepsilon_i$$
Where $(u_i, v_i)$ represents the geographical centroid of ward $i$. 

This allows coefficients to drift locally. For example, Tree Count is a major failure driver in greener residential wards (e.g., Bodakdev), while Connection Count dominates in highly dense central wards (e.g., Kalupur).
"""
    elif "hotspot" in msg_lower or "dbscan" in msg_lower or "clustering" in msg_lower:
        fallback_message = """### Ahmedabad Municipal Sewerage Authority — Hotspot Clustering Brief

#### 1. Density-Based Spatial Clustering of Applications with Noise (DBSCAN)
Civic complaint data is inherently noisy and unevenly distributed. To locate high-priority maintenance targets, AMC applies the DBSCAN clustering algorithm to complaints:
* **Epsilon ($\\varepsilon$)**: Set to $0.015$ degrees (approx. $1.5 \\text{ km}$), which defines the neighborhood search radius.
* **MinPts**: Set to $3$ complaints. If $3$ or more complaints lie within the radius, a new cluster core is identified.

#### 2. Operational Benefits
* **Noise Filtering**: Outlier complaints (isolated single events) are filtered out as noise, allowing crews to focus on systemic issues.
* **Automated Dispatch**: Heavy suction trucks and desilting machinery are automatically dispatched to the centroids of these identified hotspots.
"""
    elif "nitrogen" in msg_lower or "phosphorous" in msg_lower or "phosphorus" in msg_lower or "chemical" in msg_lower:
        fallback_message = """### Ahmedabad Municipal Sewerage Authority — Chemical & Nutrient Analysis Brief

#### 1. Nutrient Loading Metrics
Real-time IoT sensors monitor chemical levels at outfall sewers in each ward to identify industrial discharge or domestic overloads:
* **Total Nitrogen (TN)**: Ideal target is $< 10 \\text{ mg/L}$. High levels ($> 25 \\text{ mg/L}$) indicate potential untreated commercial wastes or severe domestic septic seepage.
* **Total Phosphorous (TP)**: Ideal target is $< 2 \\text{ mg/L}$. Elevated phosphorus indicates heavy detergent discharge or commercial laundry wastes.

#### 2. Treatment & Biological Process Implications
Excessive chemical loads lead to:
* **Eutrophication**: High nitrogen/phosphorous in receiving water bodies (like the Sabarmati River) triggers rapid algae blooms, depleting dissolved oxygen.
* **Corrosion**: High organic loads lead to anaerobic conditions, producing hydrogen sulfide ($H_2S$), which converts to sulfuric acid and corrodes concrete sewers.
"""
    else:
        fallback_message = f"""### Ahmedabad Municipal Sewerage Authority — Infrastructure Information System

Thank you for your inquiry: *"{message}"*.

#### 1. System Context & Operations
The Ahmedabad Municipal Corporation (AMC) operates a directed graph sewer system comprising 54 wards. Inflow rates, pipe pressures, chemical concentrations, and physical pipe conditions are tracked via integrated telemetry:
* **Directed Flow Topology**: Wards are linked in a primary ring loop with lateral shortcuts for routing optimization.
* **Telemetry and Maintenance**: Suction crews utilize desilting machines, CIPP trenchless re-lining, and hydro-jetting to clear blockages and restore gravity-flow velocity.

#### 2. Available Expert Briefing Modules
To receive detailed mathematical and physical briefings, please include one of these keywords in your inquiry:
* **Manning**: Gravity conduit flow, velocity limits, and fluid calculations.
* **GWR / OLS**: Statistical regression analysis of civic failure factors.
* **DBSCAN / Hotspot**: Density-based spatial complaint clustering.
* **Nitrogen / Chemical**: Sewer chemistry, detergent indicators, and river protection.
"""

    return {
        "status": "success",
        "source": "fallback_spatial_hydrological_general",
        "message": fallback_message,
        "topology": None
    }


async def _predictive_chat_impl(message: str, history: list):
    # Check local relevance first
    if message and not is_relevant_to_infrastructure(message):
        return {
            "status": "success",
            "source": "rejection_filter",
            "message": "This question is not valid or appropriate for the Ahmedabad Municipal Sewerage and Drainage system. Please ask an infrastructure-related query.",
            "topology": None
        }

    # Run GWR regression analysis
    try:
        regression_data = run_regression_analysis(bandwidth=0.08)
        if "error" in regression_data:
            raise HTTPException(status_code=400, detail=regression_data["error"])
        
        sorted_wards = sorted(regression_data["gwr_risk_heatmap"], key=lambda x: x["risk_score"], reverse=True)
        top_risk_wards = sorted_wards[:3]
        ols = regression_data["global_regression"]
    except Exception as e:
        print(f"[Predictive Ingestion Error] Failed to get regression data: {e}")
        return {
            "status": "success",
            "source": "predictive_error_fallback",
            "message": "Error calculating statistical GWR monsoon forecast. Please check if database is seeded.",
            "topology": None
        }

    system_prompt = (
        "You are an expert AI City Planner, Hydrological Analyst, and Monsoon Risk Planner "
        "for the Ahmedabad Municipal Corporation (AMC). Your job is to advise municipal officials "
        "on which wards are likely to experience severe drainage and sewer blockages in the upcoming monsoon "
        "using Geographically Weighted Regression (GWR) statistics.\n\n"
        "CORE RULES:\n"
        "- Focus ONLY on Ahmedabad's wards, GWR regression risk metrics, sewer ages, tree root intrusions, "
        "and active connection counts. Do NOT answer generic questions.\n"
        "- Use the statistical regression parameters provided to explain localized factors "
        "driving vulnerabilities.\n"
        "- Incorporate mathematical LaTeX expressions where appropriate (e.g. OLS regression drift, GWR weights).\n"
        "- Provide a professional, highly detailed, technical report. Avoid filler words."
    )

    context_prompt = f"""
    [AMC MONSOON GWR PREDICTIVE DATA]
    The user is asking a monsoon sewer risk forecasting question. Use the following dynamic regression data:
    
    - Global OLS R-Squared Score: {ols["r2_score"]}
    - Adjusted R-Squared: {ols["r2_adj"]}
    - OLS Regression Formula: Blockages = {ols["intercept"]["coefficient"]} + ({ols["coefficients"]["avg_sewer_age_years"]["coefficient"]} * SewerAge) + ({ols["coefficients"]["tree_count"]["coefficient"]} * Trees) + ({ols["coefficients"]["connections_count"]["coefficient"]} * Connections) + ({ols["coefficients"]["population_density"]["coefficient"]} * PopDensity) + ({ols["coefficients"]["pipe_diameter_mm"]["coefficient"]} * PipeDiameter)
    
    - Top 3 Highest Risk Wards (GWR calculated probability):
      1. {top_risk_wards[0]["ward_name"]}: Risk Score = {top_risk_wards[0]["risk_score"]}% (Coefficients: SewerAge={round(top_risk_wards[0]["local_coefficients"]["avg_sewer_age_years"], 2)}, Trees={round(top_risk_wards[0]["local_coefficients"]["tree_count"], 2)}, Connections={round(top_risk_wards[0]["local_coefficients"]["connections_count"], 2)})
      2. {top_risk_wards[1]["ward_name"]}: Risk Score = {top_risk_wards[1]["risk_score"]}% (Coefficients: SewerAge={round(top_risk_wards[1]["local_coefficients"]["avg_sewer_age_years"], 2)}, Trees={round(top_risk_wards[1]["local_coefficients"]["tree_count"], 2)}, Connections={round(top_risk_wards[1]["local_coefficients"]["connections_count"], 2)})
      3. {top_risk_wards[2]["ward_name"]}: Risk Score = {top_risk_wards[2]["risk_score"]}%
    
    [USER INPUT QUESTION]
    {message if message else "Which wards are likely to have sewer issues next monsoon based on current data?"}
    
    [OUTPUT INSTRUCTION]
    Address the user inquiry by structuring your response in clean markdown:
    1. **Monsoon Forecast Overview**: A summary of overall municipal sewer risk using the OLS coefficients and parameters.
    2. **Top Risk Zone Analysis**: Detail the top 3 wards identified by GWR, explaining *why* they are high risk based on their GWR coefficients.
    3. **Pre-Monsoon Preventive Checklist**: Provide a list of 3-4 specific operations (desilting, hydraulic capacity expansion, root barriers) prioritized by ward.
    """

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if GROQ_API_KEY and "your_groq_api_key" not in GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            payload_messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                payload_messages.append({"role": msg.role, "content": msg.content})
            payload_messages.append({"role": "user", "content": context_prompt})
            
            response = client.chat.completions.create(
                messages=payload_messages,
                model="llama-3.3-70b-versatile",
                temperature=0.3
            )
            chat_reply = response.choices[0].message.content
            return {
                "status": "success",
                "source": "groq_llama3",
                "message": chat_reply,
                "topology": None
            }
        except Exception as err:
            print(f"[Groq Chat API Error] Predictive forecast query failed: {err}. Triggering local fallback.")

    # High-Fidelity Local Fallback for predictive forecast
    fallback_message = f"""### Ahmedabad Municipal Sewerage Authority — Spatial Predictive Monsoon Forecast

#### 1. OLS Baseline & Statistical Risk Drivers
Our global Ordinary Least Squares (OLS) model establishes a highly accurate baseline for AMC sewer blockages ($R^2 = {ols["r2_score"]}$, Adjusted $R^2 = {ols["r2_adj"]}$):
$$\\text{{Blockages}} = {ols["intercept"]["coefficient"]} + {ols["coefficients"]["avg_sewer_age_years"]["coefficient"]}(\\text{{Age}}) + {ols["coefficients"]["tree_count"]["coefficient"]}(\\text{{Roots}}) + {ols["coefficients"]["connections_count"]["coefficient"]}(\\text{{Connections}}) - {abs(ols["coefficients"]["pipe_diameter_mm"]["coefficient"])}(\\text{{Diameter}})$$

This shows that **sewer age** and **connection loading** represent the strongest positive global risk drivers, while pipe diameter acts as a crucial mitigation vector.

#### 2. GWR Localized Monsoon Risk Warnings
Using Geographically Weighted Regression (GWR), we identify high-probability blockage hotspots for the upcoming monsoon, mapped by localized coefficient drift:
* **{top_risk_wards[0]["ward_name"]} (Risk: {top_risk_wards[0]["risk_score"]}%)**: Primarily driven by high connection loading ($\\beta_{{local}} = {round(top_risk_wards[0]["local_coefficients"]["connections_count"], 2)}$). Heavy household discharge during the monsoon will overwhelm capacity.
* **{top_risk_wards[1]["ward_name"]} (Risk: {top_risk_wards[1]["risk_score"]}%)**: Heavily influenced by structural aging and tree root intrusion ($\\beta_{{local}} = {round(top_risk_wards[1]["local_coefficients"]["tree_count"], 2)}$). Root fractures facilitate water ingress and sand siltation.
* **{top_risk_wards[2]["ward_name"]} (Risk: {top_risk_wards[2]["risk_score"]}%)**: High risk due to small pipeline diameters bottlenecking elevated population density flows.

#### 3. Priority Pre-Monsoon Action Plan
- [ ] **Capacity Audits in {top_risk_wards[0]["ward_name"]}**: Audit high-load industrial and commercial connections to enforce grease trap maintenance before rain events.
- [ ] **Desilting & Root Cleansings in {top_risk_wards[1]["ward_name"]}**: Deploy high-velocity hydro-jetters to scour roots and accumulated sediment from aging mainlines.
- [ ] **Bypass Pumping Assets**: Pre-stage emergency suction pumps in **{top_risk_wards[2]["ward_name"]}** to cope with localized surcharging and prevent street floods.
"""

    return {
        "status": "success",
        "source": "fallback_predictive_monsoon",
        "message": fallback_message,
        "topology": None
    }


async def _anomaly_chat_impl(message: str, history: list):
    # Fetch live readings
    readings = generate_iot_sewer_readings()
    
    # Filter anomalies (state_of_sewage != 'normal' or is_blocked == 'Y')
    anomalies = [r for r in readings if r.get("state_of_sewage") != "normal" or r.get("is_blocked") == "Y"]
    
    if not anomalies:
        return {
            "status": "success",
            "source": "anomaly_scanner",
            "message": "### 🚨 Ahmedabad Sewer Telemetry Radar — Active Anomalies\n\n**Radar Scan Result: ALL SYSTEMS CLEAR**\n\nNo hydraulic surcharging, blockage propagation, or critical nutrient loadings were detected in the active telemetry streams across the 54 wards of Ahmedabad.",
            "topology": None
        }

    # Format anomalies summary
    anomalies_lines = []
    for idx, r in enumerate(anomalies[:5], start=1):
        anomalies_lines.append(
            f"{idx}. Ward: **{r['ward_name']}** (Device: `{r['device_id']}`)\n"
            f"   - **State**: {r['state_of_sewage'].upper()} ({r['state_reason']})\n"
            f"   - **Telemetry**: Nitrogen = {r['nitrogen mg/L']} mg/L, Phosphorous = {r['phosphorous mg/L']} mg/L, Blocked: `{r['is_blocked']}`\n"
            f"   - **Specs**: Pipe $\\phi = {r['pipe_diameter_mm']} \\text{{ mm}}$, Age = {r['pipe_age_years']} yrs, Groundwater = {r['groundwater_level_m']} m\n"
            f"   - **Maintenance Directive**: {r['maintenance_required']}\n"
        )
    anomalies_context = "\n".join(anomalies_lines)

    system_prompt = (
        "You are the Lead Emergency Control Coordinator for the Ahmedabad Municipal Sewerage Authority. "
        "Your job is to parse live telemetry anomaly warnings and issue high-intensity, structured emergency briefs "
        "and concrete dispatch orders to maintenance crews.\n\n"
        "CORE RULES:\n"
        "- Focus ONLY on the provided active telemetry anomalies.\n"
        "- Be professional, urgent, authoritative, and precise.\n"
        "- List specific equipment and dispatches (e.g. hydro-jetting, desilting, chemical dosing units)."
    )

    context_prompt = f"""
    [ACTIVE SEWER TELEMETRY ANOMALIES]
    The emergency control center has detected the following active anomalies in Ahmedabad:
    
    {anomalies_context}
    
    [OUTPUT INSTRUCTION]
    Format a high-intensity, structured AMC Emergency Dispatch Report in markdown:
    1. **Emergency Threat Level & Overview**: An overview of active failures, stating if there is a threat of Sanitary Sewer Overflows (SSOs) or river contamination.
    2. **Detailed Anomalies Breakdown & Diagnosis**: Diagnoses for the affected wards, comparing chemical loads or structural blocks.
    3. **Immediate Operational Dispatch Orders**: 2-3 prioritized crew dispatches (e.g. suction trucks, hydro-jetters, or chemical dosing units) with exact instructions.
    """

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if GROQ_API_KEY and "your_groq_api_key" not in GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            payload_messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                payload_messages.append({"role": msg.role, "content": msg.content})
            payload_messages.append({"role": "user", "content": context_prompt})
            
            response = client.chat.completions.create(
                messages=payload_messages,
                model="llama-3.3-70b-versatile",
                temperature=0.3
            )
            chat_reply = response.choices[0].message.content
            return {
                "status": "success",
                "source": "groq_llama3",
                "message": chat_reply,
                "topology": None
            }
        except Exception as err:
            print(f"[Groq Chat API Error] Anomaly dispatcher query failed: {err}. Triggering local fallback.")

    # High-Fidelity Local Fallback for anomaly alert
    fallback_message_parts = [
        "### 🚨 Ahmedabad Sewer Telemetry Radar — Emergency Dispatch Briefing",
        f"**Threat Assessment Level: HIGH** — {len(anomalies)} active hydraulic and chemical anomalies detected in current scan.",
        "\n#### 1. Prioritized Anomalies Diagnosis\n"
    ]
    for idx, r in enumerate(anomalies[:4], start=1):
        status_color = "🔴 CRITICAL" if r['state_of_sewage'] == 'critical' else "🟡 WARNING"
        fallback_message_parts.append(
            f"* **{r['ward_name']}** (Device: `{r['device_id']}`) — **{status_color}**:\n"
            f"  - **Failure Vector**: {r['state_reason']}\n"
            f"  - **Telemetry**: $TN = {r['nitrogen mg/L']} \\text{{ mg/L}}$ (limit: 10), $TP = {r['phosphorous mg/L']} \\text{{ mg/L}}$ (limit: 2). Blocked: `{r['is_blocked']}`\n"
            f"  - **Structural Risk**: Aging $\\phi = {r['pipe_diameter_mm']} \\text{{ mm}}$ mainline ({r['pipe_age_years']} yrs old), high groundwater table ($d_{{gw}} = {r['groundwater_level_m']} \\text{{ m}}$).\n"
            f"  - **Directive**: *{r['maintenance_required']}*\n"
        )

    fallback_message_parts.append("\n#### 2. Immediate Operational Dispatch Orders\n")
    critical_wards = [r['ward_name'] for r in anomalies if r['state_of_sewage'] == 'critical'][:2]
    warning_wards = [r['ward_name'] for r in anomalies if r['state_of_sewage'] == 'warning'][:2]

    if critical_wards:
        fallback_message_parts.append(
            f"- [ ] **Priority 1: Heavy Desilting Dispatch**: Deploy AMC heavy hydro-jetting and vacuum desilting tankers to **{', '.join(critical_wards)}** immediately to clear active pipe blockages and mitigate sewer backup.\n"
        )
    if warning_wards:
        fallback_message_parts.append(
            f"- [ ] **Priority 2: Nutrient Outfall Control**: Deploy chemical neutralizing agents and dispatch industrial source inspectors to commercial zones in **{', '.join(warning_wards)}** to locate and plug illegal effluent discharges.\n"
        )
    fallback_message_parts.append(
        "- [ ] **Priority 3: Infiltration Auditing**: Mobilize sewer camera inspection crews (CCTV) to wards with groundwater tables $< 2.0 \\text{ m}$ to audit joints for structural infiltration.\n"
    )

    return {
        "status": "success",
        "source": "fallback_anomaly_radar",
        "message": "".join(fallback_message_parts),
        "topology": None
    }


@router.post("/chat")
async def chat_about_wards_relationship(req: ChatRequest):
    """
    Specialized comparative and general chatbot route powered by Groq LLaMA 3.3.
    Supports comparative ward analyses and general infrastructure queries under AMC domain.
    """
    mode = req.mode or "compare"
    ward_a = req.ward_a
    ward_b = req.ward_b
    message = req.message
    history = req.history or []
    
    import traceback as _tb
    try:
        if mode == "general":
            return await _general_chat_impl(message, history)
        elif mode == "predictive":
            return await _predictive_chat_impl(message, history)
        elif mode == "anomaly":
            return await _anomaly_chat_impl(message, history)
        else:
            return await _chat_impl(ward_a, ward_b, message, history)
    except HTTPException:
        raise
    except Exception as e:
        _tb.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _chat_impl(ward_a, ward_b, message, history):
    
    # 1. Fetch live sewer telemetry readings
    readings = generate_iot_sewer_readings()
    readings_map = {r["ward_name"]: r for r in readings}
    
    reading_a = readings_map.get(ward_a)
    reading_b = readings_map.get(ward_b)
    
    if not reading_a or not reading_b:
        raise HTTPException(
            status_code=404, 
            detail=f"Telemetry missing for requested wards: {ward_a} or {ward_b}"
        )
        
    # 2. Run graph search to trace topological connections
    path_a_to_b = find_shortest_path(ward_a, ward_b, AHMEDABAD_SEWER_WARDS)
    path_b_to_a = find_shortest_path(ward_b, ward_a, AHMEDABAD_SEWER_WARDS)
    
    hops_a_to_b = len(path_a_to_b) - 1 if path_a_to_b else 999
    hops_b_to_a = len(path_b_to_a) - 1 if path_b_to_a else 999
    
    # Determine flow relation
    if hops_a_to_b == 999 and hops_b_to_a == 999:
        flow_summary = f"No direct topological pipeline path detected between {ward_a} and {ward_b}."
    elif hops_a_to_b < hops_b_to_a:
        flow_summary = f"{ward_a} is upstream of {ward_b} in the active sewer network loop. Flow travels downstream from {ward_a} to {ward_b} in {hops_a_to_b} hops."
    elif hops_b_to_a < hops_a_to_b:
        flow_summary = f"{ward_b} is upstream of {ward_a} in the active sewer network loop. Flow travels downstream from {ward_b} to {ward_a} in {hops_b_to_a} hops."
    else:
        flow_summary = f"{ward_a} and {ward_b} are in an equidistant structural sewer ring feedback loop."

    mentioned_wards = _detect_mentioned_wards(message, {ward_a, ward_b})
    third_ward_context = [
        _third_ward_analysis(mentioned_ward, [ward_a, ward_b], readings_map)
        for mentioned_ward in mentioned_wards
    ]

    third_ward_prompt = "No third ward was mentioned in the user question."
    if third_ward_context:
        third_ward_lines = []
        for analysis in third_ward_context:
            telemetry = analysis["telemetry"]
            third_ward_lines.append(
                f"- Third Ward: {analysis['third_ward']}\n"
                f"  Combined Verdict: {analysis['combined_verdict']} - {analysis['combined_summary']}\n"
                f"  Telemetry: state={telemetry.get('state_of_sewage')}, reason={telemetry.get('state_reason')}, "
                f"N={telemetry.get('nitrogen mg/L')} mg/L, P={telemetry.get('phosphorous mg/L')} mg/L, blocked={telemetry.get('is_blocked')}\n"
            )
            for impact in analysis["target_impacts"]:
                third_ward_lines.append(
                    f"  Target {impact['target_ward']}: verdict={impact['verdict']}, "
                    f"path={' -> '.join(impact['path_to_target']) if impact['path_to_target'] else 'No path'}, "
                    f"hops={impact['hops_to_target']}, explanation={impact['explanation']}\n"
                )
        third_ward_prompt = "".join(third_ward_lines)
        
    # 3. Formulate Groq Expert System Prompt
    system_prompt = (
        "You are a Lead Municipal Hydraulic Planning Engineer and Sewerage Systems Analyst "
        "for the Ahmedabad Municipal Corporation (AMC). Your job is to advise municipal crews "
        "and city planners about the specific relationship between two wards' drainage and sewage networks.\n\n"
        "CORE RULES:\n"
        "- You are NOT a generic assistant. You only answer questions about the municipal sewage/drainage systems "
        "of the selected wards, any other valid ward explicitly mentioned by the user, their pipe specifications, "
        "chemical loads, blockage propagation, and backflow risks.\n"
        "- If the user mentions a third ward, give a direct verdict first: valid, partially valid, weak, or not valid. "
        "Explain whether it can affect both selected wards at the same time based on upstream/downstream topology and hop distance.\n"
        "- If a user asks a general question unrelated to municipal sewers/drainage of these wards (e.g. 'tell me a joke' "
        "or 'what is the capital of France'), politely decline and redirect them back to comparing the two wards.\n"
        "- Use professional LaTeX equations to represent fluid dynamics where appropriate (e.g., Manning's Equation for gravity pipe velocity: "
        "$$V = \\frac{1}{n} R^{2/3} S^{1/2}$$ or friction head loss $$h_f = f \\frac{L}{D} \\frac{V^2}{2g}$$).\n"
        "- Be highly technical, crisp, authoritative, and precise. Avoid conversational filler."
    )
    
    # Injected real-time data context
    context_prompt = f"""
    [MUNICIPAL SEWER TELEMETRY DATA]
    WARD A: {ward_a}
    - Sensor ID: {reading_a.get('device_id')}
    - Sewage Status: {reading_a.get('state_of_sewage', 'normal').upper()} ({reading_a.get('state_reason', 'N/A')})
    - Chemical Load: Nitrogen = {reading_a.get('nitrogen mg/L')} mg/L, Phosphorous = {reading_a.get('phosphorous mg/L')} mg/L
    - Pipeline Specs: Diameter = {reading_a.get('pipe_diameter_mm')} mm, Installation = {reading_a.get('installation_method')}, Age = {reading_a.get('pipe_age_years')} years, Length = {reading_a.get('pipe_length_m')} m, Depth = {reading_a.get('pipe_depth_m')} m
    - Active Connections Load: {reading_a.get('connections_count')} connections
    - Environmental Factors: Groundwater Depth = {reading_a.get('groundwater_level_m')} m, Conditions = {reading_a.get('environmental_conditions')}
    - Blockage telemetries: Blocked = {reading_a.get('is_blocked')}, Maintenance = {reading_a.get('maintenance_required')}
    
    WARD B: {ward_b}
    - Sensor ID: {reading_b.get('device_id')}
    - Sewage Status: {reading_b.get('state_of_sewage', 'normal').upper()} ({reading_b.get('state_reason', 'N/A')})
    - Chemical Load: Nitrogen = {reading_b.get('nitrogen mg/L')} mg/L, Phosphorous = {reading_b.get('phosphorous mg/L')} mg/L
    - Pipeline Specs: Diameter = {reading_b.get('pipe_diameter_mm')} mm, Installation = {reading_b.get('installation_method')}, Age = {reading_b.get('pipe_age_years')} years, Length = {reading_b.get('pipe_length_m')} m, Depth = {reading_b.get('pipe_depth_m')} m
    - Active Connections Load: {reading_b.get('connections_count')} connections
    - Environmental Factors: Groundwater Depth = {reading_b.get('groundwater_level_m')} m, Conditions = {reading_b.get('environmental_conditions')}
    - Blockage telemetries: Blocked = {reading_b.get('is_blocked')}, Maintenance = {reading_b.get('maintenance_required')}
    
    [TOPOLOGICAL NETWORK PATH RELATIONSHIP]
    - Shortest Flow Path {ward_a} -> {ward_b}: {(' -> '.join(path_a_to_b)) if path_a_to_b else 'No path detected'}
    - Shortest Flow Path {ward_b} -> {ward_a}: {(' -> '.join(path_b_to_a)) if path_b_to_a else 'No path detected'}
    - Topological Flow Analysis: {flow_summary}

    [ADDITIONAL WARDS MENTIONED IN USER QUERY]
    {third_ward_prompt}
    
    [USER INPUT QUESTION]
    {message if message else "Compare the drainage/sewage systems of these two wards and outline their mutual hydraulic effects."}
    
    [OUTPUT INSTRUCTION]
    Address the user inquiry by structuring your response in clean markdown:
    1. **Topological Flow Assessment**: State their connection relationship, hops, and how wastewater travels between them.
    2. **Third Ward Verdict**: If another ward is mentioned, say clearly whether that ward can affect both selected wards at the same time. If not valid, say why directly.
    3. **Telemetry Comparison**: Compare Nitrogen/Phosphorus loads, pipe age, and structural parameters.
    4. **Hydraulic Surcharging & Blockage Impact**: Using LaTeX fluid equations, describe how a blockage or surge in one ward affects the downstream ward, mentioning backflow risks or sewer overflows (SSOs).
    5. **Actionable Engineering Checklist**: Provide 2-3 precise recommendations for maintenance crews.
    """
    
    # 4. Attempt Groq API invocation
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if GROQ_API_KEY and "your_groq_api_key" not in GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            
            # Reconstruct messaging payload
            payload_messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                payload_messages.append({"role": msg.role, "content": msg.content})
            payload_messages.append({"role": "user", "content": context_prompt})
            
            response = client.chat.completions.create(
                messages=payload_messages,
                model="llama-3.3-70b-versatile",
                temperature=0.3
            )
            chat_reply = response.choices[0].message.content
            return {
                "status": "success",
                "source": "groq_llama3",
                "message": chat_reply,
                "topology": {
                    "path_a_to_b": path_a_to_b,
                    "path_b_to_a": path_b_to_a,
                    "hops_a_to_b": hops_a_to_b if hops_a_to_b != 999 else None,
                    "hops_b_to_a": hops_b_to_a if hops_b_to_a != 999 else None,
                    "flow_summary": flow_summary,
                    "third_ward_context": third_ward_context
                }
            }
        except Exception as err:
            print(f"[Groq Chat API Error] LLaMA query failed: {err}. Triggering engineering fallback.")
            
    # 5. Local High-Fidelity Engineering Fallback
    path_a_to_b_str = " -> ".join(path_a_to_b) if path_a_to_b else "None"
    path_b_to_a_str = " -> ".join(path_b_to_a) if path_b_to_a else "None"
    upstream_ward = ward_a if hops_a_to_b < hops_b_to_a else ward_b
    downstream_ward = ward_b if hops_a_to_b < hops_b_to_a else ward_a
    third_ward_fallback = ""
    profile_section_number = 2

    if third_ward_context:
        profile_section_number = 3
        third_ward_fallback_parts = ["\n#### 2. Third Ward Validity Check\n"]
        for analysis in third_ward_context:
            third_ward_fallback_parts.append(
                f"* **{analysis['third_ward']} Verdict**: `{analysis['combined_verdict'].upper()}` - {analysis['combined_summary']}\n"
            )
            for impact in analysis["target_impacts"]:
                path = " -> ".join(impact["path_to_target"]) if impact["path_to_target"] else "No path"
                third_ward_fallback_parts.append(
                    f"  - Against **{impact['target_ward']}**: `{impact['verdict'].upper()}`; path `{path}` "
                    f"({impact['hops_to_target'] if impact['hops_to_target'] is not None else 0} hops). {impact['explanation']}\n"
                )
        third_ward_fallback = "".join(third_ward_fallback_parts)
    
    fallback_response = f"""### Ahmedabad Municipal Sewerage Authority - Hydrological Engineering Brief

#### 1. Topological & Hydraulic Flow Analysis
* **Network Connectivity**:
  - The directed flow path from **{ward_a}** to **{ward_b}** is `{path_a_to_b_str}` ({hops_a_to_b if hops_a_to_b != 999 else 0} hops).
  - The directed flow path from **{ward_b}** to **{ward_a}** is `{path_b_to_a_str}` ({hops_b_to_a if hops_b_to_a != 999 else 0} hops).
  - **Flow Dynamics**: {flow_summary}
{third_ward_fallback}
  
#### {profile_section_number}. Live Telemetry Comparative Profile
* **Ward {ward_a} ({reading_a.get('device_id')})**:
  - **Sewer Status**: `{reading_a.get('state_of_sewage', 'normal').upper()}` - *{reading_a.get('state_reason', '')}*
  - **Hydraulic Specs**: $\\phi = {reading_a.get('pipe_diameter_mm')} \\text{{ mm}}$ conduit, depth = {reading_a.get('pipe_depth_m')} m, age = {reading_a.get('pipe_age_years')} years.
  - **Loading**: {reading_a.get('connections_count')} active connections creating discharge.
  - **Chemistry**: Nitrogen = {reading_a.get('nitrogen mg/L')} mg/L, Phosphorous = {reading_a.get('phosphorous mg/L')} mg/L.
  
* **Ward {ward_b} ({reading_b.get('device_id')})**:
  - **Sewer Status**: `{reading_b.get('state_of_sewage', 'normal').upper()}` - *{reading_b.get('state_reason', '')}*
  - **Hydraulic Specs**: $\\phi = {reading_b.get('pipe_diameter_mm')} \\text{{ mm}}$ conduit, depth = {reading_b.get('pipe_depth_m')} m, age = {reading_b.get('pipe_age_years')} years.
  - **Loading**: {reading_b.get('connections_count')} active connections.
  - **Chemistry**: Nitrogen = {reading_b.get('nitrogen mg/L')} mg/L, Phosphorous = {reading_b.get('phosphorous mg/L')} mg/L.

#### {profile_section_number + 1}. Hydraulic Risk & Surcharging Propagation
Using Manning's gravity flow equation:
$$Q = A \\cdot V = A \\cdot \\frac{{1}}{{n}} R^{{2/3}} S^{{1/2}}$$
Where:
* $Q$ is the volumetric flow rate.
* $A$ is the cross-sectional flow area (determined by pipeline diameter $\\phi$).
* $n$ is the Manning's roughness coefficient (concrete: $n \\approx 0.013$, PVC: $n \\approx 0.009$).
* $R$ is the hydraulic radius ($R = D/4$ for full pipe flow).
* $S$ is the energy slope.

A blockage in the upstream segment (**{upstream_ward}**) will cause immediate surcharging, raising the hydraulic grade line (HGL) above the energy grade line. This triggers severe **backflow and sanitary sewer overflows (SSOs)** in adjacent lateral connections, directly compounding flooding risks down in the **{downstream_ward}** segment.

#### {profile_section_number + 2}. Actionable Engineering Checklist
- [ ] **Upstream Flush Audit**: Deploy high-velocity hydro-jetting units in **{upstream_ward}** to clear active siltation and tree roots.
- [ ] **Lateral Backflow Mitigation**: Mandate dual-plate backwater valves on all lateral links downstream in **{downstream_ward}** to safeguard against surcharging during heavy flows.
- [ ] **Sewer Age Re-lining**: Prioritize trenchless CIPP (Cured-In-Place Pipe) structural re-lining for sections exceeding 35 years in age to mitigate collapse risks.
"""
    return {
        "status": "success",
        "source": "fallback_spatial_hydrological",
        "message": fallback_response,
        "topology": {
            "path_a_to_b": path_a_to_b,
            "path_b_to_a": path_b_to_a,
            "hops_a_to_b": hops_a_to_b if hops_a_to_b != 999 else None,
            "hops_b_to_a": hops_b_to_a if hops_b_to_a != 999 else None,
            "flow_summary": flow_summary,
            "third_ward_context": third_ward_context
        }
    }


@router.get("/wards-boundaries")
async def get_wards_boundaries():
    """
    Parses Ahmedabad ward boundaries from KML and integrates
    live IoT sewer readings + historical 311 complaints to calculate
    a unified Combined Risk Score.
    """
    import xml.etree.ElementTree as ET
    from services.supabase_client import DBWrapper
    
    # 1. Resolve paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_dir = os.path.dirname(current_dir)
    root_dir = os.path.dirname(server_dir)
    
    # Try server directory first (for Render cloud environments), fallback to root parent directory
    kml_path = os.path.join(server_dir, "ahmedabad_wards_map_2024.kml")
    if not os.path.exists(kml_path):
        kml_path = os.path.join(root_dir, "ahmedabad_wards_map_2024.kml")
    
    if not os.path.exists(kml_path):
        raise HTTPException(status_code=404, detail=f"KML map file not found at {kml_path}")
        
    # 2. Parse KML
    try:
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        tree = ET.parse(kml_path)
        kml_root = tree.getroot()
        placemarks = kml_root.findall('.//kml:Placemark', ns)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse KML file: {str(e)}")
        
    # 3. KML to Generator ward mapping dictionary
    kml_to_gen_map = {
        "Amraiwadi": "Amraivadi",
        "Asarwa": "Asarva",
        "Bapu Nagar": "Bapunagar",
        "Bhaipura Hatkeshwar": "Bhaipura-Hatkeshvar",
        "Ghatlodia": "Ghatlodiya",
        "India colony": "India Colony",
        "Khadia": "Khadiya",
        "Kuber Nagar": "Kubernagar",
        "Mani Nagar": "Maninagar",
        "New Wadaj": "New Vadaj",
        "S. P. Stadium": "SP Stadium",
        "Saijpur Bogha": "Saijpurbogha",
        "Saraspur-Rakhiyal": "Saraspur",
        "Sardar Nagar": "Sardarnagar",
        "Shahibag": "Shahibaug",
        "Virat Nagar": "Viratnagar",
    }
    
    # 4. Load database complaints and group by normalized ward names
    try:
        structured_records = DBWrapper.get_records("structured_records")
    except Exception as e:
        print(f"[Wards Endpoint Warning] Failed to fetch database complaints: {e}")
        structured_records = []
        
    def normalize_name(name):
        if not name:
            return ""
        return name.lower().replace(" ", "").replace("-", "").replace(".", "").replace("y", "i").replace("w", "v")
        
    # Standard ward mapping
    norm_gen_map = {normalize_name(w["ward"]): w["ward"] for w in AHMEDABAD_SEWER_WARDS}
    
    complaints_per_ward = {w["ward"]: 0 for w in AHMEDABAD_SEWER_WARDS}
    complaints_details = {w["ward"]: [] for w in AHMEDABAD_SEWER_WARDS}
    
    for record in structured_records:
        record_ward = record.get("ward_name")
        if not record_ward:
            continue
        norm_ward = normalize_name(record_ward)
        if norm_ward in norm_gen_map:
            matched_ward = norm_gen_map[norm_ward]
            complaints_per_ward[matched_ward] += 1
            complaints_details[matched_ward].append({
                "complaint_id": record.get("complaint_id", "311-REC"),
                "category": record.get("complaint_category", "Drainage Outflow"),
                "severity": record.get("severity", "medium"),
                "description": record.get("description", ""),
                "date_filed": record.get("date_filed", "")
            })
            
    max_complaints = max(complaints_per_ward.values()) if complaints_per_ward else 0
    
    # 5. Load live IoT sewer readings
    try:
        iot_readings = generate_iot_sewer_readings()
        iot_readings_map = {r["ward_name"]: r for r in iot_readings}
    except Exception as e:
        print(f"[Wards Endpoint Warning] Failed to fetch live IoT sensor readings: {e}")
        iot_readings_map = {}
        
    # 6. Map and build KML features
    features = []
    for pm in placemarks:
        # Get KML Ward Name
        kml_name = None
        simple_datas = pm.findall('.//kml:SimpleData', ns)
        for sd in simple_datas:
            if sd.attrib.get('name') == 'sourcewardname':
                kml_name = sd.text
                break
                
        if not kml_name:
            continue
            
        # Map KML name to Generator / Database name
        gen_name = kml_to_gen_map.get(kml_name, kml_name)
        
        # Get coordinates
        coord_nodes = pm.findall('.//kml:coordinates', ns)
        if not coord_nodes:
            continue
            
        polygons = []
        for cn in coord_nodes:
            coord_str = cn.text.strip()
            pts = []
            for pt in coord_str.split():
                parts = pt.split(',')
                if len(parts) >= 2:
                    try:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        pts.append([lat, lon]) # Leaflet standard: [lat, lng]
                    except ValueError:
                        pass
            if pts:
                polygons.append(pts)
                
        if not polygons:
            continue
            
        # 7. Compute Combined Risk Score
        # IoT Risk: normal = 2.0, warning = 6.0, critical = 10.0
        reading = iot_readings_map.get(gen_name, {})
        iot_state = reading.get("state_of_sewage", "normal")
        if iot_state == "critical":
            iot_risk_score = 10.0
        elif iot_state == "warning":
            iot_risk_score = 6.0
        else:
            iot_risk_score = 2.0
            
        # 311 Complaint density Risk: (complaint_count / max_complaints * 10.0) if max_complaints > 0 else 0.0
        complaint_count = complaints_per_ward.get(gen_name, 0)
        complaint_risk_score = (complaint_count / max_complaints * 10.0) if max_complaints > 0 else 0.0
        
        # Combined risk = 50% IoT + 50% Ingested 311
        combined_risk_score = round(0.5 * iot_risk_score + 0.5 * complaint_risk_score, 2)
        
        # Color coding: Green <= 4.0, Orange <= 7.0, Red > 7.0
        if combined_risk_score <= 4.0:
            risk_level = "normal"
        elif combined_risk_score <= 7.0:
            risk_level = "warning"
        else:
            risk_level = "critical"
            
        # Build features payload
        features.append({
            "ward_name": kml_name,
            "gen_ward_name": gen_name,
            "polygons": polygons,
            "complaint_count": complaint_count,
            "complaint_risk_score": round(complaint_risk_score, 2),
            "iot_status": iot_state,
            "iot_risk_score": iot_risk_score,
            "combined_risk_score": combined_risk_score,
            "risk_level": risk_level,
            "telemetry": {
                "device_id": reading.get("device_id", "DRN-N/A"),
                "nitrogen_mg_l": reading.get("nitrogen mg/L", 0.0),
                "phosphorous_mg_l": reading.get("phosphorous mg/L", 0.0),
                "state_reason": reading.get("state_reason", "Optimal Flow Rate"),
                "pipe_diameter_mm": reading.get("pipe_diameter_mm", 300),
                "installation_method": reading.get("installation_method", "Open-Cut Excavation"),
                "pipe_age_years": reading.get("pipe_age_years", 10),
                "pipe_length_m": reading.get("pipe_length_m", 100),
                "pipe_depth_m": reading.get("pipe_depth_m", 2.0),
                "connections_count": reading.get("connections_count", 15),
                "environmental_conditions": reading.get("environmental_conditions", "No Root Intrusion"),
                "groundwater_level_m": reading.get("groundwater_level_m", 10.0),
                "is_blocked": reading.get("is_blocked", "N"),
                "maintenance_required": reading.get("maintenance_required", "None")
            },
            "recent_complaints": complaints_details.get(gen_name, [])[:10]  # Limit to top 10 for payload size
        })
        
    return {
        "status": "success",
        "city": "Ahmedabad",
        "total_wards": len(features),
        "wards": features
    }


# Setup persistent cache directory that fallback-safely works on local/Render/Vercel
OSM_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "osm_cache")
try:
    os.makedirs(OSM_CACHE_DIR, exist_ok=True)
except Exception:
    # Ephemeral serverless fallback
    OSM_CACHE_DIR = "/tmp/osm_cache"
    try:
        os.makedirs(OSM_CACHE_DIR, exist_ok=True)
    except Exception:
        OSM_CACHE_DIR = None

# In-memory cache for OSM street data per ward (persists across requests while server is running)
_osm_street_cache: Dict[str, list] = {}


def _is_point_in_polygon(x: float, y: float, poly: list) -> bool:
    """Ray-casting algorithm to check if point (lat=x, lon=y) is inside a polygon of [lat, lon] points."""
    num = len(poly)
    j = num - 1
    c = False
    for i in range(num):
        if ((poly[i][1] > y) != (poly[j][1] > y)) and \
                (x < (poly[j][0] - poly[i][0]) * (y - poly[i][1]) / (poly[j][1] - poly[i][1]) + poly[i][0]):
            c = not c
        j = i
    return c


def _generate_synthetic_streets(ward_name: str, polygons: list, center_lat: float, center_lon: float, bbox: dict) -> list:
    """
    Generates a highly realistic, organic synthetic street network that is bounded
    precisely by the ward's KML polygon boundary. Connects random nodes inside the
    polygon using a distance-limited proximity network to mimic real city road expansion.
    """
    import random
    import math

    seed_val = sum(ord(c) for c in ward_name)
    r = random.Random(seed_val)

    # 1. Generate random nodes inside the actual ward boundary polygons
    nodes = []
    # Always include the center point as the seed node
    nodes.append([center_lat, center_lon])

    min_lat = bbox["min_lat"]
    max_lat = bbox["max_lat"]
    min_lng = bbox["min_lng"]
    max_lng = bbox["max_lng"]

    # Try to generate up to 25 nodes inside the polygon(s)
    attempts = 0
    max_attempts = 1500
    target_nodes = 25

    while len(nodes) < target_nodes and attempts < max_attempts:
        attempts += 1
        lat = r.uniform(min_lat, max_lat)
        lng = r.uniform(min_lng, max_lng)

        # Check if point is inside any of the polygons of the ward
        inside = False
        if not polygons:
            inside = True # No polygon boundaries, just keep it
        else:
            for poly in polygons:
                if _is_point_in_polygon(lat, lng, poly):
                    inside = True
                    break
        
        if inside:
            # Prevent nodes from being too close to each other
            too_close = False
            for existing in nodes:
                dist = math.hypot(lat - existing[0], lng - existing[1])
                if dist < 0.0012:  # roughly 120-150 meters
                    too_close = True
                    break
            if not too_close:
                nodes.append([lat, lng])

    # If we failed to generate enough nodes inside the boundary, fallback to box sampling
    if len(nodes) < 6:
        for _ in range(12):
            lat = r.uniform(center_lat - 0.006, center_lat + 0.006)
            lng = r.uniform(center_lon - 0.006, center_lon + 0.006)
            nodes.append([lat, lng])

    # 2. Build road connections (edges) between nodes
    # For each node, connect to its nearest 2-3 neighbors within a certain max distance threshold
    edges = set()
    num_nodes = len(nodes)
    max_edge_dist = 0.005  # Max road length segment (approx 500m)

    for i in range(num_nodes):
        dists = []
        for j in range(num_nodes):
            if i == j:
                continue
            dist = math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1])
            if dist < max_edge_dist:
                dists.append((dist, j))
        
        # Connect to 2-3 closest neighbors
        dists.sort()
        num_connections = r.choice([2, 3])
        for _, neighbor_idx in dists[:num_connections]:
            # Sort index tuple to prevent duplicate bi-directional edges
            edge = (min(i, neighbor_idx), max(i, neighbor_idx))
            edges.add(edge)

    # 3. Create polylines from edges with organic curvature/wobble
    indian_prefixes = [
        "Mahatma Gandhi", "Subhash", "Sardar Patel", "Nehru", "Tagore", "Shastri",
        "Vivekananda", "Premchand", "Lal Bahadur", "Vikram Sarabhai", "Bhagat Singh",
        "Rani Laxmibai", "Ambedkar", "Kalam", "Pratap", "Shivaji", "Tilak", "Gokhale",
        "Bose", "Radhakrishnan", "Market", "Temple", "Lake View", "Park", "Hospital",
        "School", "Civil Lines", "Main Bazaar", "Industrial", "Heritage", "Crescent",
        "Circular", "Green Valley", "Royal", "Cross", "Station", "Vasant", "Kavita",
        "Sanskrit", "Panchayat", "Ganga", "Yamuna", "Narmada"
    ]
    indian_suffixes = ["Road", "Street", "Marg", "Avenue", "Lane", "Path", "Chowk", "Nagar Road", "Bypass", "Link Road"]
    categories = ["Sewer Blockage", "Road Pothole", "Drainage Overflow", "Water Contamination", "Pipeline Leak"]

    streets = []
    edges_list = list(edges)
    
    for idx, (i, j) in enumerate(edges_list):
        n1 = nodes[i]
        n2 = nodes[j]

        # Generate 4-6 intermediate points to make the street curved/organic
        num_pts = r.randint(4, 6)
        polyline = []
        for step in range(num_pts):
            t = step / (num_pts - 1)
            lat = n1[0] + t * (n2[0] - n1[0])
            lon = n1[1] + t * (n2[1] - n1[1])
            
            # Wobble internal points slightly to create organic road bends
            if 0 < step < num_pts - 1:
                wobble_lat = r.uniform(-0.00015, 0.00015)
                wobble_lon = r.uniform(-0.00015, 0.00015)
                lat += wobble_lat
                lon += wobble_lon
            
            polyline.append([round(lat, 6), round(lon, 6)])

        # Generate a unique deterministic name
        name_seed = seed_val + idx * 37
        sr = random.Random(name_seed)
        p_name = sr.choice(indian_prefixes)
        s_name = sr.choice(indian_suffixes)
        name = f"{p_name} {s_name}"

        # Deterministic risk and history
        risk_base = 15 + (name_seed % 75)
        monthly_risk = [
            max(5, min(95, int(risk_base * sr.uniform(0.6, 0.85)))),
            max(5, min(95, int(risk_base * sr.uniform(0.7, 0.9)))),
            max(5, min(95, int(risk_base * sr.uniform(0.75, 0.95)))),
            max(5, min(95, int(risk_base * sr.uniform(0.85, 1.05)))),
            risk_base
        ]

        streets.append({
            "name": name,
            "polyline": polyline,
            "risk_score": risk_base,
            "risk_level": "critical" if risk_base > 70 else "warning" if risk_base > 40 else "normal",
            "complaint_count": max(0, risk_base // 12),
            "category": categories[idx % len(categories)],
            "infrastructure_age_years": 5 + (name_seed % 45),
            "monthly_risk": monthly_risk
        })

    # Sort streets by name/risk and cap to 150 for performance
    streets.sort(key=lambda s: s["name"])
    return streets[:150]


def _fetch_osm_streets(center_lat: float, center_lon: float, bbox: dict, ward_name: str) -> list:
    """
    Fetch real street geometries from OpenStreetMap Overpass API server-side.
    First checks persistent disk cache. If not found, queries multiple public Overpass API mirrors
    in sequence with retries to avoid rate limits and timeouts, caching the results to disk.
    Returns a list of street dicts, or empty list on failure.
    """
    import urllib.request
    import urllib.parse
    import json
    import random

    # 1. Try to load from persistent disk cache
    cache_key = ward_name.lower().replace(" ", "").replace("-", "").replace(".", "").replace("y", "i").replace("w", "v")
    if OSM_CACHE_DIR:
        disk_cache_file = os.path.join(OSM_CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(disk_cache_file):
            try:
                with open(disk_cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                if isinstance(cached_data, list) and len(cached_data) > 0:
                    print(f"[OSM] Disk cache hit: Loaded {len(cached_data)} streets for '{ward_name}'")
                    return cached_data
            except Exception as e:
                print(f"[OSM] Error reading disk cache for {ward_name}: {e}")

    # 2. Setup multiple Overpass API mirrors to try in sequence
    OVERPASS_SERVERS = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.nchc.org.tw/api/interpreter"
    ]

    min_lat = bbox["min_lat"]
    max_lat = bbox["max_lat"]
    min_lng = bbox["min_lng"]
    max_lng = bbox["max_lng"]

    query = (
        f'[out:json][timeout:25];'
        f'way["highway"~"primary|secondary|tertiary|residential|unclassified|living_street"]'
        f'({min_lat},{min_lng},{max_lat},{max_lng});'
        f'out geom;'
    )
    encoded_data = urllib.parse.urlencode({"data": query}).encode("utf-8")

    data = None
    last_error = ""

    for idx, server_url in enumerate(OVERPASS_SERVERS):
        try:
            print(f"[OSM] Attempting Overpass fetch for {ward_name} from {server_url}...")
            req = urllib.request.Request(
                server_url,
                data=encoded_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "UrbanFix311/1.0"
                }
            )
            # Use a slightly shorter timeout for backup servers
            timeout_sec = 18 if idx == 0 else 12
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
            print(f"[OSM] Success! Fetched from {server_url}")
            break
        except Exception as e:
            last_error = str(e)
            print(f"[OSM] Overpass error from {server_url}: {e}")

    if not data:
        print(f"[OSM] All Overpass API query servers failed for {ward_name}. Last error: {last_error}")
        return []

    try:
        elements = data.get("elements", [])
        ways = [el for el in elements if el.get("type") == "way" and el.get("geometry") and len(el["geometry"]) >= 2]

        if not ways:
            return []

        # Prioritize: named streets first, then by road class importance, cap at 150
        road_priority = {"primary": 0, "secondary": 1, "tertiary": 2, "unclassified": 3, "living_street": 4, "residential": 5}
        def sort_key(w):
            tags = w.get("tags") or {}
            has_name = 0 if tags.get("name") else 1
            hw_rank = road_priority.get(tags.get("highway", "residential"), 5)
            return (has_name, hw_rank)

        ways.sort(key=sort_key)
        ways = ways[:150]  # Cap at 150 streets for smooth map rendering

        seed_val = sum(ord(c) for c in ward_name)
        categories = ["Sewer Blockage", "Road Pothole", "Drainage Overflow", "Water Contamination", "Pipeline Leak"]

        streets = []
        for index, way in enumerate(ways):
            name = (way.get("tags") or {}).get("name", f"{ward_name} Road {index + 1}")
            polyline = [[pt["lat"], pt["lon"]] for pt in way["geometry"]]

            # Deterministic risk based on street name
            name_seed = seed_val + sum(ord(c) for c in name) + index
            sr = random.Random(name_seed)
            risk_base = 15 + (name_seed % 75)
            highway_type = (way.get("tags") or {}).get("highway", "residential")
            if highway_type in ("primary", "secondary"):
                risk_base = min(95, risk_base + 15)

            monthly_risk = [
                max(5, min(95, int(risk_base * sr.uniform(0.6, 0.85)))),
                max(5, min(95, int(risk_base * sr.uniform(0.7, 0.9)))),
                max(5, min(95, int(risk_base * sr.uniform(0.75, 0.95)))),
                max(5, min(95, int(risk_base * sr.uniform(0.85, 1.05)))),
                risk_base
            ]

            streets.append({
                "name": name,
                "polyline": polyline,
                "risk_score": risk_base,
                "risk_level": "critical" if risk_base > 70 else "warning" if risk_base > 40 else "normal",
                "complaint_count": max(0, risk_base // 12),
                "category": categories[index % len(categories)],
                "infrastructure_age_years": 5 + (name_seed % 45),
                "monthly_risk": monthly_risk
            })

        # Save to persistent disk cache
        if OSM_CACHE_DIR and streets:
            disk_cache_file = os.path.join(OSM_CACHE_DIR, f"{cache_key}.json")
            try:
                with open(disk_cache_file, "w", encoding="utf-8") as f:
                    json.dump(streets, f, ensure_ascii=False, indent=2)
                print(f"[OSM] Saved {len(streets)} streets to persistent disk cache for '{ward_name}'")
            except Exception as e:
                print(f"[OSM] Error saving disk cache for {ward_name}: {e}")

        return streets

    except Exception as e:
        print(f"[OSM] Error parsing/saving OSM streets for {ward_name}: {e}")
        return []


@router.get("/ward-streets/{ward_name}")
async def get_ward_streets(ward_name: str):
    """
    Returns street-level GIS data for a ward. Fetches real road geometries from
    OpenStreetMap server-side (cached), with organic fallback if OSM is unavailable.
    """
    import xml.etree.ElementTree as ET
    import random
    import math

    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_dir = os.path.dirname(current_dir)
    root_dir = os.path.dirname(server_dir)

    # Try server directory first (for Render cloud environments), fallback to root parent directory
    kml_path = os.path.join(server_dir, "ahmedabad_wards_map_2024.kml")
    if not os.path.exists(kml_path):
        kml_path = os.path.join(root_dir, "ahmedabad_wards_map_2024.kml")

    if not os.path.exists(kml_path):
        raise HTTPException(status_code=404, detail="KML map file not found.")

    try:
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        tree = ET.parse(kml_path)
        kml_root = tree.getroot()
        placemarks = kml_root.findall('.//kml:Placemark', ns)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse KML file: {str(e)}")

    def normalize_name(name):
        if not name:
            return ""
        return name.lower().replace(" ", "").replace("-", "").replace(".", "").replace("y", "i").replace("w", "v")

    target_norm = normalize_name(ward_name)
    polygons = []
    actual_kml_name = ward_name

    for pm in placemarks:
        kml_name = None
        simple_datas = pm.findall('.//kml:SimpleData', ns)
        for sd in simple_datas:
            if sd.attrib.get('name') == 'sourcewardname':
                kml_name = sd.text
                break
        if not kml_name:
            continue

        if normalize_name(kml_name) == target_norm:
            actual_kml_name = kml_name
            coord_nodes = pm.findall('.//kml:coordinates', ns)
            for cn in coord_nodes:
                coord_str = cn.text.strip()
                pts = []
                for pt in coord_str.split():
                    parts = pt.split(',')
                    if len(parts) >= 2:
                        try:
                            lon = float(parts[0])
                            lat = float(parts[1])
                            pts.append([lat, lon])
                        except ValueError:
                            pass
                if pts:
                    polygons.append(pts)
            break

    # Compute center and bounding box from KML polygon
    if not polygons:
        center_lat, center_lon = 23.03, 72.62
        bbox = {"min_lat": center_lat - 0.01, "max_lat": center_lat + 0.01,
                "min_lng": center_lon - 0.01, "max_lng": center_lon + 0.01}
    else:
        all_lats = [pt[0] for poly in polygons for pt in poly]
        all_lons = [pt[1] for poly in polygons for pt in poly]
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
        bbox = {
            "min_lat": min(all_lats),
            "max_lat": max(all_lats),
            "min_lng": min(all_lons),
            "max_lng": max(all_lons)
        }

    # ---- Fetch real OSM streets (server-side, cached) ----
    cache_key = normalize_name(ward_name)
    osm_streets = _osm_street_cache.get(cache_key)

    if osm_streets is None:
        # Not in cache — fetch from Overpass API server-side
        osm_streets = _fetch_osm_streets(center_lat, center_lon, bbox, ward_name)
        _osm_street_cache[cache_key] = osm_streets  # Cache even if empty (avoids re-fetching failures)
        if osm_streets:
            print(f"[OSM] Cached {len(osm_streets)} real streets for ward '{ward_name}'")
        else:
            print(f"[OSM] No streets fetched for '{ward_name}', will use fallback")
    else:
        if osm_streets:
            print(f"[OSM] Cache hit: {len(osm_streets)} streets for '{ward_name}'")

    # Use OSM streets if available, otherwise generate organic fallback
    if osm_streets:
        streets = osm_streets
    else:
        # ---- Organic fallback street network based on actual ward KML boundary ----
        streets = _generate_synthetic_streets(ward_name, polygons, center_lat, center_lon, bbox)

    # ---- Generate complaints along streets ----
    complaints = []
    seed_val = sum(ord(c) for c in ward_name)

    categories = ["Sewer & Drainage", "Roads & Potholes", "Water Supply", "Garbage & Waste"]
    severities = ["high", "medium", "low"]
    descs = {
        "Sewer & Drainage": [
            "Surcharging sewer manhole pouring blackwater onto pavement.",
            "Sewer blockage in main lateral causing backflow into properties.",
            "Strong hydrogen sulfide odor and slow drainage on main street line."
        ],
        "Roads & Potholes": [
            "Deep structural pothole posing immediate vehicle damage hazard.",
            "Asphalt cracking and depression due to sub-surface pipe erosion.",
            "Road cave-in around drainage inspection chamber."
        ],
        "Water Supply": [
            "Contaminated rusty water supply coming from residential links.",
            "Low water pressure and muddy color in distribution main.",
            "Major water pipeline leak spraying water onto main roadway."
        ],
        "Garbage & Waste": [
            "Uncollected garbage pile attracting vermin on street corner.",
            "Overflowing waste bin blocking pedestrian pathway.",
            "Illegal dumping of construction debris along street shoulder."
        ]
    }

    MAX_COMPLAINTS = 25  # Cap total complaints per ward for clean map rendering
    for i, street in enumerate(streets):
        if len(complaints) >= MAX_COMPLAINTS:
            break
        comp_count = min(street.get("complaint_count", max(0, street["risk_score"] // 12)), 3)  # Max 3 per street
        polyline = street["polyline"]
        for j in range(comp_count):
            if len(complaints) >= MAX_COMPLAINTS:
                break
            c_seed = seed_val + i * 20 + j * 15
            c_gen = random.Random(c_seed)
            pt_idx = c_gen.randint(0, len(polyline) - 1)
            pt = polyline[pt_idx]

            c_lat = pt[0] + c_gen.uniform(-0.0004, 0.0004)
            c_lon = pt[1] + c_gen.uniform(-0.0004, 0.0004)

            c_cat = categories[(i + j) % len(categories)]
            c_sev = severities[j % len(severities)]
            desc = c_gen.choice(descs.get(c_cat, ["General civic maintenance issue reported."]))

            complaints.append({
                "id": f"311-{ward_name[:3].upper()}-{i}{j}",
                "lat": round(c_lat, 6),
                "lng": round(c_lon, 6),
                "category": c_cat,
                "severity": c_sev,
                "description": desc,
                "date_filed": f"2026-05-{10 + (j % 20)}"
            })

    # ---- Generate IoT sensors scattered across the ward ----
    sensors = []
    sensor_names = ["DRN-" + ward_name[:3].upper() + "-01", "DRN-" + ward_name[:3].upper() + "-02"]
    for i, s_name in enumerate(sensor_names):
        s_seed = seed_val + i * 50
        s_gen = random.Random(s_seed)

        s_lat = center_lat + s_gen.uniform(-0.0015, 0.0015)
        s_lon = center_lon + s_gen.uniform(-0.0015, 0.0015)

        sensors.append({
            "device_id": s_name,
            "lat": round(s_lat, 6),
            "lng": round(s_lon, 6),
            "nitrogen_mg_l": round(s_gen.uniform(3.5, 9.8), 2),
            "phosphorous_mg_l": round(s_gen.uniform(0.8, 3.2), 2),
            "flow_capacity_pct": int(s_gen.uniform(40, 95)),
            "pressure_psi": int(s_gen.uniform(25, 75)),
            "ph_level": round(s_gen.uniform(5.4, 8.2), 2)
        })

    return {
        "status": "success",
        "ward_name": actual_kml_name,
        "center": [center_lat, center_lon],
        "streets": streets,
        "complaints": complaints,
        "sensors": sensors
    }



