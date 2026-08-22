"""
Structured Logging Configuration
"""
import logging
import sys
from backend.app.core.config import settings

def setup_logging():
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Suppress verbose third-party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("rasterio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger("oil_spill_intel")
    logger.info(f"Logging initialized at level: {settings.LOG_LEVEL}")
    return logger

logger = setup_logging()
