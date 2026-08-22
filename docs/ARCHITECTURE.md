# Oil Spill Intelligence System — Technical & Scientific Architecture

## 1. System Mission & Core Contribution
The **Oil Spill Intelligence System** is an end-to-end remote sensing decision-support platform designed to transform raw satellite radar (SAR) observations into actionable, explainable, and uncertainty-calibrated marine emergency response guidance.

Unlike basic binary image classifiers, this system unifies:
1. **SAR Radiometric Calibration & Speckle Filtering**: Multiplicative speckle attenuation via spatial Lee filters preserving sharp boundary gradients.
2. **5-Class Semantic Segmentation (DeepLabV3+ / U-Net)**: Discriminating true oil from SAR look-alikes (low-wind zones, biogenic slicks, algal blooms, rain cells) using the benchmark Krestenitis schema.
3. **Geospatial WGS84 Reconstruction**: Polygonization, geometric topology repair, and exact geodetic area computation using the WGS84 ellipsoid ($pyproj.Geod$).
4. **Temporal Kinematics & Hungarian Multi-Pass Association**: Multi-date slick tracking, calculating displacement velocity, heading, growth rate, and classifying physical evolution (*Expansion, Contraction, Fragmentation, Persistence, Disappearance*).
5. **MetOcean Hydrodynamic Forcing**: Surface current assimilation from Copernicus Marine Service (CMEMS) and 10m surface winds from ECMWF ERA5 / NOAA GFS.
6. **Lagrangian Monte Carlo Trajectory Forecasting**: Simulating hydrodynamic advection ($u_{\text{current}} + 0.03 \cdot \mathbf{R}(15^\circ) u_{\text{wind}} + u_{\text{Stokes}} + \text{Diffusion}$) with 50-member perturbation ensembles generating 50%, 80%, and 95% containment envelopes over 6h, 12h, 24h, and 48h horizons.
7. **GIS Asset Exposure & Impact Intersection**: PostGIS spatial intersection against sensitive coastal assets (Marine Protected Areas WDPA, high-density fisheries/aquaculture, ports, beaches, mangrove wetlands, and coastal communities).
8. **Explainable 6-Factor Risk Engine**: A transparent, inspectable risk formula decomposed into *Impact Probability, Asset Severity, Proximity Decay, Slick Expansion, Forecast Uncertainty, and Economic Exposure*.
9. **Response Prioritization & Decision Support**: Advisory containment boom staging, aerial verification patrols, and satellite retasking recommendations with non-autonomous safety boundaries.
10. **Grounded AI Assistant**: Strict database retrieval-grounded conversational agent with zero hallucination and clickable geospatial citations.

---

## 2. Pipeline Sequence Diagram

```
+-------------------------------------------------------------------------+
| SATELLITE OBSERVATION (Sentinel-1 SAR IW Dual-Pol VV/VH)                 |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| RADIOMETRIC CALIBRATION & LEE FILTER DESPECKLING                        |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 5-CLASS SEMANTIC SEGMENTATION (DeepLabV3+ with ASPP & Low-Level Proj)   |
| [Sea Surface=0, Oil Spill=1, Look-Alike=2, Ship=3, Land=4]              |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| WGS84 GEODETIC VECTORIZATION (Exact Area in km², BBox, Centroid)        |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| MULTI-TEMPORAL HUNGARIAN ASSOCIATION (Track Identity & Kinematics)     |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| METOCEAN ENVIRONMENTAL FUSION (CMEMS Currents + ERA5/GFS 10m Winds)     |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| LAGRANGIAN MONTE CARLO ENSEMBLE FORECASTING (6h, 12h, 24h, 48h Bands)   |
| 50% Best Guess  |  80% Standard Envelope  |  95% Minimum Regret GNOME   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| GIS ASSET INTERSECTION & IMPACT WINDOWS (Arrival Time, Distance, Prob)  |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| EXPLAINABLE 6-FACTOR RISK ENGINE & AHP DECOMPOSITION                    |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| RESPONSE PRIORITIZATION & MONITORING DECISION SUPPORT                   |
+-------------------------------------------------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+------------------------------------+    +-------------------------------+
| FASTAPI STATE LEDGER & REST API   |    | GROUNDED AI ASSISTANT         |
+------------------------------------+    | (DB-Constrained Citations)    |
            |                             +-------------------------------+
            v                                               |
+-----------------------------------------------------------+-------------+
| REACT + MAPLIBRE/LEAFLET GIS INTELLIGENCE DASHBOARD                     |
+-------------------------------------------------------------------------+
```

---

## 3. Database State Ledger Schema
The PostgreSQL/PostGIS (and local SQLite fallback) schema stores all observations and states immutably:
- `satellite_scenes`: Ingested SAR scenes with WGS84 bounding polygon footprints.
- `observations`: Preprocessing version metadata, tile grids, and noise profiles.
- `spill_detections`: Extracted polygons with calibrated confidence, look-alike confusion index, and circularity morphology.
- `tracked_slicks`: Persistent slick identity tracked across repeat satellite passes.
- `temporal_observations`: Advection-compensated matching nodes storing $\Delta \text{Area}$, displacement vector, and state classification.
- `environmental_snapshots`: Cached CMEMS current fields, GFS winds, and Stokes wave drift with vintage timestamps.
- `forecast_runs`: Monte Carlo simulations with physical transport parameters.
- `forecast_bands`: 50%, 80%, and 95% containment polygon envelopes per forecast horizon.
- `assets`: WDPA Marine Protected Areas, Ramsar wetlands, fisheries effort, and ports.
- `impact_assessments`: Spatiotemporal intersection results with time-to-impact counters.
- `risk_assessments`: Decomposed 6-factor risk evaluations and textual justifications.
- `response_recommendations`: Operational decision-support guidance for response coordinators.
