"""
Copernicus Data Space Ecosystem (CDSE) Client

Search and download interface for Sentinel-1 SAR products.
Requires CDSE_CLIENT_ID and CDSE_CLIENT_SECRET in environment for authenticated download.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import json
import os
import re
import zipfile
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger


class CDSEClient:
    """
    REST client for CDSE catalogue search and product download.
    """

    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    DOWNLOAD_PUBLIC_CLIENT_ID = "cdse-public"
    DOWNLOAD_URL_TEMPLATE = (
        "https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    )
    _DOWNLOAD_REDIRECT_HOSTS = frozenset(
        {
            "download.dataspace.copernicus.eu",
            "zipper.dataspace.copernicus.eu",
            "catalogue.dataspace.copernicus.eu",
        }
    )
    _SENSITIVE_JSON_KEYS = frozenset(
        {
            "access_token",
            "refresh_token",
            "id_token",
            "password",
            "username",
            "client_secret",
        }
    )

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.client_id = client_id or settings.CDSE_CLIENT_ID
        self.client_secret = client_secret or settings.CDSE_CLIENT_SECRET
        self.has_credentials = bool(self.client_id and self.client_secret)
        self.has_credentials = self.has_credentials

    def search_sentinel1(
        self,
        bbox: List[float],
        start: datetime,
        end: datetime,
        product_type: str = "GRD",
        max_records: int = 20,
    ) -> Dict[str, Any]:
        """
        Search Sentinel-1 catalogue by bounding box and acquisition window using OData.

        bbox: [min_lon, min_lat, max_lon, max_lat]
        """
        if not self.has_credentials:
            return {
                "data_mode": "UNAVAILABLE",
                "message": "CDSE credentials not configured. Set CDSE_CLIENT_ID and CDSE_CLIENT_SECRET.",
                "products": [],
            }

        token = self.get_access_token()
        if not token:
            return {
                "data_mode": "UNAVAILABLE",
                "message": "Failed to obtain CDSE access token.",
                "products": [],
            }

        # OData dynamically filters
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # OData Polygon requires format: POLYGON((lon lat, lon lat, ...))
        # Note the double parenthesis for POLYGON
        polygon = f"POLYGON(({min_lon} {min_lat}, {min_lon} {max_lat}, {max_lon} {max_lat}, {max_lon} {min_lat}, {min_lon} {min_lat}))"
        
        start_str = start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Collection eq SENTINEL-1 and spatial intersection
        filter_str = (
            "Collection/Name eq 'SENTINEL-1' and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{polygon}') and "
            f"ContentDate/Start ge {start_str} and ContentDate/Start le {end_str}"
        )

        if product_type == "GRD":
            # Prefer IW_GRDH_1S where possible for Sentinel-1 GRD
            filter_str += " and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'IW_GRDH_1S')"
        url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        params = {
            "$filter": filter_str,
            "$top": max_records,
            "$expand": "Attributes",
            "$orderby": "ContentDate/Start desc"
        }
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"CDSE search HTTP error: {exc}")
            return {"data_mode": "UNAVAILABLE", "message": f"HTTP error {exc.response.status_code}", "products": []}
        except Exception as exc:
            logger.error(f"CDSE search failed: {exc}")
            return {"data_mode": "UNAVAILABLE", "message": str(exc), "products": []}

        value = data.get("value", [])
        products = []
        for prod in value:
            polarisation = None
            for attr in prod.get("Attributes", []):
                if attr.get("Name") == "polarisationChannels":
                    polarisation = attr.get("Value")
                    break

            products.append({
                "id": prod.get("Id"),
                "title": prod.get("Name"),
                "acquisition_time": prod.get("ContentDate", {}).get("Start"),
                "product_type": "GRD",
                "polarisation": polarisation,
                "footprint": prod.get("GeoFootprint"),
                "s3_path": prod.get("S3Path"),
                "quicklook_url": f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({prod.get('Id')})/Nodes({prod.get('Name')}.SAFE)/Nodes(preview)/Nodes(quick-look.png)/$value"
            })

        return {
            "data_mode": "LIVE_API",
            "count": len(products),
            "products": products,
        }

    def get_access_token(self) -> Optional[str]:
        """Obtain OAuth2 access token for CDSE catalogue API using client credentials."""
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

    @staticmethod
    def sanitize_error_body(text: Optional[str], max_len: int = 500) -> str:
        """Return a truncated error body with tokens and secrets redacted."""
        if not text:
            return ""
        try:
            payload = json.loads(text)

            def _redact(value: Any) -> Any:
                if isinstance(value, dict):
                    redacted = {}
                    for key, inner in value.items():
                        if str(key).lower() in CDSEClient._SENSITIVE_JSON_KEYS:
                            redacted[key] = "[REDACTED]"
                        else:
                            redacted[key] = _redact(inner)
                    return redacted
                if isinstance(value, list):
                    return [_redact(item) for item in value]
                return value

            text = json.dumps(_redact(payload))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        text = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", text)
        return text[:max_len]

    def request_download_token(self) -> Dict[str, Any]:
        """
        Obtain an OAuth2 access token using the official CDSE password grant.

        client_id=cdse-public, grant_type=password, username/password from settings.
        Never logs credentials or tokens.
        """
        username = settings.CDSE_USERNAME
        password = settings.CDSE_PASSWORD
        if not username or not password:
            logger.error("CDSE_USERNAME and CDSE_PASSWORD required for download token.")
            return {
                "ok": False,
                "http_status": None,
                "message": "CDSE_USERNAME and CDSE_PASSWORD are required for product download.",
                "sanitized_body": "",
            }

        data = {
            "grant_type": "password",
            "client_id": self.DOWNLOAD_PUBLIC_CLIENT_ID,
            "username": username,
            "password": password,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.TOKEN_URL, data=data)
        except Exception as exc:
            logger.error("CDSE download token request failed before HTTP response.")
            return {
                "ok": False,
                "http_status": None,
                "message": f"Download token request failed: {type(exc).__name__}",
                "sanitized_body": "",
            }

        sanitized = self.sanitize_error_body(response.text)
        if response.status_code != 200:
            logger.error(
                "CDSE download token request failed with HTTP %s.",
                response.status_code,
            )
            return {
                "ok": False,
                "http_status": response.status_code,
                "message": f"Download authentication failed with HTTP {response.status_code}.",
                "sanitized_body": sanitized,
            }

        try:
            payload = response.json()
        except Exception:
            logger.error("CDSE download token response was not JSON.")
            return {
                "ok": False,
                "http_status": response.status_code,
                "message": "Download authentication response was not JSON.",
                "sanitized_body": sanitized,
            }

        token = payload.get("access_token")
        if not token:
            logger.error("CDSE download token response omitted access_token.")
            return {
                "ok": False,
                "http_status": response.status_code,
                "message": "Download authentication succeeded but access_token was missing.",
                "sanitized_body": self.sanitize_error_body(json.dumps(payload)),
            }

        return {
            "ok": True,
            "http_status": response.status_code,
            "access_token": token,
            "message": "Download authentication succeeded.",
            "sanitized_body": "",
        }

    def get_download_token(self) -> Optional[str]:
        """Obtain OAuth2 access token for CDSE download API using password grant."""
        result = self.request_download_token()
        if not result.get("ok"):
            return None
        return result.get("access_token")

    def download_quicklook(self, product_id: str, product_title: str, output_dir: str) -> Dict[str, Any]:
        """
        Download the quicklook PNG for a product.
        """
        url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})/Nodes({product_title}.SAFE)/Nodes(preview)/Nodes(quick-look.png)/$value"
        token = self.get_access_token()
        if not token:
            return {"status": "ERROR", "message": "Failed to get access token"}

        headers = {"Authorization": f"Bearer {token}"}
        os.makedirs(output_dir, exist_ok=True)
        local_path = os.path.join(output_dir, f"{product_id}_quicklook.png")

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(response.content)
            return {"status": "SUCCESS", "local_path": local_path}
        except Exception as exc:
            logger.error(f"Failed to download quicklook: {exc}")
            return {"status": "ERROR", "message": str(exc)}

    def download_product(
        self,
        product_id: str,
        output_dir: str,
        product_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Stream a single Sentinel-1 product from the official CDSE OData $value endpoint.

        Endpoint: https://download.dataspace.copernicus.eu/odata/v1/Products(<UUID>)/$value
        """
        username = settings.CDSE_USERNAME
        password = settings.CDSE_PASSWORD
        if not username or not password:
            return {
                "status": "UNAVAILABLE",
                "message": "CDSE_USERNAME and CDSE_PASSWORD are required for product download.",
                "download_url": self.DOWNLOAD_URL_TEMPLATE.format(product_id=product_id),
            }

        token_result = self.request_download_token()
        if not token_result.get("ok"):
            return {
                "status": "ERROR",
                "message": token_result.get("message"),
                "http_status": token_result.get("http_status"),
                "sanitized_body": token_result.get("sanitized_body", ""),
                "download_url": self.DOWNLOAD_URL_TEMPLATE.format(product_id=product_id),
            }

        token = token_result["access_token"]
        download_url = self.DOWNLOAD_URL_TEMPLATE.format(product_id=product_id)
        headers = {"Authorization": f"Bearer {token}"}

        os.makedirs(output_dir, exist_ok=True)
        filename = self._download_filename(product_id, product_name)
        local_path = os.path.join(output_dir, filename)

        timeout = httpx.Timeout(connect=60.0, read=300.0, write=60.0, pool=60.0)
        bytes_written = 0
        content_type = None
        http_status = None

        try:
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                current_url = download_url
                for _ in range(10):
                    with client.stream("GET", current_url, headers=headers) as response:
                        http_status = response.status_code
                        content_type = response.headers.get("content-type")
                        if response.is_redirect:
                            location = response.headers.get("Location")
                            if not location:
                                return {
                                    "status": "ERROR",
                                    "message": f"Download redirect HTTP {http_status} omitted Location.",
                                    "http_status": http_status,
                                    "content_type": content_type,
                                    "download_url": download_url,
                                    "final_url_host": urlparse(current_url).hostname,
                                }
                            next_url = urljoin(current_url, location)
                            next_host = urlparse(next_url).hostname
                            if next_host not in self._DOWNLOAD_REDIRECT_HOSTS:
                                logger.error(
                                    "CDSE download redirected to unexpected host; refusing to follow."
                                )
                                return {
                                    "status": "ERROR",
                                    "message": "Download redirected to a non-CDSE host.",
                                    "http_status": http_status,
                                    "content_type": content_type,
                                    "download_url": download_url,
                                }
                            current_url = next_url
                            continue

                        if http_status != 200:
                            error_body = self._read_limited_body(response)
                            logger.error(
                                "CDSE download failed for product %s with HTTP %s.",
                                product_id,
                                http_status,
                            )
                            return {
                                "status": "ERROR",
                                "message": f"Download failed with HTTP {http_status}.",
                                "http_status": http_status,
                                "content_type": content_type,
                                "sanitized_body": self.sanitize_error_body(error_body),
                                "download_url": download_url,
                                "final_url_host": urlparse(str(response.url)).hostname,
                            }

                        with open(local_path, "wb") as handle:
                            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                                if chunk:
                                    handle.write(chunk)
                                    bytes_written += len(chunk)
                        break
                else:
                    return {
                        "status": "ERROR",
                        "message": "Download exceeded CDSE redirect limit.",
                        "download_url": download_url,
                    }
        except Exception as exc:
            logger.error("CDSE download failed for product %s: %s", product_id, type(exc).__name__)
            if os.path.exists(local_path) and os.path.getsize(local_path) == 0:
                os.remove(local_path)
            return {
                "status": "ERROR",
                "message": f"Download failed: {type(exc).__name__}",
                "http_status": http_status,
                "content_type": content_type,
                "bytes_written": bytes_written,
                "download_url": download_url,
            }

        file_exists = os.path.isfile(local_path)
        file_size = os.path.getsize(local_path) if file_exists else 0
        archive_check = self.verify_sentinel1_product_archive(local_path) if file_size else {
            "valid": False,
            "reason": "Downloaded file is empty.",
        }

        if not file_exists or file_size == 0:
            return {
                "status": "ERROR",
                "message": "Download completed but the output file is missing or empty.",
                "http_status": http_status,
                "content_type": content_type,
                "file_size": file_size,
                "storage_path": local_path,
                "download_url": download_url,
                "product_id": product_id,
            }

        return {
            "status": "COMPLETED",
            "storage_path": local_path,
            "product_id": product_id,
            "product_name": product_name,
            "data_mode": "REAL_SATELLITE_DATA",
            "http_status": http_status,
            "content_type": content_type,
            "file_size": file_size,
            "download_url": download_url,
            "archive": archive_check,
        }

    @staticmethod
    def _download_filename(product_id: str, product_name: Optional[str]) -> str:
        if product_name:
            name = os.path.basename(product_name.strip())
            if not name.lower().endswith(".zip"):
                name = f"{name}.zip"
            return name
        return f"{product_id}.zip"

    @staticmethod
    def _read_limited_body(response: httpx.Response, max_bytes: int = 4096) -> str:
        chunks: List[bytes] = []
        total = 0
        for chunk in response.iter_bytes(chunk_size=1024):
            if not chunk:
                continue
            remaining = max_bytes - total
            chunks.append(chunk[:remaining])
            total += min(len(chunk), remaining)
            if total >= max_bytes:
                break
        return b"".join(chunks).decode("utf-8", errors="replace")

    @staticmethod
    def verify_sentinel1_product_archive(path: str) -> Dict[str, Any]:
        """Validate that a downloaded file is a ZIP containing a Sentinel-1 SAFE product."""
        if not os.path.isfile(path):
            return {"valid": False, "reason": "File does not exist."}
        size = os.path.getsize(path)
        if size <= 0:
            return {"valid": False, "reason": "File is empty.", "file_size": size}
        if not zipfile.is_zipfile(path):
            return {"valid": False, "reason": "File is not a ZIP archive.", "file_size": size}

        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                bad_entry = archive.testzip()
        except zipfile.BadZipFile:
            return {"valid": False, "reason": "ZIP archive is corrupt.", "file_size": size}

        if bad_entry:
            return {
                "valid": False,
                "reason": "ZIP CRC check failed.",
                "file_size": size,
                "entry_count": len(names),
            }

        has_safe = any(".SAFE/" in name or name.endswith(".SAFE") for name in names)
        has_manifest = any(name.endswith("manifest.safe") for name in names)
        has_measurement = any("/measurement/" in name.replace("\\", "/") for name in names)
        valid = has_safe and has_manifest
        reason = None if valid else "ZIP is readable but missing Sentinel-1 SAFE/manifest.safe structure."
        return {
            "valid": valid,
            "reason": reason,
            "file_size": size,
            "entry_count": len(names),
            "has_safe": has_safe,
            "has_manifest": has_manifest,
            "has_measurement": has_measurement,
        }
