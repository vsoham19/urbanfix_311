import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))

from routes.iot import _generate_synthetic_streets

print("Imported successfully!")
# Bounding box of a dummy ward
bbox = {"min_lat": 23.0, "max_lat": 23.01, "min_lng": 72.5, "max_lng": 72.51}
polygons = [[[23.0, 72.5], [23.01, 72.5], [23.01, 72.51], [23.0, 72.51], [23.0, 72.5]]]

streets = _generate_synthetic_streets("TestWard", polygons, 23.005, 72.505, bbox)
print(f"Generated {len(streets)} synthetic streets!")
for idx, s in enumerate(streets[:5]):
    print(f"  [{idx+1}] {s['name']} — {len(s['polyline'])} pts, risk={s['risk_score']}")
