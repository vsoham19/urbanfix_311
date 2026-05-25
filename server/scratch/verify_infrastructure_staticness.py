import sys
import os

# Append the server directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables to run without Supabase first
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""

from generators.iot_sewer_data import generate_iot_sewer_readings

def test_static_physical_characteristics():
    print("[Testing] Generating first set of readings...")
    readings1 = generate_iot_sewer_readings()
    
    print("[Testing] Generating second set of readings...")
    readings2 = generate_iot_sewer_readings()
    
    print("[Testing] Asserting equality of physical characteristics across both iterations...")
    
    assert len(readings1) == len(readings2), "Readings lengths differ!"
    
    mismatches = 0
    checked_fields = [
        "geo_latitude", "geo_longitude", "pipe_diameter_mm", 
        "installation_method", "pipe_age_years", "pipe_length_m", 
        "pipe_depth_m", "connections_count"
    ]
    
    for r1, r2 in zip(readings1, readings2):
        assert r1["ward_name"] == r2["ward_name"], "Ward names differ!"
        
        # Verify static physical/coord fields are identical
        for field in checked_fields:
            if r1[field] != r2[field]:
                print(f"❌ Mismatch in {r1['ward_name']} for {field}: {r1[field]} vs {r2[field]}")
                mismatches += 1
                
        # Verify dynamic fields differ or are successfully generated
        # (dynamic fields like nitrogen/phosphorous can sometimes be equal by chance, 
        # but shouldn't fail the staticness test)
        
    if mismatches == 0:
        print("[SUCCESS] All physical characteristics and coordinates are 100% static!")
    else:
        print(f"[FAIL] Found {mismatches} dynamic mismatches in physical attributes.")
        sys.exit(1)

if __name__ == "__main__":
    test_static_physical_characteristics()
