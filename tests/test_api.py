"""
Integration Tests for FastAPI Backend Endpoints and Assistant
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db

client = TestClient(app)


def setup_module():
    init_db()


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["database"] == "CONNECTED"


def test_scenes_endpoint():
    response = client.get("/api/v1/scenes")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert isinstance(res["data"], list)


def test_detections_geojson():
    response = client.get("/api/v1/detections/geojson")
    assert response.status_code == 200
    res = response.json()
    assert res["type"] == "FeatureCollection"
    assert "features" in res


def test_assets_endpoint():
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True


def test_grounded_assistant_query():
    # Query about risk
    response = client.post("/api/v1/assistant/query", json={"question": "Why is this spill high risk?"})
    assert response.status_code == 200
    data = response.json()
    assert data["is_grounded"] is True
    assert "answer" in data
    assert len(data["answer"]) > 10

    # Query about size
    response2 = client.post("/api/v1/assistant/query", json={"question": "How large is the detected slick?"})
    assert response2.status_code == 200
    assert "km²" in response2.json()["answer"]
