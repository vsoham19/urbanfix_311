import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

def test_run_endpoint():
    print("Testing /predictive/run endpoint...")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/predictive/run") as response:
            assert response.status == 200, "Should return 200"
            data = json.loads(response.read().decode())
            
            assert data["status"] == "success", "Should indicate success"
            assert "global_ols" in data, "Should contain global_ols stats"
            assert "ward_gwr_risk" in data, "Should contain GWR risk scores"
            assert "hotspots" in data, "Should contain DBSCAN clustered hotspots"
            
            print("\n--- OLS Regression Metrics ---")
            print(f"R2 Score: {data['global_ols']['r2_score']}")
            print(f"Intercept: {data['global_ols']['intercept']}")
            print(f"Coefficients: {data['global_ols']['coefficients']}")
            
            print(f"\nTotal Wards Analyzed: {len(data['ward_gwr_risk'])}")
            print(f"Active DBSCAN Hotspots: {data['hotspots_count']}")
            print("Success! /predictive/run is operational and mathematically valid.")
            
    except Exception as e:
        print(f"FAILED /predictive/run test: {e}")

def test_insights_endpoint():
    print("\nTesting /predictive/insights endpoint...")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/predictive/insights") as response:
            assert response.status == 200, "Should return 200"
            data = json.loads(response.read().decode())
            
            assert "source" in data, "Should indicate LLM/fallback source"
            assert "report" in data, "Should contain executive briefing report text"
            
            print(f"Briefing Source: {data['source']}")
            print("\n--- AI Planning Report Excerpt ---")
            lines = data['report'].split('\n')
            for line in lines[:15]:
                print(line)
            print("...")
            print("Success! /predictive/insights is operational.")
            
    except Exception as e:
        print(f"FAILED /predictive/insights test: {e}")

if __name__ == "__main__":
    test_run_endpoint()
    test_insights_endpoint()
