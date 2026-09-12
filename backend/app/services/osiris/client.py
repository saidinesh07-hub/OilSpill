import httpx
from typing import Optional, Tuple
from backend.app.core.config import settings
from backend.app.core.logging import logger
from .schemas import OsirisMaritimeResponse

class OsirisClient:
    def __init__(self):
        self.base_url = settings.OSIRIS_BASE_URL.rstrip('/')
        self.timeout = settings.OSIRIS_TIMEOUT_SECONDS
        self.enabled = getattr(settings, 'OSIRIS_ENABLED', True)

    async def fetch_maritime_data(self) -> Tuple[str, Optional[OsirisMaritimeResponse]]:
        """
        Fetches the raw maritime data from OSIRIS.
        Returns a tuple: (status, data)
        status can be SUCCESS, TIMEOUT, CONNECTION_ERROR, HTTP_ERROR, INVALID_RESPONSE, DISABLED.
        """
        if not self.enabled:
            return "DISABLED", None

        url = f"{self.base_url}/api/maritime"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                # Validate with Pydantic
                parsed_data = OsirisMaritimeResponse(**data)
                return "SUCCESS", parsed_data

        except httpx.TimeoutException:
            logger.warning(f"OSIRIS connection timed out ({self.timeout}s): {url}")
            return "TIMEOUT", None
        except httpx.ConnectError:
            logger.warning(f"OSIRIS connection failed: {url}")
            return "CONNECTION_ERROR", None
        except httpx.HTTPStatusError as e:
            logger.warning(f"OSIRIS HTTP error {e.response.status_code}: {url}")
            return "HTTP_ERROR", None
        except Exception as e:
            logger.error(f"OSIRIS unexpected error or invalid response: {e}")
            return "INVALID_RESPONSE", None
