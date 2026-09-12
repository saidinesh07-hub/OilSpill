import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from backend.app.services.osiris.client import OsirisClient
from backend.app.services.osiris.schemas import OsirisMaritimeResponse

@pytest.fixture
def osiris_client():
    return OsirisClient()

@pytest.mark.asyncio
async def test_successful_osiris_response(osiris_client):
    mock_data = {
        "ports": [],
        "chokepoints": [],
        "ships": [{"id": 1, "mmsi": 123456789, "timestamp": 1700000000000, "lat": 10.0, "lng": 20.0}],
        "total_ports": 0,
        "total_chokepoints": 0,
        "total_ships": 1
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status.return_value = None

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        status, data = await osiris_client.fetch_maritime_data()
        
    assert status == "SUCCESS"
    assert isinstance(data, OsirisMaritimeResponse)
    assert len(data.ships) == 1

@pytest.mark.asyncio
async def test_empty_ships_array(osiris_client):
    mock_data = {
        "ships": [],
        "total_ships": 0
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status.return_value = None

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        status, data = await osiris_client.fetch_maritime_data()
        
    assert status == "SUCCESS"
    assert len(data.ships) == 0

@pytest.mark.asyncio
async def test_malformed_json(osiris_client):
    mock_response = MagicMock()
    # Pydantic validation error or JSON decode error
    mock_response.json.side_effect = ValueError("Bad JSON")
    mock_response.raise_for_status.return_value = None

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        status, data = await osiris_client.fetch_maritime_data()
        
    assert status == "INVALID_RESPONSE"
    assert data is None

@pytest.mark.asyncio
async def test_http_500(osiris_client):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        status, data = await osiris_client.fetch_maritime_data()
        
    assert status == "HTTP_ERROR"
    assert data is None

@pytest.mark.asyncio
async def test_timeout(osiris_client):
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Timeout")
        status, data = await osiris_client.fetch_maritime_data()
        
    assert status == "TIMEOUT"
    assert data is None

@pytest.mark.asyncio
async def test_connection_failure(osiris_client):
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Failed to connect")
        status, data = await osiris_client.fetch_maritime_data()
        
    assert status == "CONNECTION_ERROR"
    assert data is None

@pytest.mark.asyncio
async def test_disabled_client(osiris_client):
    osiris_client.enabled = False
    status, data = await osiris_client.fetch_maritime_data()
    assert status == "DISABLED"
    assert data is None
