import requests

def test():
    try:
        res = requests.get("http://localhost:8000/api/v1/health")
        print(res.status_code)
        data = res.json()
        print("Data:", data)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
