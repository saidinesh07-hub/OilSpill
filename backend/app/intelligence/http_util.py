"""Shared HTTP helpers with timeout, retry, and sanitized error reporting."""
from typing import Any, Dict, Optional
import time
import httpx
from backend.app.core.logging import logger

DEFAULT_TIMEOUT = 25.0


def fetch_json(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 2,
) -> Dict[str, Any]:
    """
    Perform an HTTP request and return {ok, status_code, data, error}.
    Never includes Authorization header values in error strings.
    """
    last_error = "request_failed"
    last_status = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
            last_status = response.status_code
            if response.status_code >= 500 and attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            content_type = response.headers.get("content-type", "")
            payload: Any
            if "json" in content_type:
                payload = response.json()
            else:
                payload = {"text": (response.text or "")[:400]}
            if response.status_code >= 400:
                return {
                    "ok": False,
                    "status_code": response.status_code,
                    "data": None,
                    "error": f"HTTP {response.status_code}",
                    "sanitized_body": str(payload)[:400],
                }
            return {
                "ok": True,
                "status_code": response.status_code,
                "data": payload,
                "error": None,
            }
        except httpx.TimeoutException:
            last_error = "timeout"
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
        except Exception as exc:
            last_error = type(exc).__name__
            logger.info("HTTP helper failed for %s: %s", url.split("?")[0], type(exc).__name__)
            if attempt < retries:
                time.sleep(0.4 * (attempt + 1))
                continue
    return {
        "ok": False,
        "status_code": last_status,
        "data": None,
        "error": last_error,
    }
