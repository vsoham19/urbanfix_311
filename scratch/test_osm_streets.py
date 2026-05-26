import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8000"

wards_to_test = ["Paldi", "Bapunagar", "Navrangpura", "Ghatlodia", "Bodakdev"]

for ward in wards_to_test:
    url = f"{BASE_URL}/iot/ward-streets/{ward}"
    print(f"\n{'='*60}")
    print(f"Testing: {ward}")
    print(f"{'='*60}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            
        print(f"  Status: {data.get('status')}")
        print(f"  Ward Name: {data.get('ward_name')}")
        print(f"  Center: {data.get('center')}")
        
        streets = data.get('streets', [])
        print(f"  Total Streets: {len(streets)}")
        
        if streets:
            # Show first 5 street names
            for idx, s in enumerate(streets[:5]):
                pts = len(s.get('polyline', []))
                print(f"    [{idx+1}] {s['name']} — {pts} pts, risk={s['risk_score']}, level={s['risk_level']}")
            if len(streets) > 5:
                print(f"    ... and {len(streets) - 5} more streets")
        
        complaints = data.get('complaints', [])
        sensors = data.get('sensors', [])
        print(f"  Total Complaints: {len(complaints)}")
        print(f"  Total Sensors: {len(sensors)}")
        
    except Exception as e:
        print(f"  ERROR: {e}")
    
    time.sleep(1)  # Be polite to Overpass API

print(f"\n{'='*60}")
print("All tests complete!")
