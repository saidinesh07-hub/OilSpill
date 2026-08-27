"""
Dedicated validation: download ONE real Sentinel-1 product via CDSE OData.

Does not search, does not download multiple products, and never prints secrets.
"""
import os
import sys

sys.path.insert(0, os.getcwd())

from backend.app.core.config import settings
from backend.app.services.cdse_client import CDSEClient

PRODUCT_ID = "bd3012c2-2e52-4891-91fd-d6fc79084d37"
PRODUCT_NAME = "S1D_IW_GRDH_1SDV_20260820T005429_20260820T005454_004202_007B39_CEBC.SAFE"
OUTPUT_DIR = os.path.join(os.getcwd(), "temp_downloads")


def _print_report(result: dict) -> int:
    download_url = CDSEClient.DOWNLOAD_URL_TEMPLATE.format(product_id=PRODUCT_ID)
    storage_path = result.get("storage_path")
    file_exists = bool(storage_path and os.path.isfile(storage_path))
    file_size = os.path.getsize(storage_path) if file_exists else 0
    archive = result.get("archive") or {}
    if storage_path and file_exists and not archive:
        archive = CDSEClient.verify_sentinel1_product_archive(storage_path)

    print("=== CDSE Sentinel-1 download validation ===")
    print(f"product_id: {PRODUCT_ID}")
    print(f"product_name: {PRODUCT_NAME}")
    print(f"download_endpoint: {download_url}")
    print(f"username_configured: {bool(settings.CDSE_USERNAME)}")
    print(f"password_configured: {bool(settings.CDSE_PASSWORD)}")
    print(f"auth_http_status: {result.get('auth_http_status', result.get('http_status'))}")
    print(f"download_http_status: {result.get('http_status')}")
    print(f"content_type: {result.get('content_type')}")
    print(f"status: {result.get('status')}")
    print(f"message: {result.get('message')}")
    if result.get("sanitized_body"):
        print(f"sanitized_response: {result.get('sanitized_body')}")
    print(f"download_location: {storage_path}")
    print(f"file_exists: {file_exists}")
    print(f"file_size_bytes: {file_size}")
    print(f"file_nonzero: {file_size > 0}")
    print(f"safe_zip_valid: {archive.get('valid')}")
    print(f"safe_zip_reason: {archive.get('reason')}")
    print(f"has_safe: {archive.get('has_safe')}")
    print(f"has_manifest: {archive.get('has_manifest')}")
    print(f"has_measurement: {archive.get('has_measurement')}")
    print(f"zip_entry_count: {archive.get('entry_count')}")

    success = (
        result.get("status") == "COMPLETED"
        and result.get("http_status") == 200
        and file_exists
        and file_size > 0
        and archive.get("valid") is True
    )
    print(f"real_sentinel1_product_downloaded: {success}")
    return 0 if success else 1


def main() -> int:
    client = CDSEClient()
    token_result = client.request_download_token()
    auth_status = token_result.get("http_status")
    if not token_result.get("ok"):
        return _print_report(
            {
                "status": "ERROR",
                "message": token_result.get("message"),
                "http_status": auth_status,
                "auth_http_status": auth_status,
                "sanitized_body": token_result.get("sanitized_body"),
            }
        )

    result = client.download_product(PRODUCT_ID, OUTPUT_DIR, product_name=PRODUCT_NAME)
    result["auth_http_status"] = 200
    return _print_report(result)


if __name__ == "__main__":
    raise SystemExit(main())
