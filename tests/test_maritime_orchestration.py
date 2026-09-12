import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.services.maritime_service import MaritimeOrchestrator
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.app.api.v1.router import api_router

app = FastAPI()
app.include_router(api_router)
client = TestClient(app)

@pytest.fixture
def orchestrator():
    return MaritimeOrchestrator()

@pytest.mark.asyncio
async def test_osiris_success(orchestrator):
    with patch('backend.app.services.osiris.client.OsirisClient.fetch_maritime_data', new_callable=AsyncMock) as mock_osiris:
        from backend.app.services.osiris.schemas import OsirisMaritimeResponse, OsirisVessel
        mock_data = OsirisMaritimeResponse()
        mock_data.ships = [OsirisVessel(lat=10.0, lng=20.0, timestamp=1700000000000, speed=15.0, course=90.0, source="Terrestrial", name="Test Ship")]
        mock_osiris.return_value = ("SUCCESS", mock_data)
        
        response = await orchestrator.get_vessels()
        assert response.status == "SUCCESS"
        assert response.provider == "OSIRIS"
        assert response.fallback_used is False
        assert response.vessel_count == 1

@pytest.mark.asyncio
async def test_osiris_timeout_fallback_to_aishub(orchestrator):
    with patch('backend.app.services.osiris.client.OsirisClient.fetch_maritime_data', new_callable=AsyncMock) as mock_osiris:
        mock_osiris.return_value = ("TIMEOUT", None)
        with patch('backend.app.services.ais_client.AISClient.get_vessels_in_bbox') as mock_aishub:
            mock_aishub.return_value = {"status": "COMPLETED", "vessels": [{"mmsi": 123, "latitude": 10.0, "longitude": 20.0}]}
            
            # Require bbox for aishub
            response = await orchestrator.get_vessels(min_lat=0.0, min_lon=0.0, max_lat=20.0, max_lon=30.0)
            assert response.status == "SUCCESS"
            assert response.provider == "AISHUB"
            assert response.fallback_used is True
            assert response.fallback_reason == "OSIRIS_TIMEOUT"

@pytest.mark.asyncio
async def test_aishub_failure_demo_fallback(orchestrator):
    orchestrator.demo_enabled = True
    with patch('backend.app.services.osiris.client.OsirisClient.fetch_maritime_data', new_callable=AsyncMock) as mock_osiris:
        mock_osiris.return_value = ("TIMEOUT", None)
        with patch('backend.app.services.ais_client.AISClient.get_vessels_in_bbox') as mock_aishub:
            mock_aishub.return_value = {"status": "ERROR"}
            
            response = await orchestrator.get_vessels(min_lat=0.0, min_lon=0.0, max_lat=20.0, max_lon=30.0)
            assert response.status == "SUCCESS"
            assert response.provider == "DEMO_DATA"
            assert response.fallback_used is True

@pytest.mark.asyncio
async def test_all_fail_no_demo(orchestrator):
    orchestrator.demo_enabled = False
    with patch('backend.app.services.osiris.client.OsirisClient.fetch_maritime_data', new_callable=AsyncMock) as mock_osiris:
        mock_osiris.return_value = ("TIMEOUT", None)
        with patch('backend.app.services.ais_client.AISClient.get_vessels_in_bbox') as mock_aishub:
            mock_aishub.return_value = {"status": "ERROR"}
            
            response = await orchestrator.get_vessels(min_lat=0.0, min_lon=0.0, max_lat=20.0, max_lon=30.0)
            assert response.status == "UNAVAILABLE"
            assert response.provider is None

def test_api_success():
    with patch('backend.app.services.maritime_service.MaritimeOrchestrator.get_vessels', new_callable=AsyncMock) as mock_get:
        mock_res = MagicMock()
        mock_res.model_dump.return_value = {"status": "SUCCESS", "provider": "OSIRIS", "vessels": []}
        mock_get.return_value = mock_res
        
        response = client.get("/api/v1/maritime/vessels")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "SUCCESS"

def test_api_invalid_bbox():
    response = client.get("/api/v1/maritime/vessels?min_lat=10")
    assert response.status_code == 400
