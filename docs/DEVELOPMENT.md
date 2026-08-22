# Development & Contribution Guide

## 1. Project Organization
- `backend/app/core/`: Configuration, structured logging, custom error hierarchies.
- `backend/app/database/`: SQLAlchemy 2.0 ORM models, session lifecycle, SQLite / PostGIS support.
- `backend/app/schemas/`: Pydantic models for validation and OpenAPI generation.
- `backend/app/ml/`:
  - `models/`: DeepLabV3+ with ASPP and U-Net PyTorch implementations.
  - `preprocessing/`: Radiometric calibration to sigma0 dB, Lee speckle filter, windowed tiling with Hann blending.
  - `training/`: Combined Cross-Entropy + Soft Dice training loop.
  - `evaluation/`: Per-class IoU, Dice/F1, Confusion Matrix, and Look-alike False Positive Rate.
- `backend/app/geospatial/`: Projections, affine transform, exact WGS84 geodetic area ($pyproj.Geod$), polygon cleanup, GeoJSON serialization.
- `backend/app/temporal/`: Multi-pass Hungarian tracker, kinematics (drift speed km/h, heading, growth rate), and evolution state classification.
- `backend/app/environmental/`: CMEMS current & wave adapters, ERA5/GFS 10m wind adapters.
- `backend/app/forecasting/`: Lagrangian hydrodynamic advection engine ($u_{\text{current}} + 0.03 \cdot \mathbf{R}(15^\circ) u_{\text{wind}} + u_{\text{Stokes}} + \text{Diffusion}$), 50-member Monte Carlo ensemble, 50%/80%/95% containment envelopes.
- `backend/app/assets/`: Marine Protected Areas (WDPA), fisheries, ports, beaches, wetlands registry.
- `backend/app/impact/`: Spatiotemporal intersection between forecast bands and assets, arrival windows, exposure levels.
- `backend/app/risk/`: Decomposed 6-factor risk formula, AHP weighting, sensitivity analysis.
- `backend/app/decision_support/`: Priority response guidance and monitoring recommendations.
- `backend/app/assistant/`: Strict DB-grounded natural-language query engine with provenance citations.
- `frontend/src/`:
  - `components/`: MapDashboard, TimelinePanel, ForecastControls, RiskWaterfallInspector, AssetImpactTable, DecisionSupportPanel, AssistantChat, Navbar.
  - `services/`: API client for all backend endpoints.
  - `types/`: Full TypeScript interface definitions.

---

## 2. Coding Guidelines
- **Zero Hallucination**: Never invent model metrics, satellite observations, or risk scores.
- **Geospatial Rigor**: Never calculate area from degrees squared. Always use geodesic ellipsoid calculations.
- **Non-Autonomous Disclaimer**: All decision-support recommendations must carry explicit advisory warnings.
