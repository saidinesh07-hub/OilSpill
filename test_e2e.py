import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_test(name, lat, lon):
    print(f"\n--- TESTING LOCATION: {name} ({lat}, {lon}) ---")
    print("1. TRIGGERING /location/analyze (REAL MODE)")
    start = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/location/analyze", json={
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "mode": "REAL"
        }, timeout=300)
    except requests.exceptions.Timeout:
        print("ERROR: Timeout during CDSE download/processing")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

    dur = time.time() - start
    print(f"Response ({dur:.1f}s): {resp.status_code}")
    if resp.status_code != 200:
        print(resp.text)
        return False
        
    data = resp.json().get("data", {})
    incident_id = data.get("incident_id")
    print(f"Incident created: ID {incident_id}")

    print("\n2. TRIGGERING /location/{id}/intelligence")
    intel_resp = requests.get(f"{BASE_URL}/location/{incident_id}/intelligence")
    print(f"Response: {intel_resp.status_code}")
    if intel_resp.status_code != 200:
        print(intel_resp.text)
        return False

    intel_data = intel_resp.json().get("data", {})
    vessels = intel_data.get("vessels", [])
    infra = intel_data.get("infrastructure", [])
    sources = intel_data.get("possible_sources", [])
    
    print(f"Found {len(vessels)} vessels, {len(infra)} infrastructure items.")
    print("Top Source Attribution:")
    for s in sources[:3]:
        print(f" - {s['category']} | {s['object_name']} | {s['confidence']} | {s['evidence']}")
        
    print("\n3. TRIGGERING /scenes")
    scenes_resp = requests.get(f"{BASE_URL}/scenes")
    scenes = scenes_resp.json().get("data", [])
    if scenes:
         scene = scenes[-1]
         print(f"Latest Scene: {scene['scene_name']} | {scene['source']} | Synthetic? {scene['is_synthetic']}")
         print(f"Acquisition: {scene['acquisition_time']}")
    else:
         print("No scenes returned.")

    print("\nTEST PASSED")
    return True

if __name__ == "__main__":
    print("Waiting for server to start...")
    success = True
    
    # Check health
    try:
         requests.get(f"{BASE_URL}/health")
    except:
         print("Server is not running. Please start the backend.")
         sys.exit(1)
         
    if not run_test("Chennai", 13.0827, 80.2707): success = False
    if not run_test("Mumbai", 18.922, 72.8347): success = False
    if not run_test("Visakhapatnam", 17.6868, 83.2185): success = False
    
    sys.exit(0 if success else 1)
