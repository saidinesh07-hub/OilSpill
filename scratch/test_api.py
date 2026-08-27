import requests

def test():
    res = requests.post("http://localhost:8000/api/v1/location/analyze", json={
        "name": "Kochi",
        "latitude": 9.9312,
        "longitude": 76.2673,
        "mode": "REAL"
    })
    print(res.status_code)
    try:
        data = res.json()
        print("Data:", data)
    except Exception as e:
        print("Error parsing JSON:", e)
        print("Text:", res.text)

if __name__ == "__main__":
    test()
