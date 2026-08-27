# SYSTEM AUDIT

**Date:** 2026-08-24

## Pipeline Trace
1. **Frontend Search:** The user searches via `IncidentLocationControl` in `App.tsx`.
2. **Backend Entry:** Hits `/api/v1/location/analyze` in `backend/app/api/v1/endpoints/incidents.py`.
3. **Geocoding:** Works via `NominatimGeocodingProvider`.
4. **Satellite Search:** Handled by `CDSEClient.search_sentinel1()`. Works if credentials are provided in `.env`.
5. **Asset Download:** Attempts to download quicklook via `CDSEClient.download_quicklook()`. Currently failing/404ing or skipping if unavailable.
6. **Slick Processing:** Uses `detect_dark_spot_candidates()`. Skipped/Unavailable if the quicklook download fails.
7. **AIS/Vessels:** Handled by `AISClient`. Currently returns "LIVE VESSEL DATA UNAVAILABLE" because credentials are missing.
8. **Infrastructure:** Uses OSM provider.
9. **Source Attribution / Hindcast:** Uses `estimate_source_zone()`. Currently fails if weather/current data is missing.
10. **Frontend Display:** Map layers and `IntelligencePanel` are updated using the returned flat payload.

## Current Blockers & Missing Data
- **Satellite Quicklook:** The `quick-look.png` path might not be reliable on CDSE.
- **AIS Data:** No API key configured.
- **Weather Data:** Copernicus Marine credentials missing.
- **Real data fallbacks:** When real data fails, the system correctly falls back to "UNAVAILABLE" messages instead of inventing data, adhering to C1/C3.
