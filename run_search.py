import os
import sys
from datetime import datetime, timedelta

sys.path.append(r"c:\projects\OIL SPILL")

from backend.app.services.cdse_client import CDSEClient

def main():
    client = CDSEClient()
    print(f"Has credentials: {client.has_credentials}")
    
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    
    print("\n--- CHENNAI ---")
    chennai_bbox = [80.1, 12.9, 80.4, 13.2]
    res_chennai = client.search_sentinel1(chennai_bbox, start, end)
    print(f"Result count: {res_chennai.get('count', 0)}")
    print(f"Data mode: {res_chennai.get('data_mode')}")
    if res_chennai.get('products'):
        print(f"Sample product: {res_chennai['products'][0]['title']}")
        
    print("\n--- MUMBAI ---")
    mumbai_bbox = [72.7, 18.9, 73.0, 19.2]
    res_mumbai = client.search_sentinel1(mumbai_bbox, start, end)
    print(f"Result count: {res_mumbai.get('count', 0)}")
    print(f"Data mode: {res_mumbai.get('data_mode')}")
    if res_mumbai.get('products'):
        print(f"Sample product: {res_mumbai['products'][0]['title']}")

if __name__ == '__main__':
    main()
