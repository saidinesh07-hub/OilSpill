# Data Provenance Audit — Oil Spill Intelligence Dashboard

**Audit date:** 2026-08-22  
**Purpose:** Trace every value displayed in the GIS dashboard to its computational source and classify as REAL vs SYNTHETIC/DEMO.

## Legend

| Classification | Meaning |
|----------------|---------|
| **REAL calculation** | Computed from stored observations using documented algorithms |
| **REAL model inference** | Output of PyTorch segmentation model (weights may be untrained) |
| **REAL dataset value** | Loaded from external dataset file on disk |
| **SYNTHETIC/DEMO** | Generated for pipeline testing; labeled `DEMO_DATA` |
| **HARDCODED placeholder** | Static UI constant not from backend |
| **RANDOM** | Stochastic component (Monte Carlo ensemble, demo SAR noise) |

---

## Dashboard Value Traceability

| UI VALUE | SOURCE FILE | FUNCTION | DATA SOURCE | REAL/SYNTHETIC | CALCULATION METHOD | CURRENT STATUS |
|----------|-------------|----------|-------------|----------------|-------------------|----------------|
| Active incident name (`slick_name`) | `frontend/App.tsx` → `Navbar.tsx` | `loadData()` → `apiService.getTracks()` | `tracked_slicks.slick_name` DB | REAL calculation | Assigned at track creation in `pipeline_orchestrator.py` | **OK** — from DB |
| Surface extent (`total_area_km2`) | `Navbar.tsx` | props from `activeTrack` | `tracked_slicks.total_area_km2` | REAL calculation (DEMO input) | Geodesic area from latest detection polygon (`geometry_ops.compute_geodetic_area_km2`) | **OK** — geodesic; DEMO SAR in default mode |
| Drift speed (`drift_speed_kmh`) | `Navbar.tsx` | props from `activeTrack` | `tracked_slicks.drift_speed_kmh` | REAL calculation | Kinematics from consecutive detections (`temporal/tracker.py`) | **OK** — computed between passes |
| Drift heading (`drift_heading_deg`) | `Navbar.tsx` | props from `activeTrack` | `tracked_slicks.drift_heading_deg` | REAL calculation | Bearing between consecutive centroids | **OK** |
| Track status (`ACTIVE`) | `Navbar.tsx` | `activeTrack.current_status` | DB | REAL calculation | Set by tracker | **OK** |
| DEMO / SYNTHETIC DATA badge | `Navbar.tsx` | `selectedScene.is_synthetic` | `satellite_scenes.is_synthetic` | SYNTHETIC flag | Set at scene registration | **OK** — visible when demo |
| SAR scene footprint polygon | `MapDashboard.tsx` | `scene.footprint_geojson` | `satellite_scenes.footprint_geojson` | SYNTHETIC (demo) / REAL (ingested) | Bbox → polygon at registration | **OK** |
| Scene name / acquisition time (tooltip) | `MapDashboard.tsx` | `scene.scene_name`, `scene.acquisition_time` | DB | Case-study metadata (DEMO) | Registered in `scene_ingestion.py` | **OK** |
| Detection polygon geometry | `MapDashboard.tsx` | `det.geom_geojson` | `spill_detections.geom_geojson` | REAL calculation (DEMO input) | `polygonize_segmentation_output()` | **OK** |
| Detection area (popup) | `MapDashboard.tsx` | `det.area_km2` | DB | REAL calculation | WGS84 geodesic area (`pyproj.Geod`) | **OK** — not degree² |
| Detection confidence | `MapDashboard.tsx` | `det.confidence` | DB | REAL model inference | Mean softmax probability over polygon mask | **Partial** — untrained model; demo reinforcement in DEMO mode |
| Look-alike risk score | `MapDashboard.tsx` | `det.lookalike_risk_score` | DB | REAL model inference | Mean class-2 probability in polygon | **Partial** |
| "CONFIRMED OIL SPILL" label | `MapDashboard.tsx` | popup template | **Frontend hardcoded** | HARDCODED placeholder | Label from `predicted_class === 'oil_spill'` | **FIXED** → classification label with uncertainty |
| Circularity (popup) | `MapDashboard.tsx` | `det.morphology_features.circularity` | DB | REAL calculation | 4πA/P² from geodesic area/perimeter | **OK** |
| Model version (popup) | `MapDashboard.tsx` | `det.model_version` | DB | Metadata | Set at inference | **OK** |
| Forecast band polygons | `MapDashboard.tsx` | `forecastBands` filtered by horizon | `forecast_bands.geom_geojson` | REAL calculation (DEMO forcing) | Lagrangian Monte Carlo ensemble | **OK** |
| Forecast band area (tooltip) | `MapDashboard.tsx` | `band.area_km2` | DB | REAL calculation | Geodesic area of containment contour | **OK** |
| Asset polygons | `MapDashboard.tsx` | `assets` from API | `assets.geom_geojson` | SYNTHETIC/DEMO | `assets/registry.py` reference polygons | **OK** — labeled demo assets |
| Asset sensitivity weight | `MapDashboard.tsx` | `asset.sensitivity_weight` | DB | DEMO reference | Static lookup table | **OK** |
| Historical track markers | `MapDashboard.tsx` | `activeTrack.temporal_observations` | DB | REAL calculation | Centroids from each pass detection | **OK** |
| Map initial center `[13.25, 80.35]` | `MapDashboard.tsx` | Leaflet init | HARDCODED placeholder | Static default view | Ennore region default | **OK** — view only; data drives layers |
| Timeline pass buttons | `TimelinePanel.tsx` | `temporalObs` from track | DB `temporal_observations` | REAL calculation | One row per satellite pass | **OK** |
| Pass area badge | `TimelinePanel.tsx` | `obs.area_km2` | DB | REAL calculation | From detection at that pass | **OK** |
| Temporal scrubber selection | `TimelinePanel.tsx` → `App.tsx` | `currentStep` | — | — | Was **not connected** to displayed state | **FIXED** → updates active detection & navbar |
| Forecast horizon buttons (+6/12/24/48h) | `TimelinePanel.tsx`, `ForecastControls.tsx` | `selectedHorizonHours` | UI state filtering | REAL calculation | Filters `forecast_bands.horizon_hours` | **OK** |
| Engine version badge | `ForecastControls.tsx` | `forecastRun.engine_version` | DB | Metadata | Stored at forecast run | **OK** |
| Surface current `0.24 m/s` | `ForecastControls.tsx` | **was hardcoded** | — | HARDCODED placeholder | Static string | **FIXED** → `forecastRun.summary` |
| Wind leeway `3.0%` | `ForecastControls.tsx` | **was hardcoded** | — | HARDCODED placeholder | Static string | **FIXED** → `forecastRun.wind_drift_factor` |
| Stokes drift `0.04 m/s` | `ForecastControls.tsx` | **was hardcoded** | — | HARDCODED placeholder | Static string | **FIXED** → `forecastRun.summary` |
| Diffusion `2.0 m²/s` | `ForecastControls.tsx` | **was hardcoded** | — | HARDCODED placeholder | Static string | **FIXED** → `forecastRun.diffusion_coefficient` |
| Risk score `/100` | `RiskWaterfallInspector.tsx` | `riskAssessment.total_risk_score` | DB | REAL calculation | 6-factor weighted formula (`risk/engine.py`) | **OK** |
| Risk category | `RiskWaterfallInspector.tsx` | `riskAssessment.risk_category` | DB | REAL calculation | Threshold on total score | **OK** |
| Factor waterfall bars | `RiskWaterfallInspector.tsx` | `factor_breakdown.weighted_contributions` | DB | REAL calculation | Decomposed AHP weights | **OK** |
| Fallback factor points | `RiskWaterfallInspector.tsx` | **was hardcoded** defaults | — | HARDCODED placeholder | Static fallback object | **FIXED** → show empty state only |
| Risk explanation text | `RiskWaterfallInspector.tsx` | `explanation_text` | DB | REAL calculation | Template from factor values | **OK** |
| Asset arrival window | `AssetImpactTable.tsx` | `imp.earliest_time_to_impact_hours` | DB | REAL calculation | Horizon + distance model (`impact/analyzer.py`) | **OK** |
| Impact probability | `AssetImpactTable.tsx` | `imp.impact_probability` | DB | REAL calculation | From forecast band confidence intersection | **OK** |
| Distance to slick | `AssetImpactTable.tsx` | `imp.distance_to_slick_km` | DB | REAL calculation | Geodesic centroid distance | **OK** |
| Response recommendations | `DecisionSupportPanel.tsx` | API `/recommendations/{track_id}` | DB | REAL calculation | Ranked from risk scores (`decision_support/prioritization.py`) | **OK** |
| Assistant answers | `AssistantChat.tsx` | API `/assistant/query` | DB state ledger | REAL calculation | Intent → SQL retrieval (`assistant/grounded_engine.py`) | **OK** — grounded; enhanced with `IncidentContext` |

