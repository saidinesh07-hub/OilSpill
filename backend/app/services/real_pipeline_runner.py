import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.core.logging import logger
from backend.app.services.cdse_client import CDSEClient
from backend.app.services.scene_ingestion import SceneIngestionService
from backend.app.services.pipeline_orchestrator import IntelligencePipelineOrchestrator
import zipfile
import rasterio

class RealPipelineRunner:
    def __init__(self, db: Session):
        self.db = db
        self.cdse = CDSEClient()
        self.ingestion = SceneIngestionService(db)
        self.orchestrator = IntelligencePipelineOrchestrator(db)

    def run_pipeline(self, lat: float, lon: float) -> dict:
        if not self.cdse.has_credentials:
             return {"status": "UNAVAILABLE", "message": "Copernicus API credentials not configured."}

        # Search last 14 days
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=14)
        bbox = [lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5]

        logger.info(f"Searching CDSE for location ({lat}, {lon})")
        search_result = self.cdse.search_sentinel1(bbox=bbox, start=start_date, end=end_date)
        if search_result.get("data_mode") == "UNAVAILABLE" or not search_result.get("products"):
            return {"status": "UNAVAILABLE", "message": "No Sentinel-1 products found for this location in the last 14 days."}

        product = search_result["products"][0]
        product_id = product["id"]
        product_name = product["title"]
        logger.info(f"Found product: {product_name} ({product_id})")

        output_dir = "temp_downloads"
        os.makedirs(output_dir, exist_ok=True)
        zip_path = os.path.join(output_dir, f"{product_name}.zip")

        # Download if not exists
        if not os.path.exists(zip_path):
             logger.info(f"Downloading product {product_id}...")
             dl_result = self.cdse.download_product(product_id, output_dir, product_name)
             if dl_result["status"] == "ERROR":
                 return {"status": "UNAVAILABLE", "message": f"Download failed: {dl_result.get('message')}"}

        # Find the VV measurement tiff inside the zip
        tiff_path = None
        try:
             with zipfile.ZipFile(zip_path, 'r') as z:
                 for name in z.namelist():
                     if "/measurement/" in name and name.endswith(".tiff") and "-vv-" in name:
                         tiff_path = f"zip://{os.path.abspath(zip_path)}!/{name}"
                         break
        except zipfile.BadZipFile:
             return {"status": "UNAVAILABLE", "message": "Downloaded zip is corrupt."}

        if not tiff_path:
             return {"status": "UNAVAILABLE", "message": "VV polarization TIFF not found in the product archive."}

        logger.info(f"Using measurement TIFF: {tiff_path}")

        # Ingest scene and process
        try:
             scene = self.ingestion.ingest_from_local_geotiff(
                 scene_name=product_name,
                 acquisition_time=datetime.fromisoformat(product["acquisition_time"].replace("Z", "+00:00")),
                 geotiff_path=tiff_path,
                 is_synthetic=False
             )
             
             # Read SAR Raster for ML Engine
             from backend.app.geospatial.sar_reader import read_sar_geotiff
             # Downsample read to avoid memory issues on full 1.5GB scene
             sar_raster, _ = read_sar_geotiff(tiff_path, window=(0, 0, 4096, 4096))
             
             res = self.orchestrator.process_scene(scene, sar_raster=sar_raster, is_synthetic=False)
             return {"status": "COMPLETED", "scene": res}
        except Exception as e:
             logger.error(f"Processing failed: {str(e)}")
             return {"status": "ERROR", "message": f"Processing failed: {str(e)}"}
