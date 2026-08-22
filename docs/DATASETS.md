# Satellite & Oceanographic Datasets Specification

## 1. Primary Remote Sensing Sensor: Sentinel-1 SAR
- **Constellation Status (2025/2026)**: Sentinel-1A (launched 2014) and Sentinel-1C (launched Dec 2024), with Sentinel-1D (launched Nov 2025) restoring full 6-day tandem repeat coverage.
- **Acquisition Modes**: Interferometric Wide Swath (IW) & Extra Wide Swath (EW).
- **Polarizations**: Dual-polarization VV (vertical transmit, vertical receive) and VH (cross-polarization). VV is the primary channel for oil detection as sea surface capillary and short gravity wave Bragg scattering is strongest in co-polarization.
- **Physical Detection Principle**: Crude oil creates a thin viscoelastic surface film that dampens wind-generated centimeter-scale capillary waves. This reduces radar backscatter, creating a distinct "dark patch" on the SAR image.

---

## 2. Benchmark Datasets for ML Training & Evaluation

### A. Krestenitis Oil Spill Detection Benchmark (Primary)
- **Source**: MKLab / CERTH (Zenodo / Remote Sensing 2019).
- **Format**: 1,002 training tiles and 110 testing tiles cropped at $256 \times 256$ pixels.
- **5-Class Schema**:
  1. `0: sea_surface` — Ambient background sea clutter.
  2. `1: oil_spill` — Ground-truthed mineral oil slick.
  3. `2: look_alike` — Low-wind shadows, biogenic films, algal blooms, rain cells.
  4. `3: ship` — Vessel hard targets exhibiting bright corner-reflector backscatter.
  5. `4: land` — Coastal landmass.

### B. SOS-Sentinel Cross-Domain Test Set
- **Source**: SOS-ALOS / SOS-Sentinel academic benchmark.
- **Role**: Held-out cross-sensor and cross-domain generalization evaluation. Used to quantify the domain shift penalty when transferring models from European to tropical sea states.

---

## 3. MetOcean Hydrodynamic & Meteorological Datasets

| Dataset | Provider | Parameters | Resolution | Operational Role |
|---|---|---|---|---|
| **Global Ocean Physics Analysis & Forecast** | Copernicus Marine Service (CMEMS) | Surface current vectors $(u, v)$, Sea surface temp | 0.083° (~9 km), 1-hour | Primary advection forcing for Lagrangian particle tracking |
| **Global Ocean Waves (MFWAM)** | CMEMS / Meteo-France | Stokes wave drift $(u_s, v_s)$, Wave height $H_s$, Period $T_p$ | 0.083°, 3-hour | Wave-induced transport and surface turbulence |
| **10m Surface Winds** | ECMWF ERA5 (Reanalysis) / NOAA GFS (Operational) | 10m wind velocity $(u_{10}, v_{10})$ | 0.25°, 6-hour | 3% wind leeway drift and SAR look-alike wind speed conditioning |
| **World Database on Protected Areas (WDPA)** | UNEP-WCMC & IUCN | Marine protected areas, IUCN Category I-VI polygons | Vector GeoPackage | Ecological sensitivity weighting in GIS impact layer |
| **Apparent Fishing Effort** | Global Fishing Watch (GFW) | Gridded vessel fishing hours | 1 km grid | Economic exposure scoring for fishery and aquaculture assets |

---

## 4. Documented Real-World Validation Incidents

1. **Ennore Port Oil Spill (Chennai, India, Jan 2017)**:
   - Collision of MT BW Maple and MT Dawn Kanchipuram off Kamarajar Port.
   - Captured by Sentinel-1A pass 1 (Jan 28) and revisit pass 2 (Jan 29).
   - Validated southward drift along the Coromandel coast towards Marina Beach.
2. **Deepwater Horizon (Gulf of Mexico, 2010)**:
   - Massive multi-month Macondo well discharge used for wide-envelope dispersion modeling.
3. **Bohai Sea Offshore Platform Leak (China, 2011)**:
   - Successive SAR multi-pass observations cross-validated against GNOME physical trajectory simulations.
