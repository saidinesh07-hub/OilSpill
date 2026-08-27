import os, sys, json
sys.path.insert(0, os.getcwd())
import httpx
from datetime import datetime, timedelta, timezone
from backend.app.services.cdse_client import CDSEClient

client = CDSEClient()
end = datetime.now(timezone.utc)
start = end - timedelta(days=14)

print("Searching Chennai...")
res_chennai = client.search_sentinel1([80.1, 13.0, 80.6, 13.5], start, end)
products = res_chennai.get('products', [])
if not products:
    print("No products found.")
    sys.exit(1)

prod = products[0]
prod_id = prod['id']
print(f"Product ID: {prod_id}")
print(f"Product Name: {prod['title']}")

token = client.get_access_token()
headers = {
    "Authorization": f"Bearer {token}",
    "Range": "bytes=0-1023" # Download only the first 1KB
}

# Check size of the full zip via Range request
zip_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({prod_id})/$value"
with httpx.Client(follow_redirects=True) as hclient:
    resp = hclient.get(zip_url, headers=headers)
    print(f"Zip GET Status: {resp.status_code}")
    print(f"Zip GET Headers: {resp.headers}")
    
    if resp.status_code in [200, 206]:
        content = resp.content
        print(f"Successfully downloaded {len(content)} bytes.")
        print(f"Content-Range: {resp.headers.get('Content-Range')}")
        with open('test_download_chunk.zip', 'wb') as f:
            f.write(content)
        sys.exit(0)
    else:
        print(f"Failed to download chunk. Text: {resp.text}")
        sys.exit(1)
