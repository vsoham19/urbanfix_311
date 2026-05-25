import random
from datetime import datetime, timezone


AHMEDABAD_SEWER_WARDS = [
    {"ward": "Chandkheda", "lat": 23.1127, "lng": 72.5941},
    {"ward": "Sabarmati", "lat": 23.0838, "lng": 72.5864},
    {"ward": "Naranpura", "lat": 23.0637, "lng": 72.5531},
    {"ward": "New Vadaj", "lat": 23.0644, "lng": 72.5660},
    {"ward": "SP Stadium", "lat": 23.0460, "lng": 72.5624},
    {"ward": "Navrangpura", "lat": 23.0365, "lng": 72.5611},
    {"ward": "Paldi", "lat": 23.0120, "lng": 72.5620},
    {"ward": "Vasna", "lat": 22.9917, "lng": 72.5434},
    {"ward": "Shahpur", "lat": 23.0348, "lng": 72.5835},
    {"ward": "Dariyapur", "lat": 23.0374, "lng": 72.5926},
    {"ward": "Jamalpur", "lat": 23.0131, "lng": 72.5847},
    {"ward": "Khadiya", "lat": 23.0234, "lng": 72.5899},
    {"ward": "Asarva", "lat": 23.0562, "lng": 72.6056},
    {"ward": "Shahibaug", "lat": 23.0572, "lng": 72.5887},
    {"ward": "Gomtipur", "lat": 23.0176, "lng": 72.6226},
    {"ward": "Odhav", "lat": 23.0225, "lng": 72.6727},
    {"ward": "Vastral", "lat": 22.9979, "lng": 72.6697},
    {"ward": "Bhaipura-Hatkeshvar", "lat": 22.9994, "lng": 72.6261},
    {"ward": "Thakkarbapa Nagar", "lat": 23.0482, "lng": 72.6406},
    {"ward": "Saraspur", "lat": 23.0325, "lng": 72.6089},
    {"ward": "Sardarnagar", "lat": 23.0755, "lng": 72.6214},
    {"ward": "Naroda", "lat": 23.0705, "lng": 72.6530},
    {"ward": "Kubernagar", "lat": 23.0834, "lng": 72.6348},
    {"ward": "Saijpurbogha", "lat": 23.0656, "lng": 72.6290},
    {"ward": "Gota", "lat": 23.1013, "lng": 72.5407},
    {"ward": "Chandlodiya", "lat": 23.0811, "lng": 72.5481},
    {"ward": "Ghatlodiya", "lat": 23.0696, "lng": 72.5324},
    {"ward": "Thaltej", "lat": 23.0497, "lng": 72.5164},
    {"ward": "Bodakdev", "lat": 23.0390, "lng": 72.5130},
    {"ward": "Baherampura", "lat": 22.9972, "lng": 72.5891},
    {"ward": "Indrapuri", "lat": 22.9908, "lng": 72.6163},
    {"ward": "Khokhra", "lat": 22.9991, "lng": 72.6129},
    {"ward": "Maninagar", "lat": 22.9986, "lng": 72.6060},
    {"ward": "Danilimda", "lat": 22.9792, "lng": 72.5904},
    {"ward": "Lambha", "lat": 22.9467, "lng": 72.5851},
    {"ward": "Isanpur", "lat": 22.9752, "lng": 72.6048},
    {"ward": "Vatva", "lat": 22.9562, "lng": 72.6359},
    {"ward": "Sarkhej", "lat": 22.9823, "lng": 72.5019},
    {"ward": "Jodhpur", "lat": 23.0158, "lng": 72.5174},
    {"ward": "Vejalpur", "lat": 23.0046, "lng": 72.5141},
    {"ward": "Maktampura", "lat": 22.9997, "lng": 72.5302},
    {"ward": "Ranip", "lat": 23.0818, "lng": 72.5703},
    {"ward": "Amraivadi", "lat": 23.0067, "lng": 72.6221},
    {"ward": "Ramol Hathijan", "lat": 22.9756, "lng": 72.6686},
    {"ward": "Nikol", "lat": 23.0577, "lng": 72.6698},
    {"ward": "Viratnagar", "lat": 23.0422, "lng": 72.6588},
    {"ward": "Bapunagar", "lat": 23.0384, "lng": 72.6308},
    {"ward": "India Colony", "lat": 23.0475, "lng": 72.6254},
]


