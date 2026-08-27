import httpx
from datetime import datetime, timedelta, timezone

def test_search(lat, lon, mode, name):
    url = "http://127.0.0.1:8000/api/v1/satellite/search"
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=14)
    
    payload = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "mode": mode
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=60.0)
        data = response.json()
        print(f"[{name} - {mode}] Success: {data.get('success', True)}")
        print(f"Results: {data.get('data')}")
        print("-" * 50)
    except Exception as e:
        print(f"[{name} - {mode}] Failed: {e}")

if __name__ == "__main__":
    print("Testing Chennai (DEMO)")
    test_search(13.25, 80.35, "DEMO", "Chennai")
    
    print("Testing Chennai (REAL)")
    test_search(13.25, 80.35, "REAL", "Chennai")
    
    print("Testing Mumbai (REAL)")
    test_search(18.92, 72.83, "REAL", "Mumbai")
