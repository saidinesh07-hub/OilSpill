import os, sys
sys.path.insert(0, os.getcwd())
from datetime import datetime, timedelta, timezone
from backend.app.services.cdse_client import CDSEClient

client = CDSEClient()
end = datetime.now(timezone.utc)
start = end - timedelta(days=14)

print("Searching Chennai...")
res_chennai = client.search_sentinel1([80.1, 13.0, 80.6, 13.5], start, end)
print('Products found Chennai:', len(res_chennai.get('products', [])))

print("Searching Mumbai...")
res_mumbai = client.search_sentinel1([72.7, 18.8, 73.0, 19.1], start, end)
print('Products found Mumbai:', len(res_mumbai.get('products', [])))
