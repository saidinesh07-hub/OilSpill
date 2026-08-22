"""
Copernicus Data Space Ecosystem (CDSE) Client

Search and download interface for Sentinel-1 SAR products.
Requires CDSE_CLIENT_ID and CDSE_CLIENT_SECRET in environment for authenticated download.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger


class CDSEClient:
    """
    REST client for CDSE catalogue search and product download.
    """

    SEARCH_PATH = "/collections/Sentinel1/search.json"
    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        catalogue_url: Optional[str] = None,
    ):
        self.client_id = client_id or settings.CDSE_CLIENT_ID
        self.client_secret = client_secret or settings.CDSE_CLIENT_SECRET
        self.catalogue_url = (catalogue_url or settings.CDSE_API_URL).rstrip("/")
        self.has_credentials = bool(self.client_id and self.client_secret)

    def search_sentinel1(
        self,
        bbox: List[float],
        start: datetime,
        end: datetime,
        product_type: str = "GRD",
        max_records: int = 20,
    ) -> Dict[str, Any]:
        """
        Search Sentinel-1 catalogue by bounding box and acquisition window.

        bbox: [min_lon, min_lat, max_lon, max_lat]
        """
        if not self.has_credentials:
            return {
                "data_mode": "UNAVAILABLE",
                "message": "CDSE credentials not configured. Set CDSE_CLIENT_ID and CDSE_CLIENT_SECRET.",
                "products": [],
            }

        params = {
            "box": f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}",
            "startDate": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "completionDate": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "productType": product_type,
            "maxRecords": max_records,
        }

        url = f"{self.catalogue_url}{self.SEARCH_PATH}"
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.error(f"CDSE search failed: {exc}")
            return {"data_mode": "ERROR", "message": str(exc), "products": []}

        features = payload.get("features", [])
        products = []
        for feat in features:
            props = feat.get("properties", {})
            products.append({
                "id": props.get("id") or feat.get("id"),
                "title": props.get("title"),
                "acquisition_time": props.get("startDate"),
                "product_type": props.get("productType"),
                "polarisation": props.get("polarisation"),
                "footprint": feat.get("geometry"),
            })

        return {
            "data_mode": "LIVE_API",
            "count": len(products),
            "products": products,
        }

    def get_access_token(self) -> Optional[str]:
        """Obtain OAuth2 access token for CDSE download API."""
        if not self.has_credentials:
            return None

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.TOKEN_URL, data=data)
                response.raise_for_status()
                return response.json().get("access_token")
        except Exception as exc:
            logger.error(f"CDSE token request failed: {exc}")
            return None

    def download_product(self, product_id: str, output_dir: str) -> Dict[str, Any]:
        """
        Download a Sentinel-1 SAFE product by ID to output_dir.

        Returns status dict with local storage_path when successful.
        """
        if not self.has_credentials:
            return {
                "status": "UNAVAILABLE",
                "message": "CDSE credentials required for product download.",
            }

        token = self.get_access_token()
        if not token:
            return {"status": "ERROR", "message": "Failed to obtain CDSE access token."}

        # CDSE OData download endpoint (product-specific URL resolved via catalogue)
        download_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
        headers = {"Authorization": f"Bearer {token}"}

        import os
        os.makedirs(output_dir, exist_ok=True)
        local_path = os.path.join(output_dir, f"{product_id}.zip")

        try:
            with httpx.Client(timeout=600.0, follow_redirects=True) as client:
                with client.stream("GET", download_url, headers=headers) as response:
                    response.raise_for_status()
                    with open(local_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
            return {
                "status": "COMPLETED",
                "storage_path": local_path,
                "product_id": product_id,
                "data_mode": "REAL_SATELLITE_DATA",
            }
        except Exception as exc:
            logger.error(f"CDSE download failed for {product_id}: {exc}")
            return {"status": "ERROR", "message": str(exc)}
