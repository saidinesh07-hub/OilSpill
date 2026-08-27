import os, sys, shutil
sys.path.insert(0, os.getcwd())
from datetime import datetime, timedelta, timezone
from backend.app.services.cdse_client import CDSEClient

client = CDSEClient()
end = datetime.now(timezone.utc)
start = end - timedelta(days=14)
temp_dir = "./temp_downloads"
os.makedirs(temp_dir, exist_ok=True)

for loc_name, bbox in [("Chennai", [80.1, 13.0, 80.6, 13.5]), ("Mumbai", [72.7, 18.8, 73.0, 19.1])]:
    print(f"--- Testing {loc_name} ---")
    res = client.search_sentinel1(bbox, start, end)
    products = res.get('products', [])
    if not products:
        print(f"No products found for {loc_name}")
        continue
    prod = products[0]
    prod_id = prod['id']
    print(f"Product ID: {prod_id}")
    print(f"Product Name: {prod['title']}")
    
    # Try downloading
    dl_res = client.download_product(prod_id, temp_dir)
    print(f"Download Result: {dl_res}")
    
    if dl_res.get('status') == 'COMPLETED':
        path = dl_res['storage_path']
        size = os.path.getsize(path)
        print(f"Downloaded file size: {size} bytes")
    
    # Do only the first product for each location
    
