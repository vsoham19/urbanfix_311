import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routes.iot import get_wards_boundaries
import asyncio

result = asyncio.run(get_wards_boundaries())
print(f"Status: {result['status']}, Total Wards: {result['total_wards']}")

# Print a summary of risk levels
normal = sum(1 for w in result['wards'] if w['risk_level'] == 'normal')
warning = sum(1 for w in result['wards'] if w['risk_level'] == 'warning')
critical = sum(1 for w in result['wards'] if w['risk_level'] == 'critical')
print(f"Risk Distribution: Normal={normal}, Warning={warning}, Critical={critical}")

# Print first 3 wards details
for w in result['wards'][:3]:
    print(f"  Ward: {w['ward_name']} | Combined Risk: {w['combined_risk_score']} | Level: {w['risk_level']} | Polygons: {len(w['polygons'])} | Complaints: {w['complaint_count']}")
