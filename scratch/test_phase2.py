import requests

def test_location(name):
    res = requests.post("http://localhost:8000/api/v1/location/analyze", json={
        "name": name,
        "latitude": 22.3995,  # approximate lat for Vadinar, will be replaced if we geocode first, but wait, the frontend geocodes first.
        "longitude": 69.6705,
        "mode": "REAL"
    })
    print(f"--- Analysis for {name} ---")
    data = res.json()
    if 'data' in data:
        loc = data['data']['location']
        sat = data['data']['satellite']
        print("Location:", loc['name'], loc['latitude'], loc['longitude'], "bbox:", loc.get('bbox'))
        print("Satellite:", sat['status'], sat['message'])
    else:
        print("Failed:", data)

def geocode_and_analyze(name):
    res = requests.get(f"http://localhost:8000/api/v1/location/geocode?q={name}")
    g_data = res.json().get('data', {})
    lat = g_data.get('latitude')
    lon = g_data.get('longitude')
    print(f"Geocoded {name} -> {lat}, {lon}")
    
    if lat is not None:
        analyze_res = requests.post("http://localhost:8000/api/v1/location/analyze", json={
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "mode": "REAL"
        })
        a_data = analyze_res.json().get('data', {})
        loc = a_data.get('location', {})
        sat = a_data.get('satellite', {})
        print(f"Analysis for {name}:")
        print(f"  Location: {loc.get('name')} | BBox: {loc.get('bbox')}")
        print(f"  Satellite Status: {sat.get('status')} | Message: {sat.get('message')}")
        print(f"  Timestamp: {a_data.get('timestamp', 'N/A')}")
        print()

if __name__ == "__main__":
    geocode_and_analyze("Vadinar")
    geocode_and_analyze("Visakhapatnam, India")
