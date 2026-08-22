# API Specification (v1)

The system exposes a FastAPI REST backend structured under `/api/v1`. Interactive OpenAPI Swagger documentation is available at `http://127.0.0.1:8000/docs`.

---

## Key Endpoints Reference

### 1. Health & Diagnostics
- `GET /api/v1/health`
  - **Description**: Returns system operational status, connected database, ML device, and timestamp.
  - **Response**: `{"status": "HEALTHY", "device": "cpu", "database": "CONNECTED", ...}`

### 2. Satellite Scenes
- `GET /api/v1/scenes`
  - **Description**: Lists all ingested SAR satellite scenes with WGS84 footprint polygons and acquisition times.
- `GET /api/v1/scenes/{scene_id}`
  - **Description**: Returns metadata for a specific scene.
- `GET /api/v1/scenes/{scene_id}/observations`
  - **Description**: Retrieves preprocessed observations derived from the scene.

### 3. Spill Detections
- `GET /api/v1/detections`
  - **Description**: Returns list of detected slick polygons with area in km², confidence, and morphology.
  - **Parameters**: `min_confidence` (float), `predicted_class` (string).
- `GET /api/v1/detections/geojson`
  - **Description**: Standard RFC 7946 GeoJSON FeatureCollection of all detections.

### 4. Temporal Slick Tracking
- `GET /api/v1/tracks`
  - **Description**: Lists active physical slicks tracked across repeat satellite passes.
- `GET /api/v1/tracks/{track_id}`
  - **Description**: Detailed kinematics (drift speed km/h, heading, growth rate km²/hr).
- `GET /api/v1/tracks/{track_id}/history`
  - **Description**: Multi-date temporal observations with area deltas and state classifications (*EXPANSION, CONTRACTION, PERSISTENCE*).

### 5. Trajectory Forecasting
- `GET /api/v1/forecasts/latest?track_id={track_id}`
  - **Description**: Retrieves the most recent Monte Carlo forecast simulation run.
- `GET /api/v1/forecasts/{forecast_run_id}/geojson`
  - **Description**: GeoJSON polygons of uncertainty containment envelopes (50%, 80%, 95%) for lead times +6h, +12h, +24h, +48h.
  - **Parameters**: `horizon_hours` (int), `confidence_level` (float).

### 6. Environmental MetOcean
- `GET /api/v1/environmental/metocean_summary`
  - **Description**: Returns surface current vectors, 10m wind speeds, and Stokes drift for bounding box.

### 7. Asset Layers
- `GET /api/v1/assets`
  - **Description**: Tabular list of coastal assets (MPAs, fisheries, ports, beaches, wetlands).
- `GET /api/v1/assets/geojson`
  - **Description**: GeoJSON FeatureCollection of asset boundaries and sensitivity weights.

### 8. Impact Assessment & Risk Engine
- `GET /api/v1/impacts/{forecast_run_id}`
  - **Description**: Spatiotemporal intersection results with estimated time-to-impact and exposure levels.
- `GET /api/v1/risk/{impact_id}`
  - **Description**: Returns 6-factor decomposed risk score and text explanation.
- `GET /api/v1/recommendations/{track_id}`
  - **Description**: Ranked decision-support recommendations (containment booms, shoreline defense, aerial patrol).
- `GET /api/v1/risk/analysis/sensitivity`
  - **Description**: Weight perturbation sensitivity report proving monotonic stability.

### 9. Grounded AI Assistant
- `POST /api/v1/assistant/query`
  - **Request Body**: `{"question": "Why is this spill high risk?", "track_id": "..."}`
  - **Response**: `{"answer": "...", "citations": [{"source_table": "...", "coordinates": [...]}]}`

### 10. Pipeline Execution
- `POST /api/v1/pipeline/process/{scene_id}`
  - **Description**: Triggers full intelligence chain on a scene.
- `POST /api/v1/pipeline/case_studies/seed`
  - **Description**: Ingests and executes the 2-pass Ennore Port 2017 Sentinel-1 historical incident.
