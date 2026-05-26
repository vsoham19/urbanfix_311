import urllib.request
import json

def test_endpoint(url):
    print(f"Testing {url}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')
            print(f"Response status: {status}")
            data = json.loads(body)
            print(f"Status in JSON: {data.get('status')}")
            print(f"Keys in JSON: {list(data.keys())}")
            if 'ward_name' in data:
                print(f"Ward Name: {data['ward_name']}")
            if 'center' in data:
                print(f"Center coordinates: {data['center']}")
            if 'streets' in data:
                print(f"Number of streets returned: {len(data['streets'])}")
            if 'complaints' in data:
                print(f"Number of complaints returned: {len(data['complaints'])}")
    except Exception as e:
        print(f"Error occurred: {e}")

test_endpoint("https://urbanfix-311.onrender.com/")
test_endpoint("https://urbanfix-311.onrender.com/iot/ward-streets/Bapunagar")
