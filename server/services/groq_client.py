import random as py_random
from datetime import datetime
import os
import json
import re
import difflib
from groq import Groq
from dotenv import load_dotenv

# Robustly load environment variables from server/.env and root .env using absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
# server/.env is the parent of services (current_dir is server/services, so its parent is server)
server_env = os.path.join(os.path.dirname(current_dir), '.env')
# root .env is the parent of server
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class GroqClient:
    def __init__(self):
        self.client = None
        if GROQ_API_KEY and "your_groq_api_key" not in GROQ_API_KEY:
            try:
                self.client = Groq(api_key=GROQ_API_KEY)
                print("[AI] Groq client initialized successfully.")
            except Exception as e:
                print(f"[AI] Error initializing Groq client: {e}. Running in local mock mode.")

    def clean_record(self, raw_record: dict) -> dict:
        """
        Cleans a single 311 record. Returns a structured JSON dict with the keys:
        - complaint_id: str
        - ward_name: str
        - complaint_category: str
        - severity: str
        - description: str
        - language: str
        - lat: float or null
        - lng: float or null
        - phone: str
        - postal_code: str
        - date_filed: str (ISO 8601 format)
        - confidence_score: float (0.0 to 1.0)
        - flags: list of strings (for issues detected)
        - reason_code: str (if quarantined)
        """
        if self.client:
            try:
                return self._call_groq_api(raw_record)
            except Exception as e:
                print(f"[AI] Groq API call failed: {e}. Falling back to local rules.")
                return self._local_heuristic_clean(raw_record)
        else:
            return self._local_heuristic_clean(raw_record)

    def _call_groq_api(self, raw_record: dict) -> dict:
        prompt = f"""
        You are an AI city-data cleaning agent for the UrbanFix 311 system.
        Your task is to analyze and clean the following raw complaint data:
        
        {json.dumps(raw_record, indent=2)}

        Perform the following steps:
        1. Resolve Ward/Area: Standardize to one of these valid Ahmedabad Wards:
           ["Navrangpura", "Vastrapur", "Satellite", "Naranpura", "Girdhar Nagar", "Paldi", "Bodakdev", "Jodhpur", "Bopal", "Thaltej", "Ranip", "Chandkheda", "Sabarmati", "Nikol", "Maninagar", "Kalupur", "Jamalpur", "Shahpur", "Dariapur", "Astodia"].
           If the ward cannot be resolved, flag it and output null.
        2. Classify Category: Choose exactly one of ["Sewer & Drainage", "Garbage & Waste", "Streetlights", "Roads & Potholes", "Water Supply", "Other"].
        3. Severity: Classify as "Low", "Medium", or "High" based on hazard level (e.g. sewage leakage or open wire is High, streetlight out is Medium/Low).
        4. Detect Language: Detect the primary language ("English", "Gujarati", "Hinglish").
        5. Normalize Phone: Standardize to 10 digit Indian format (e.g. "9876543210"). If invalid/missing, flag it.
        6. Normalize Postal Code: Normalize pincode to 6 digits (e.g., 380015). Ahmedabad pincodes start with 380.
        7. Normalize Date: Convert date string to ISO 8601 (YYYY-MM-DDTHH:MM:SS).
        8. Calculate Confidence Score: Assign a score from 0.0 to 1.0 based on readability, missing critical fields (like phone, description, or ward), or invalid formats.
        9. Identify Flags: Add reasons to the "flags" array (e.g., "invalid_phone", "missing_ward", " गुजराती_ભાષા" if non-English, etc.).

        Output strictly a JSON object with these exact keys:
        {{
            "complaint_id": "string",
            "ward_name": "string or null",
            "complaint_category": "string",
            "severity": "string",
            "description": "string",
            "language": "string",
            "phone": "string or null",
            "postal_code": "string or null",
            "date_filed": "string or null",
            "confidence_score": float,
            "flags": ["string"],
            "reason_code": "string or null"
        }}
        """
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a precise data normalizer. You only output valid raw JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        
        # Add lat/lng via coordinates mapper if missing
        if not result.get("lat") or not result.get("lng"):
            coords = self._geocode_ward(result.get("ward_name"))
            result["lat"] = coords[0]
            result["lng"] = coords[1]
            
        return result

    def _local_heuristic_clean(self, raw_record: dict) -> dict:
        """
        Rule-based clean fallback when Groq isn't available.
        Ensures high reliability and 100% correct JSON formats.
        """
        desc = raw_record.get("Complaint Details", "")
        raw_ward = raw_record.get("Ward/Area", "")
        raw_phone = raw_record.get("Reporter Phone", "")
        raw_pincode = raw_record.get("Pincode", "")
        raw_date = raw_record.get("Date", "")
        complaint_id = raw_record.get("Complaint ID", "")

        flags = []
        confidence_score = 1.0

        # 1. Resolve Ward
        ward_name = None
        matched_ward = False
        from generators.mock_data import AHMEDABAD_WARDS
        
        if raw_ward:
            closest = difflib.get_close_matches(raw_ward, AHMEDABAD_WARDS, n=1, cutoff=0.5)
            if closest:
                ward_name = closest[0]
                matched_ward = True
                if ward_name.lower() != raw_ward.lower():
                    flags.append("ward_name_corrected")
                    confidence_score -= 0.1
            else:
                flags.append("unknown_ward")
                confidence_score -= 0.35
        else:
            flags.append("missing_ward")
            confidence_score -= 0.45

        # 2. Categorize and Severity
        complaint_category = "Other"
        severity = "Medium"
        
        sewer_keywords = ["sewer", "drainage", "overflow", "gutter", "blockage", "ગટર", "ગંદુ પાણી", "choke up", "leakage"]
        garbage_keywords = ["garbage", "waste", "trash", "kachra", "કચરો", "કચરાપેટી", "dump", "pile"]
        light_keywords = ["streetlight", "street light", "dark", "light", "અંધારું", "પોલ", "pole", "switch board"]
        road_keywords = ["pothole", "road", "pavement", "khada", "ખાડા", "repair", "asphalt", "damage"]
        water_keywords = ["water supply", "drinking water", "water pipe", "leakage", "pressure", "પીવાનું પાણી"]

        desc_lower = desc.lower()
        if any(kw in desc_lower for kw in sewer_keywords):
            complaint_category = "Sewer & Drainage"
            severity = "High"
        elif any(kw in desc_lower for kw in garbage_keywords):
            complaint_category = "Garbage & Waste"
            severity = "Medium"
        elif any(kw in desc_lower for kw in light_keywords):
            complaint_category = "Streetlights"
            severity = "Low"
        elif any(kw in desc_lower for kw in road_keywords):
            complaint_category = "Roads & Potholes"
            severity = "Medium"
        elif any(kw in desc_lower for kw in water_keywords):
            complaint_category = "Water Supply"
            severity = "High"
            
        if not desc:
            flags.append("missing_details")
            confidence_score -= 0.5

        # 3. Detect Language
        # Simple heuristic
        if any(ord(char) > 2000 for char in desc):  # Simple Gujarati unicode check
            language = "Gujarati"
        elif any(kw in desc_lower for kw in ["hogayi", "hogaya", "gandi", "clean karvao", "kharab", "bohot", "baki"]):
            language = "Hinglish"
        else:
            language = "English"

        # 4. Normalize Phone
        phone = None
        if raw_phone:
            # strip all non-digits
            digits = re.sub(r"\D", "", raw_phone)
            if digits.startswith("91") and len(digits) == 12:
                phone = digits[2:]
            elif digits.startswith("0") and len(digits) == 11:
                phone = digits[1:]
            elif len(digits) == 10:
                phone = digits
            else:
                phone = digits
                flags.append("invalid_phone_format")
                confidence_score -= 0.15
        else:
            flags.append("missing_phone")
            confidence_score -= 0.2

        # 5. Normalize Pincode
        postal_code = None
        if raw_pincode:
            digits = re.sub(r"\D", "", raw_pincode)
            if len(digits) == 6 and digits.startswith("380"):
                postal_code = digits
            else:
                postal_code = digits[:6] if digits else None
                flags.append("invalid_pincode")
                confidence_score -= 0.1
        else:
            flags.append("missing_pincode")
            confidence_score -= 0.15

        # 6. Normalize Date
        date_filed = None
        if raw_date and raw_date != "N/A":
            try:
                # Try standard parsing
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y %I:%M %p", "%b %d, %Y", "%Y/%m/%d"):
                    try:
                        parsed = datetime.strptime(raw_date, fmt)
                        date_filed = parsed.isoformat()
                        break
                    except ValueError:
                        continue
                if not date_filed:
                    date_filed = datetime.now().isoformat()
                    flags.append("date_parsed_fallback")
                    confidence_score -= 0.05
            except:
                date_filed = datetime.now().isoformat()
                flags.append("invalid_date")
                confidence_score -= 0.15
        else:
            date_filed = datetime.now().isoformat()
            flags.append("missing_date")
            confidence_score -= 0.2

        # Lat/lng resolution
        coords = self._geocode_ward(ward_name)
        lat = coords[0]
        lng = coords[1]
        
        # Override with raw if present
        raw_lat = raw_record.get("Latitude")
        raw_lng = raw_record.get("Longitude")
        if raw_lat and raw_lng:
            try:
                raw_lat_f = float(raw_lat)
                raw_lng_f = float(raw_lng)
                if abs(raw_lat_f) > 0.1 and abs(raw_lng_f) > 0.1:
                    lat = raw_lat_f
                    lng = raw_lng_f
                else:
                    flags.append("coordinates_zeroed")
                    confidence_score -= 0.1
            except ValueError:
                flags.append("invalid_coordinates")
                confidence_score -= 0.1
        else:
            flags.append("missing_coordinates_geocoded")
            # geocoding doesn't heavily penalize confidence, but does subtract a bit
            confidence_score -= 0.05

        confidence_score = max(0.1, round(confidence_score, 2))

        # Quarantine reason code
        reason_code = None
        if confidence_score < 0.50:
            if "missing_details" in flags:
                reason_code = "ERR_NO_CONTENT"
            elif "missing_ward" in flags or "unknown_ward" in flags:
                reason_code = "ERR_UNRESOLVED_GEOGRAPHY"
            else:
                reason_code = "ERR_LOW_CONFIDENCE"

        return {
            "complaint_id": complaint_id or f"311-{py_random.randint(100000, 999999)}",
            "ward_name": ward_name,
            "complaint_category": complaint_category,   
            "severity": severity,
            "description": desc,
            "language": language,
            "lat": lat,
            "lng": lng,
            "phone": phone,
            "postal_code": postal_code,
            "date_filed": date_filed,
            "confidence_score": confidence_score,
            "flags": flags,
            "reason_code": reason_code
        }

    def _geocode_ward(self, ward_name: str) -> tuple:
        """
        Returns (latitude, longitude) center of wards in Ahmedabad.
        """
        # Ahmedabad general: 23.0225, 72.5714
        ward_coords = {
            "Navrangpura": (23.0364, 72.5611),
            "Vastrapur": (23.0350, 72.5293),
            "Satellite": (23.0305, 72.5178),
            "Naranpura": (23.0568, 72.5478),
            "Girdhar Nagar": (23.0494, 72.5939),
            "Paldi": (23.0134, 72.5623),
            "Bodakdev": (23.0373, 72.5119),
            "Jodhpur": (23.0186, 72.5284),
            "Bopal": (23.0319, 72.4646),
            "Thaltej": (23.0497, 72.5117),
            "Ranip": (23.0768, 72.5604),
            "Chandkheda": (23.1065, 72.5768),
            "Sabarmati": (23.0827, 72.5855),
            "Nikol": (23.0450, 72.6710),
            "Maninagar": (22.9976, 72.6102),
            "Kalupur": (23.0300, 72.5975),
            "Jamalpur": (23.0130, 72.5855),
            "Shahpur": (23.0390, 72.5780),
            "Dariapur": (23.0345, 72.5890),
            "Astodia": (23.0220, 72.5925)
        }

        if ward_name in ward_coords:
            base = ward_coords[ward_name]
            # Add slight jitter for visualization
            return (base[0] + py_random.uniform(-0.003, 0.003), base[1] + py_random.uniform(-0.003, 0.003))
        return (23.0225 + py_random.uniform(-0.04, 0.04), 72.5714 + py_random.uniform(-0.04, 0.04))
