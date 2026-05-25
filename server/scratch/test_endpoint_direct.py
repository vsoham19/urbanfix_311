import asyncio
import sys
import os

sys.path.append(r"c:\Users\vsoha\Desktop\Work\urbanfix\311\server")

from routes.iot import get_wards_boundaries

async def run_test():
    try:
        print("Executing get_wards_boundaries() directly...")
        result = await get_wards_boundaries()
        print("Success!")
        print("Keys returned:", result.keys())
        print("Total Wards:", result.get("total_wards"))
        
        wards = result.get("wards", [])
        if wards:
            sample = wards[0]
            print("\nSample Ward details:")
            print(f"Name: {sample['ward_name']} (Gen: {sample['gen_ward_name']})")
            print(f"Complaint Count: {sample['complaint_count']} (Score: {sample['complaint_risk_score']})")
            print(f"IoT Status: {sample['iot_status']} (Score: {sample['iot_risk_score']})")
            print(f"Combined Risk: {sample['combined_risk_score']} (Level: {sample['risk_level']})")
            print(f"Coordinates Sets: {len(sample['polygons'])}, Points in first set: {len(sample['polygons'][0])}")
            print(f"Telemetry fields: {list(sample['telemetry'].keys())}")
            print(f"Recent complaints count: {len(sample['recent_complaints'])}")
            
            # Count levels
            levels = [w["risk_level"] for w in wards]
            from collections import Counter
            print("\nRisk Level Distribution:", Counter(levels))
    except Exception as e:
        print("Test failed with error:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