def _sewage_state(nitrogen_mg_l: float, phosphorous_mg_l: float) -> str:
    if nitrogen_mg_l >= 35 or phosphorous_mg_l >= 7.5:
        return "critical"
    if nitrogen_mg_l >= 25 or phosphorous_mg_l >= 5.5:
        return "warning"
    return "normal"


def generate_iot_sewer_readings() -> list[dict]:
    reading_time = datetime.now(timezone.utc).isoformat()
    readings = []

    # Try to fetch static infrastructure details from the database
    from services.supabase_client import DBWrapper
    try:
        infra_records = DBWrapper.get_sewer_infrastructure()
        infra_map = {r["ward_name"]: r for r in infra_records}
    except Exception as e:
        print(f"[IoT Generator Error] Failed to fetch static sewer infrastructure: {e}")
        infra_map = {}

    for index, ward in enumerate(AHMEDABAD_SEWER_WARDS, start=1):
        nitrogen = round(random.uniform(11.0, 42.0), 2)
        phosphorous = round(random.uniform(2.0, 9.0), 2)
        state = _sewage_state(nitrogen, phosphorous)

        # Correlated values based on state
        if state == "critical":
            state_reason = "Severe Chemical Outflow & Extreme Silt Surcharging"
            is_blocked = "Y"
            maintenance_required = "Hydraulic Deterioration - Structural Re-lining & Jetting Required"
            environmental_conditions = "Heavy Tree Root Intrusion, High Water Table"
            groundwater_level = round(random.uniform(1.2, 3.5), 1)
        elif state == "warning":
            state_reason = "Elevated Chemical Levels & Flow Rate Slowdown"
            is_blocked = random.choice(["Y", "N"])
            maintenance_required = "Minor Debris Build-up - Standard Flushing Scheduled"
            environmental_conditions = "Moderate Tree Root Encroachment, Sandy Soil"
            groundwater_level = round(random.uniform(3.5, 7.5), 1)
        else:
            state_reason = "Optimal Chemical Balance & Steady Flow Telemetry"
            is_blocked = "N"
            maintenance_required = "None - Operating at High Flow Capacity"
            environmental_conditions = "Clear Sandy-Loam Soil, No Root Intrusion"
            groundwater_level = round(random.uniform(7.5, 15.0), 1)

        # Retrieve static details from database OR fall back to deterministic hash/seed if unseeded
        static_data = infra_map.get(ward["ward"])
        if static_data:
            geo_latitude = static_data["sensor_latitude"]
            geo_longitude = static_data["sensor_longitude"]
            pipe_diameter = static_data["pipe_diameter_mm"]
            installation_method = static_data["installation_method"]
            pipe_age = static_data["avg_sewer_age_years"]
            pipe_length = static_data["pipe_length_m"]
            pipe_depth = static_data["pipe_depth_m"]
            connections_count = static_data["connections_count"]
        else:
            # Safe deterministic local seed fallback if DB hasn't seeded yet
            ward_rand = random.Random(ward["ward"])
            lat_offset = ward_rand.uniform(-0.0020, 0.0020)
            lng_offset = ward_rand.uniform(-0.0020, 0.0020)
            geo_latitude = round(ward["lat"] + lat_offset, 6)
            geo_longitude = round(ward["lng"] + lng_offset, 6)
            
            pipe_diameter = ward_rand.choice([200, 300, 450, 600, 750, 900])
            installation_method = ward_rand.choice(["Trenchless (HDD)", "Open-Cut Excavation", "Microtunneling"])
            pipe_age = round(ward_rand.uniform(2.0, 60.0), 1)
            pipe_length = ward_rand.randint(50, 250)
            pipe_depth = round(ward_rand.uniform(1.5, 6.0), 1)
            connections_count = ward_rand.randint(5, 45)

        readings.append({
            "device_id": f"DRN-{index:03d}",
            "ward_name": ward["ward"],
            "geo_latitude": geo_latitude,
            "geo_longitude": geo_longitude,
            "date": reading_time,
            "nitrogen mg/L": nitrogen,
            "phosphorous mg/L": phosphorous,
            "state_of_sewage": state,
            "state_reason": state_reason,
            "pipe_diameter_mm": pipe_diameter,
            "installation_method": installation_method,
            "pipe_age_years": pipe_age,
            "pipe_length_m": pipe_length,
            "pipe_depth_m": pipe_depth,
            "connections_count": connections_count,
            "environmental_conditions": environmental_conditions,
            "groundwater_level_m": groundwater_level,
            "is_blocked": is_blocked,
            "maintenance_required": maintenance_required
        })

    return readings
