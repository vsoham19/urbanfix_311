import urllib.request
import json

def test_api():
    print("[Testing] Hitting http://localhost:8000/iot/sewer-readings ...")
    try:
        with urllib.request.urlopen("http://localhost:8000/iot/sewer-readings") as response:
            data = json.loads(response.read().decode())
            print(f"[SUCCESS] Received successful response!")
            print(f"Device Count: {data['device_count']}")
            print(f"Source: {data['source']}")
            
            # Print the first reading details to verify
            first = data['readings'][0]
            print("\nFirst Reading Details:")
            for k, v in first.items():
                print(f"  {k}: {v}")
    except Exception as e:
        print(f"❌ Failed to query API: {e}")

if __name__ == "__main__":
    test_api()
