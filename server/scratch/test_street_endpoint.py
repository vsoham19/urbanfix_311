import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routes.iot import get_ward_streets
import asyncio

result = asyncio.run(get_ward_streets("Bapunagar"))
print(f"Status: {result['status']}")
print(f"Ward: {result['ward_name']}")
print(f"Center: {result['center']}")
print(f"Total Streets: {len(result['streets'])}")
print(f"Total Complaints: {len(result['complaints'])}")
print(f"Total Sensors: {len(result['sensors'])}")

# Check first street structure
s = result['streets'][0]
print(f"\nStreet 1: {s['name']}")
print(f"  Polyline: {s['polyline']}")
print(f"  Risk Base: {s['risk_score']}")
print(f"  Monthly Risk Trend: {s['monthly_risk']}")
