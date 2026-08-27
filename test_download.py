import os, sys, shutil
sys.path.insert(0, os.getcwd())
import httpx
from datetime import datetime, timedelta, timezone
from backend.app.services.cdse_client import CDSEClient

client = CDSEClient()
end = datetime.now(timezone.utc)
start = end - timedelta(days=14)
temp_dir = "./temp_downloads"
os.makedirs(temp_dir, exist_ok=True)

for loc_name, bbox in [("Chennai", [80.1, 13.0, 80.6, 13.5]), ("Mumbai", [72.7, 18.8, 73.0, 19.1])]:
    print(f"\n--- Testing {loc_name} ---")
    res = client.search_sentinel1(bbox, start, end)
    products = res.get('products', [])
    if not products:
        print(f"No products found for {loc_name}")
        continue
    prod = products[0]
    prod_id = prod['id']
    print(f"Product ID: {prod_id}")
    print(f"Product Name: {prod['title']}")
    
    token = client.get_download_token()
    if not token:
        print("Failed to get download token")
        sys.exit(1)
        
    download_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({prod_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}
    
    local_path = os.path.join(temp_dir, f"{prod_id}.zip")
    
    print(f"Downloading from {download_url}")
    try:
        with httpx.Client(timeout=600.0, follow_redirects=True) as hclient:
            with hclient.stream("GET", download_url, headers=headers) as response:
                print(f"HTTP Status: {response.status_code}")
                if response.status_code == 200:
                    bytes_downloaded = 0
                    with open(local_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            if bytes_downloaded > 1024 * 1024 * 5: # download only 5MB for test
                                print("Downloaded 5MB, breaking early for test.")
                                break
                    
                    size = os.path.getsize(local_path)
                    print(f"Downloaded file size: {size} bytes")
                else:
                    print(f"Download failed with status: {response.status_code}")
                    print(response.read().decode())
    except Exception as e:
        print(f"Exception during download: {e}")