---

## Backend Pipeline Data Sources

| Stage | Source File | Input | Output | Mode |
|-------|-------------|-------|--------|------|
| Scene registration | `scene_ingestion.py` | Bbox metadata or GeoTIFF | `SatelliteScene` | DEMO or REAL |
| SAR raster | `demo_sar_generator.py` / `sar_reader.py` | None or file path | sigma0 dB array | DEMO or REAL |
| Preprocessing | `ml/preprocessing/*` | Raw SAR | Normalized tiles | REAL calculation |
| Segmentation | `ml/inference/engine.py` | Tiles | Class mask + probabilities | REAL model inference |
| Polygonization | `geospatial/raster_to_vector.py` | Mask + affine | GeoJSON polygons + area | REAL calculation |
| Temporal tracking | `temporal/tracker.py` | Detections | Kinematics + association | REAL calculation |
| Environmental | `environmental/cmems_adapter.py`, `era5_gfs_adapter.py` | Bbox + time | Currents/wind/stokes | DEMO without credentials |
| Forecast | `forecasting/ensemble.py` | Polygon + forcing | Bands + trajectory | REAL calculation + RANDOM ensemble |
| Impact | `impact/analyzer.py` | Bands × assets | Impact assessments | REAL calculation |
| Risk | `risk/engine.py` | Impact + track state | Risk assessment | REAL calculation |

---

## Known Issues (Pre-Fix)

1. **ForecastControls** displayed hardcoded MetOcean telemetry — not from backend.
2. **RiskWaterfallInspector** had hardcoded fallback factor contributions.
3. **Timeline scrubber** did not change displayed detection or navbar values.
4. **"CONFIRMED OIL SPILL"** overclaimed certainty for unvalidated model output.
5. **Demo case study** used synthetic SAR but real-looking scene names (fixed in prior session).
6. **No `DATA_MODE` central config** — now added.
7. **Environmental adapters** returned demo physics without explicit unavailable state when credentials missing.

---

## Post-Implementation Status

After this phase:

- All scientific values route through FastAPI services with `data_status` metadata.
- `DATA_MODE=DEMO|REAL` controls default pipeline behavior.
- Sentinel-1 GeoTIFF local ingestion path available via `Sentinel1Provider`.
- Temporal scrubber updates observation state from backend timeline endpoint.
- Frontend displays backend-computed MetOcean parameters only.
- Classification labels reflect uncertainty (Potential Oil / Look-Alike Candidate).
