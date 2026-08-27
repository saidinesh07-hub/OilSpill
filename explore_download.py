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

token = client.get_access_token()
headers = {"Authorization": f"Bearer {token}"}

# Check size of the full zip
zip_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({prod_id})/$value"
resp = httpx.head(zip_url, headers=headers, follow_redirects=True)
print(f"Zip HEAD Status: {resp.status_code}")
print(f"Zip HEAD Headers: {resp.headers}")

# Check Nodes endpoint to find a TIFF
nodes_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({prod_id})/Nodes"
resp = httpx.get(nodes_url, headers=headers)
print(f"Nodes Status: {resp.status_code}")
if resp.status_code == 200:
    nodes = resp.json().get('value', [])
    for node in nodes:
        print(node.get('Name'))
        # Usually it's something like S1A_IW_GRDH_1SDV_...SAFE
        if node.get('Name').endswith('.SAFE'):
            safe_name = node.get('Name')
            meas_url = f"{nodes_url}('{safe_name}')/Nodes('measurement')/Nodes"
            meas_resp = httpx.get(meas_url, headers=headers)
            if meas_resp.status_code == 200:
                print("Measurement nodes:")
                for m in meas_resp.json().get('value', []):
                    print(f" - {m.get('Name')} (Id: {m.get('Id')})")
                    if m.get('Name').endswith('.tiff'):
                        tiff_id = m.get('Id')
                        # Download this specific TIFF
                        tiff_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({prod_id})/Nodes('{safe_name}')/Nodes('measurement')/Nodes('{m.get('Name')}')/$value"
                        tiff_head = httpx.head(tiff_url, headers=headers, follow_redirects=True)
                        print(f"TIFF HEAD Status: {tiff_head.status_code}")
                        print(f"TIFF HEAD Headers: {tiff_head.headers}")
                        
                        # Download a chunk
                        with httpx.stream("GET", tiff_url, headers=headers, follow_redirects=True) as stream:
                            print(f"TIFF Stream Status: {stream.status_code}")
                            chunk = next(stream.iter_bytes(chunk_size=1024))
                            print(f"Downloaded 1KB chunk: {len(chunk)} bytes")
                            with open('test_download.tiff', 'wb') as f:
                                f.write(chunk)
                        sys.exit(0)
