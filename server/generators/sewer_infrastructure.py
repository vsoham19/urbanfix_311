import uuid
import random
from services.supabase_client import DBWrapper
from generators.iot_sewer_data import AHMEDABAD_SEWER_WARDS

# Set random seed for deterministic mock data with clear regression correlations
random.seed(42)

def seed_sewer_infrastructure_if_empty(force=False):
    """
    Seeds the sewer_infrastructure table with realistic structural and environmental
    predictors for all 53 Ahmedabad wards if the table is currently empty.
    """
    existing = DBWrapper.get_sewer_infrastructure()
    if len(existing) > 0 and not force:
        print(f"[Seeding] sewer_infrastructure already populated with {len(existing)} records. Skipping.")
        return

    print("[Seeding] Populating sewer_infrastructure table with ward-level predictors...")
    records = []
    
    # Historic central wards that typically have older infrastructure and high commercial density
    central_wards = {
        "Khadiya", "Jamalpur", "Dariyapur", "Shahpur", "Jamalpur", "Asarva", 
        "Gomtipur", "Saraspur", "Shahibaug", "Baherampura"
    }
    
    # High green-cover/suburban wards
    green_wards = {
        "Gota", "Bodakdev", "Thaltej", "Jodhpur", "Vejalpur", "Navrangpura", "Chandkheda"
    }

    for index, ward_info in enumerate(AHMEDABAD_SEWER_WARDS):
        ward_name = ward_info["ward"]
        
        # Apply structured correlations for realistic regression findings:
        if ward_name in central_wards:
            # Central historic wards: Older sewers, high restaurant grease, low tree count
            sewer_age = round(random.uniform(32.0, 52.0), 1)
            trees = random.randint(15, 60)
            pop_density = round(random.uniform(180.0, 290.0), 1)  # Thousands per sq km
            restaurants = random.randint(45, 95)
            pipe_dia = round(random.choice([250.0, 300.0, 350.0]), 1)
            inst_method = "Open-Cut Excavation"
            pipe_len = random.randint(50, 120)
            pipe_dep = round(random.uniform(1.5, 3.0), 1)
            conn_count = random.randint(25, 45)
        elif ward_name in green_wards:
            # Green suburbs: Newer sewers, high tree counts (root intrusion!), low/medium restaurants
            sewer_age = round(random.uniform(6.0, 18.0), 1)
            trees = random.randint(140, 320)
            pop_density = round(random.uniform(40.0, 95.0), 1)
            restaurants = random.randint(12, 38)
            pipe_dia = round(random.choice([600.0, 800.0, 1000.0]), 1)
            inst_method = random.choice(["Trenchless (HDD)", "Microtunneling"])
            pipe_len = random.randint(120, 250)
            pipe_dep = round(random.uniform(3.5, 6.0), 1)
            conn_count = random.randint(5, 18)
        else:
            # standard mixed wards
            sewer_age = round(random.uniform(15.0, 32.0), 1)
            trees = random.randint(50, 150)
            pop_density = round(random.uniform(80.0, 180.0), 1)
            restaurants = random.randint(20, 60)
            pipe_dia = round(random.choice([350.0, 450.0, 500.0, 600.0]), 1)
            inst_method = random.choice(["Trenchless (HDD)", "Open-Cut Excavation"])
            pipe_len = random.randint(80, 180)
            pipe_dep = round(random.uniform(2.5, 4.5), 1)
            conn_count = random.randint(12, 30)

        # GPS sensor coordinates with static deterministic offset per ward
        coord_rand = random.Random(ward_name)
        sensor_lat = round(ward_info["lat"] + coord_rand.uniform(-0.0020, 0.0020), 6)
        sensor_lng = round(ward_info["lng"] + coord_rand.uniform(-0.0020, 0.0020), 6)

        records.append({
            "id": str(uuid.uuid4()),
            "ward_name": ward_name,
            "avg_sewer_age_years": sewer_age,
            "tree_count": trees,
            "population_density": pop_density,
            "restaurant_count": restaurants,
            "pipe_diameter_mm": pipe_dia,
            "installation_method": inst_method,
            "pipe_length_m": pipe_len,
            "pipe_depth_m": pipe_dep,
            "connections_count": conn_count,
            "sensor_latitude": sensor_lat,
            "sensor_longitude": sensor_lng
        })

    DBWrapper.insert_sewer_infrastructure(records)
    print(f"[Seeding] Successfully seeded {len(records)} Ahmedabad wards into sewer_infrastructure.")

if __name__ == "__main__":
    seed_sewer_infrastructure_if_empty(force=True)
