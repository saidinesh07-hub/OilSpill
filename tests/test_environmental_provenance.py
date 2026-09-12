import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from backend.app.services.intelligence_orchestrator import IntelligenceOrchestrator

@patch("backend.app.database.models.SpillDetection")
@patch("backend.app.api.v1.endpoints.maritime.correlate_spill_vessels")
def test_orchestrator_propagates_provenance(mock_correlate, mock_spill):
    db_mock = MagicMock()
    
    mock_detection = MagicMock()
    mock_detection.created_at = datetime.now(timezone.utc)
    mock_detection.geom_geojson = {"type": "Polygon", "coordinates": [[[0,0],[0,1],[1,1],[1,0],[0,0]]]}
    mock_detection.centroid_lat = 0.5
    mock_detection.centroid_lon = 0.5
    mock_detection.area_km2 = 10.0
    
    db_mock.query().filter().first.return_value = mock_detection
    mock_correlate.return_value = MagicMock(data={"candidates": []})
    
    orchestrator = IntelligenceOrchestrator(db=db_mock)
    response = orchestrator.get_unified_intelligence("SPILL-123")
    
    data = response.data
    print("WARNINGS:", data.get("warnings"))
    assert "environmental_provenance" in data
    prov = data["environmental_provenance"]
    
    # By default, without credentials, CMEMSAdapter returns DEMO_DATA
    assert "currents" in prov
    assert "winds" in prov
    assert prov["currents"]["data_mode"] == "DEMO_DATA"
    assert prov["winds"]["data_mode"] == "DEMO_DATA"
    assert "Live" not in prov["currents"]["data_provenance"]
