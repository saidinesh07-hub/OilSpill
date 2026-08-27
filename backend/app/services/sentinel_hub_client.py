"""Copernicus Data Space Sentinel Hub Process API — actual Sentinel-1 pixels."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import io
import uuid
import httpx
import numpy as np
from PIL import Image
from backend.app.core.config import settings
from backend.app.core.logging import logger

PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PREVIEW_DIR = Path("data/sar_previews")

VV_PNG_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{bands: ["VV", "VH", "dataMask"]}],
    output: {bands: 4}
  };
}
function evaluatePixel(s) {
  var vv = Math.max(0, Math.min(1, (s.VV + 25.0) / 25.0));
  var vh = Math.max(0, Math.min(1, (s.VH + 30.0) / 25.0));
  return [vv, vh, (vv + vh) / 2.0, s.dataMask];
}
"""

VV_FLOAT_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{bands: ["VV", "VH", "dataMask"]}],
    output: {bands: 3, sampleType: "FLOAT32"}
  };
}
function evaluatePixel(s) {
  return [s.VV, s.VH, s.dataMask];
}
"""


class SentinelHubProcessClient:
    def __init__(self):
        self.client_id = settings.CDSE_CLIENT_ID
        self.client_secret = settings.CDSE_CLIENT_SECRET

    def _token(self) -> Optional[str]:
        if not self.client_id or not self.client_secret:
            return None
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
            if resp.status_code != 200:
                logger.error("Sentinel Hub token HTTP %s", resp.status_code)
                return None
            return resp.json().get("access_token")
        except Exception:
            logger.error("Sentinel Hub token request failed")
            return None

    def fetch_s1_window(
        self,
        bbox: List[float],
        time_from: datetime,
        time_to: datetime,
        width: int = 512,
        height: int = 512,
    ) -> Dict[str, Any]:
        """
        Fetch a Sentinel-1 GRD window for bbox/time via Process API.
        Returns PNG preview path plus VV/VH float arrays when possible.
        """
        token = self._token()
        if not token:
            return {
                "status": "UNAVAILABLE",
                "message": "Sentinel Hub Process API token unavailable. CDSE_CLIENT_ID/CDSE_CLIENT_SECRET required.",
            }

        t0 = time_from.astimezone(timezone.utc) if time_from.tzinfo else time_from.replace(tzinfo=timezone.utc)
        t1 = time_to.astimezone(timezone.utc) if time_to.tzinfo else time_to.replace(tzinfo=timezone.utc)
        body = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-1-grd",
                        "dataFilter": {
                            "timeRange": {
                                "from": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "to": t1.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            },
                            "mosaickingOrder": "mostRecent",
                        },
                        "processing": {"orthorectify": True, "backCoeff": "SIGMA0_ELLIPSOID"},
                    }
                ],
            },
            "output": {"width": width, "height": height},
            "evalscript": VV_PNG_EVALSCRIPT,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "image/png",
        }
        try:
            with httpx.Client(timeout=90.0) as client:
                png_resp = client.post(PROCESS_URL, json=body, headers=headers)
        except Exception as exc:
            return {"status": "ERROR", "message": f"Process API request failed: {type(exc).__name__}"}

        if png_resp.status_code != 200:
            snippet = (png_resp.text or "")[:300]
            return {
                "status": "ERROR",
                "message": f"Process API HTTP {png_resp.status_code}",
                "detail": snippet,
            }

        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        fname = f"{uuid.uuid4().hex}_vv.png"
        png_path = PREVIEW_DIR / fname
        png_path.write_bytes(png_resp.content)

        arrays = self._fetch_float_arrays(token, bbox, t0, t1, width, height)
        return {
            "status": "OK",
            "image_url": f"/api/v1/satellite/preview/{fname}",
            "bbox": bbox,
            "width": width,
            "height": height,
            "vv": arrays.get("vv"),
            "vh": arrays.get("vh"),
            "mask": arrays.get("mask"),
        }

    def _fetch_float_arrays(
        self,
        token: str,
        bbox: List[float],
        t0: datetime,
        t1: datetime,
        width: int,
        height: int,
    ) -> Dict[str, Any]:
        body = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-1-grd",
                        "dataFilter": {
                            "timeRange": {
                                "from": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "to": t1.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            },
                            "mosaickingOrder": "mostRecent",
                        },
                        "processing": {"orthorectify": True, "backCoeff": "SIGMA0_ELLIPSOID"},
                    }
                ],
            },
            "output": {"width": width, "height": height},
            "evalscript": VV_FLOAT_EVALSCRIPT,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "image/tiff",
        }
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(PROCESS_URL, json=body, headers=headers)
            if resp.status_code != 200:
                logger.error("Process API float TIFF HTTP %s", resp.status_code)
                return {}
            from rasterio.io import MemoryFile
            with MemoryFile(resp.content) as mem:
                with mem.open() as ds:
                    vv = ds.read(1).astype(np.float32)
                    vh = ds.read(2).astype(np.float32) if ds.count >= 2 else None
                    mask = ds.read(3).astype(np.float32) if ds.count >= 3 else np.ones_like(vv)
            return {"vv": vv, "vh": vh, "mask": mask}
        except Exception as exc:
            logger.error("Float SAR decode failed: %s", type(exc).__name__)
            return {}
