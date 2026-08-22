# AI-Powered Satellite Oil Spill Intelligence, Forecasting, Impact Assessment & Response Decision-Support System

**Research & Architecture Document — v1.0**
Prepared as a pre-implementation design study (no application code included).

---

## PART 1 — PROBLEM DEFINITION

### 1.1 Operational problem
Coastal states and response agencies need to know, within minutes to hours of a suspected slick appearing on radar: *is it oil, how big is it, where is it going, what will it hit, and what should be checked first.* Today this chain is split across disconnected tools and people. The closest operational analogue, EMSA's **CleanSeaNet**, tasks SAR imagery, has trained analysts visually confirm slicks, and issues an alert with location, estimated area, and a confidence level — but it stops at detection/identification. Trajectory forecasting, ecological-asset intersection, and prioritized response guidance are done separately (if at all), often manually, using tools like NOAA's GNOME that are not integrated with the detection step. There is no single, open system that carries an observation from "pixel" to "prioritized, explainable decision."

### 1.2 Technical problem
This is a **multi-stage, spatio-temporal, uncertainty-propagating inference problem**, not a single model:
- Stage 1 output (segmentation mask) is Stage 2's input (temporal association).
- Stage 2 output (a tracked object with a velocity estimate) is Stage 3's input (forecasting), which itself must fuse three independent forecast systems (wind, currents, waves) each with their own error characteristics.
- Stage 3's *distribution* of possible futures (not a single line) drives Stage 4 (GIS intersection against static/semi-static asset layers).
- Every upstream error (a missed pixel, a mis-associated blob, a bad current field) compounds downstream. A system that reports a single risk number without carrying uncertainty through every stage is not scientifically honest.

### 1.3 Research problem
Two problems remain genuinely open in the literature: (1) **discriminating true oil from SAR look-alikes** (biogenic slicks, low-wind zones, rain cells, current shear, algal mats) with calibrated confidence rather than a hard label, and (2) **multi-scene temporal association and forecasting under scarce ground truth** — almost all published SAR oil-spill work operates on single, independent scenes; very little addresses tracking the same slick across repeat passes or forecasting its future shape with quantified uncertainty.

### 1.4 Why simple "spill / no spill" classification is insufficient
A binary classifier answers one question and generates zero of the thirteen things a response coordinator actually needs: location precision, area, boundary geometry, direction of travel, time-to-coast, which asset is threatened first, how confident the system is, and what changed since the last look. Classification is a necessary first component, not a system.

### 1.5 What this system contributes beyond existing systems
Nothing here is claimed to be a new physical model or a new detection algorithm — those exist and are mature (Section 2). The contribution is **integration and explainability**: a single, reproducible, open pipeline that (a) segments at pixel level rather than classifying whole scenes, (b) associates detections through time, (c) forecasts with a physics-based particle model rather than an unvalidated learned trajectory model, (d) intersects forecasts against real open asset layers (protected areas, coastlines, fisheries), (e) computes a transparent, inspectable risk score instead of an opaque one, and (f) exposes all of it through a natural-language layer that is *grounded* in the system's own stored outputs. CleanSeaNet does (a)–partially and is not open; academic papers each address one of (a)–(e) in isolation; nobody publicly combines all of them with an explanation layer on top. That combination — not any single algorithm — is the contribution.

---

## PART 2 — STATE OF THE ART

### 2.1 SAR oil-spill detection & segmentation
- **Classical era**: adaptive/CFAR thresholding and texture (GLCM) features on dark-spot candidates, followed by rule-based or SVM look-alike discrimination. Still used as a fast pre-filter in some operational chains.
- **Deep learning era, whole-image classification**: early CNNs classified entire tiles as oil/no-oil — now considered obsolete for anything beyond triage, since it can't give geometry.
- **Semantic segmentation (current standard)**: the field-defining benchmark is <cite index="8-1">Krestenitis et al. (2019), who introduced a publicly available Sentinel-1 SAR dataset for oil spill detection and showed that DeepLabv3+ achieved the best test-set accuracy and inference time among well-known DCNN segmentation models evaluated on it</cite>. This established segmentation, not classification, as the correct problem framing, and DeepLabv3+/U-Net as reasonable baselines.
- **Data-scarcity mitigation**: because real spill imagery is rare, recent work uses GAN-based synthetic data generation, diffusion-based augmentation with soft-label knowledge distillation, and cross-domain/synthetic label-to-SAR generation to fight the chronic shortage of labeled positives.
- **Attention & multi-task refinement**: multi-task networks that jointly classify and segment (reducing false positives from look-alikes) and attention-augmented U-Net variants (e.g., residual + channel/spatial attention blocks) report meaningful gains on edge quality and look-alike suppression over plain U-Net/DeepLab baselines.
- **Foundation-model adaptation**: the most recent direction (2024) adapts the Segment Anything Model (SAM) to this domain — an object detector proposes boxes, an adapter-tuned SAM produces masks, and a fusion module resolves category conflicts, surpassing prior segmentation-only pipelines on the standard benchmark. This is state-of-the-art but heavier and less mature/reproducible than DeepLabv3+/U-Net.
- **Cross-domain generalization** (geographic domain shift) is explicitly flagged in 2025 literature as still unsolved: models trained on the mostly-European benchmark data degrade on other regions' sea states and SAR incidence geometries.

### 2.2 Look-alike discrimination
Still the central open difficulty. Oil and look-alikes (biogenic films, low-wind "wind shadow" zones, rain cells, current fronts/shear zones, upwelling, algal blooms) both dampen Bragg scattering and appear dark. No single feature reliably separates them; the field relies on combinations of shape/texture descriptors, context (wind speed at acquisition time, proximity to shipping lanes/platforms), and — where available — dual-polarization ratio information. Datasets that explicitly label a "look-alike" class (as opposed to just "sea") are what make training a discriminative model possible at all, which is why dataset choice matters more than architecture choice here.

### 2.3 Temporal, multi-date monitoring
This is the thinnest part of the literature. Individual scenes are analyzed independently in almost all published work; genuine multi-pass tracking of the *same* slick (association, not just repeated detection) is rare in the deep-learning literature and mostly appears as case studies (e.g., manual tracking of the 2011 Bohai Sea/Penglai spill across successive SAR passes cross-validated against the GNOME physical model). This is a legitimate area where an engineering contribution (not a novel algorithm — classical tracking-by-detection is well understood in computer vision generally) is genuinely missing from the oil-spill-specific literature.

### 2.4 Trajectory forecasting
Two mature, **operational** physics-based tools already exist and should be reused, not reinvented:
- **NOAA GNOME** — the U.S. federal government's spill trajectory model, in active use since the late 1990s, distributed as open-source Python (**PyGNOME**). It characteristically produces both a "best guess" trajectory and a "minimum regret" (conservative, wider-spread) envelope rather than one deterministic line — i.e., it is uncertainty-aware by design. Multiple published case studies (Persian Gulf, Bohai Sea, Bandar Abbas, North Sea) validate GNOME trajectories against actual SAR-observed spill extents, including a documented case where GNOME driven by forecast ocean currents *underestimated* spread relative to Sentinel-1A observations — an important, honest calibration data point.
- **OpenDrift** (Norwegian Meteorological Institute) — an open-source, Python, Lagrangian particle-tracking framework with a dedicated, ready-made **oil drift module** ("OpenOil"), built for exactly this problem, in daily operational use for Norwegian emergency preparedness, and validated to run millions of particles on a laptop.

Given these exist, mature, open-source, and validated, **building a custom deep trajectory-forecasting model from scratch instead of using OpenDrift/PyGNOME would be a weaker engineering decision, not a stronger one** for anything short of a multi-year research program: the training data needed to out-predict decades-old physics (real, ground-truthed spill trajectories) simply does not exist in usable volume. Pure sequence models (LSTM/transformer trajectory prediction) appear in the literature almost entirely for *vessel* trajectory prediction (dense AIS data, millions of tracks) — that data abundance does not exist for oil slicks. The credible research contribution in this part of the system is a **hybrid**: physics-based particle advection as the backbone, with a learned residual-correction or ensemble-weighting layer trained on the (small) set of validated case studies, and Monte Carlo perturbation of the forcing fields to produce a genuine probability envelope instead of a single line.

### 2.5 Environmental impact assessment
Precedent exists for exactly this kind of layered impact analysis: a published Persian Gulf decision-support system couples **GNOME with Copernicus Marine (CMEMS) and ECMWF met-ocean forcing**, converts trajectory output into concentration/time-of-impact fields, and derives two explicit indices — an **Emergency Response Priority Number (ERPN)** and a **Risk Index (RI)** — for response planning. A separate Malaysia study built a GNOME-driven "environmental vulnerability" map intersecting spill trajectories against biological/socio-economic/shoreline resource layers across seasons. These are strong templates: this system's risk/impact layers should follow the same "physics model → asset intersection → explicit index" pattern rather than inventing a new methodology.

### 2.6 GIS-based emergency response
CleanSeaNet is the reference *operational* system (Europe-wide, EMSA-run since 2007, SAR-based, alerts within ~30 minutes of image acquisition, includes wind/met-ocean context and optional very-high-resolution optical follow-up) — but it is a closed, institutional, detection-and-alerting service, not an open research platform, and it does not publish forecasting or ecological-risk scoring as part of the public service description.

### 2.7 Digital twins for environmental monitoring
This is a genuinely nascent area — mostly conceptual/position papers on "digital twin ocean/Earth" initiatives, with very few concrete, narrow implementations. There is **no established, standard architecture** for an oil-spill digital twin to benchmark against. This is real white space, but it should be scoped modestly (Part 11): a true digital twin implies continuous bidirectional sync with the physical system, which is not achievable when the primary sensor (Sentinel-1) only revisits a given area every 6 days in routine tasking (currently two operational satellites, 1A and 1C, with 1D launched Nov 2025 to gradually replace 1A — see Part 3). What is achievable and honest to call a "digital-twin-like" architecture is a versioned, replayable state ledger, not a live simulation.

### 2.8 Multimodal geospatial AI
An emerging general trend (foundation models that reason jointly over imagery, tabular, and text data, and natural-language geospatial assistants) but with very few deployed examples specific to disaster response, and none found specific to oil spills. The NL assistant designed in Part 10 sits in this space but is deliberately scoped as a **grounded retrieval/reporting layer over the system's own database**, not a model that reasons freely over raw imagery — this avoids the single biggest failure mode (hallucination) at the cost of some flexibility, which is the right trade for a safety-relevant tool.

### 2.9 Classification summary

| Category | Examples |
|---|---|
| **Established technology** — reuse, don't reinvent | Sentinel-1 access (Copernicus Data Space Ecosystem); DeepLabv3+/U-Net SAR segmentation; PyGNOME and OpenDrift/OpenOil physics-based trajectory modeling; Copernicus Marine (CMEMS) current/wave forecasts; WDPA protected-area layers |
| **Research opportunity** (genuinely open) | Calibrated look-alike discrimination; multi-scene temporal association with uncertainty; hybrid physics+ML trajectory correction with proper probabilistic calibration; grounded (non-hallucinating) NL explanation of a live geospatial risk pipeline |
| **Engineering contribution** (valuable, not novel) | Wiring SAR → segmentation → tracking → OpenDrift → GIS asset intersection → transparent risk score → dashboard → grounded assistant into one coherent, reproducible, open pipeline with a real database and API |
| **Potentially novel combination** | An end-to-end, open, uncertainty-propagating pipeline from raw SAR pixels to a natural-language-explained, asset-grounded risk score — not found as a single system in the reviewed literature or in any public operational service |

---

## PART 3 — DATASET STRATEGY

### 3.1 Positive/negative training data for segmentation

| Dataset | Source | License | Spatial res. | Content | Format | Access | Use |
|---|---|---|---|---|---|---|---|
| **Oil Spill Detection (OSD) / Krestenitis benchmark** | MKLab / CERTH (Zenodo) | CC-BY (open, published with the 2019 *Remote Sensing* paper) | Sentinel-1, tiles cropped to 256×256 (from 650×1250 originals) | <cite index="2-1">1,002 training and 110 testing images across five pixel-level classes: oil-spill, look-alike, land, ship, sea surface</cite> | GeoTIFF / PNG masks | Direct download (Zenodo) | **Primary** segmentation training/eval set — the field's de facto benchmark |
| **Deep-SAR Oil Spill (SOS)** | Academic release (SOS-ALOS + SOS-Sentinel) | Research use (verify license on release page before redistribution) | 256×256 crops from 21 raw scenes | <cite index="2-1">8,070 labeled images total — 3,101/776 train/test on ALOS PALSAR, 3,354/839 train/test on Sentinel-1A</cite> | PNG/TIFF pairs | Paper/repo download | Cross-sensor generalization testing; secondary training/augmentation source |
| **Raw Sentinel-1 GRD/SLC scenes** | Copernicus Data Space Ecosystem (ESA/EU) | Free, open, registration required | IW mode ~5×20 m (20 m after multilooking), EW mode ~20-40m | C-band VV/VH (dual-pol over most ocean areas) | SAFE / GeoTIFF via Sentinel Hub API | REST API / OData / STAC + Sentinel Hub API | Unlabeled scenes for (a) inference demos, (b) self-supervised pretraining, (c) building your own difficult-negative bank from known clean/look-alike areas |
| **Difficult negatives (biogenic slicks, wind shadows, algal blooms)** | Curated subset of the above, cross-referenced with known low-wind days (via CMEMS/ERA5 wind fields) or documented algal bloom events | Same as source imagery | — | Manually or semi-automatically flagged "look-alike" scenes not already in Krestenitis | — | Manual curation | Hardest, most valuable class for reducing false positives — budget real time for this |

**Design decision**: build the segmentation pipeline around the Krestenitis 5-class schema (it *already* separates look-alikes from sea and from true oil, which is exactly the discrimination problem in Section 2.2) rather than inventing a new label taxonomy. Use SOS-Sentinel as a held-out cross-domain test set to honestly report generalization gap (Part 16).

### 3.2 Environmental/oceanographic forcing data

| Dataset | Source | License | Res. (space / time) | Variables | Format | Access | Use |
|---|---|---|---|---|---|---|---|
| **Global Ocean Physics Analysis & Forecast** | Copernicus Marine Service (CMEMS) | Free, registration, cite per SLA | ~0.083° (~9 km) / daily, hourly means | Ocean currents (u,v), sea surface temp, salinity | NetCDF via `copernicusmarine` Python toolbox | Python client / OPeNDAP | Advection forcing for OpenDrift/GNOME |
| **Global Ocean Waves Analysis & Forecast** | CMEMS (Meteo-France MFWAM model) | Free, same SLA | ~0.083° (1/12°) / 3-hourly, 10-day forecast | Significant wave height, period, direction, Stokes drift | NetCDF | `copernicusmarine` client | Wave/Stokes-drift forcing (affects surface transport, weathering) |
| **Surface wind** | ECMWF ERA5 (reanalysis, for training/backtests) + operational GFS or CMEMS scatterometer winds (for live forecasts) | Free (ERA5 via Copernicus Climate Data Store); GFS fully open (NOAA) | ERA5 ~0.25° hourly; GFS ~0.25° 6-hourly, 16-day forecast | 10 m u/v wind | GRIB/NetCDF | CDS API / NOMADS | Wind-drift forcing for OpenDrift; also used to flag low-wind "look-alike-prone" acquisitions |
| **Coastline / land mask** | OpenStreetMap coastline extract or Natural Earth | ODbL / public domain | Vector, high detail | Polygons | Shapefile/GeoJSON | Direct download | Land mask for particle beaching logic; asset-proximity baseline |
| **Protected areas** | World Database on Protected Areas (WDPA / Protected Planet, UNEP-WCMC & IUCN) | Free for non-commercial/research use (check WDPA terms for exact redistribution conditions) | Vector polygons, monthly updates | IUCN category, marine flag, area | Shapefile/GeoPackage/GeoJSON | Direct download or `wdpar` client pattern | Ecological-sensitivity asset layer |
| **Fishing/vessel activity** | Global Fishing Watch (AIS-derived apparent fishing effort) | CC-BY-SA (gridded effort products) | ~1 km grid / daily (historical products; API for near-real-time) | Fishing hours by gear type | Raster (GeoTIFF-like) / API | Public API (registration) | Fisheries-exposure asset layer |
| **Bathymetry** | GEBCO | Public domain | ~450 m global grid | Depth | NetCDF/GeoTIFF | Direct download | Context for weathering/dispersion assumptions, shallow-water risk flagging |

### 3.3 Sentinel-1 access specifics (important, and time-sensitive)
As of this document's writing, the operational Sentinel-1 constellation consists of **Sentinel-1A** (launched 2014, well beyond design life) and **Sentinel-1C** (launched Dec 2024), with **Sentinel-1D** launched Nov 2025 specifically to replace the aging 1A and restore a full two-satellite tandem. Sentinel-1B was permanently lost in 2021. **Design implication**: routine repeat coverage of a given area is on the order of 6 days in tandem configuration, not the 6-day *single-satellite* cadence some older documentation assumes — verify current constellation status at acquisition time rather than hardcoding a revisit assumption, since it has changed twice in the last two years and will change again as 1D fully takes over from 1A.

### 3.4 Dataset structure (proposed)
```
data/
  raw_scenes/            # unprocessed Sentinel-1 SAFE products, by scene_id
  segmentation/
    krestenitis/          # primary benchmark, unmodified splits preserved
    sos_sentinel/          # cross-domain eval only, never mixed into train
    curated_negatives/      # manually flagged hard look-alikes
  environmental/
    currents/  waves/  wind/     # NetCDF, partitioned by date
  assets/
    protected_areas.gpkg  coastline.gpkg  fisheries/  bathymetry.tif
  case_studies/            # a handful of real, documented spills (location,
                            # date, SAR scenes, reported extent) used to
                            # validate the trajectory + risk pipeline end-to-end
```
Keep `krestenitis` train/test splits exactly as published — re-splitting them yourself breaks comparability with every paper that reports numbers on this benchmark (Part 16 depends on this).

---

## PART 4 — ML ARCHITECTURE

### 4.1 Task framing
Pixel-level **semantic segmentation**, 5 classes (sea surface, oil spill, look-alike, ship, land), matching the Krestenitis schema — not binary classification, not pure object detection.

### 4.2 Candidate architectures compared

| Architecture | Strengths here | Weaknesses here | Verdict |
|---|---|---|---|
| **U-Net (ResNet/EfficientNet encoder)** | Simple, well-understood, strong on limited data, fast to train on a single GPU, easy to debug/explain in a thesis | Weaker global context than dilated/pyramid methods; can blur long, thin slick boundaries | **Baseline #1** — always report this number |
| **DeepLabv3+** | Directly validated as best-performing on the exact benchmark dataset in the field-defining paper; atrous spatial pyramid pooling captures the elongated, multi-scale geometry of real slicks better than plain U-Net | Slightly heavier, more hyperparameters (atrous rates, output stride) | **Primary baseline / default model** |
| **U-Net++** | Nested skip connections modestly improve boundary precision over U-Net | Marginal gain for real added complexity at this data scale | Optional ablation, not required |
| **SegFormer / transformer segmentation** | Strong global context, good published results generally | Needs more data / careful augmentation to avoid overfitting on ~1,000 training images; heavier to train and explain; less proven specifically on this benchmark | Stretch goal for Version C only (Part 20) |
| **YOLOv8 (detect) + adapted SAM** | Current state-of-the-art mIoU on the benchmark via the 2024 SAM-OIL approach; box-first framing may help separate touching ship/oil/look-alike regions | Two-stage system, more moving parts, SAM adapter tuning is nontrivial, less transparent for a thesis defense, heavier inference | Stretch goal for Version C only — cite as the SOTA ceiling to compare against, not the thing to ship first |
| **Full multimodal fusion (SAR + optical + AIS)** | Optical bands add color/texture cues when cloud-free | Optical is frequently unusable exactly when spills are most likely (storms → cloud cover; SAR's whole advantage is working through cloud) — fusing modalities that are rarely co-available adds complexity without reliable benefit | **Rejected** as a baseline; keep as an opportunistic enrichment only when a cloud-free Sentinel-2 scene happens to coincide |

### 4.3 Selected baseline and justification
**DeepLabv3+ with a ResNet-34 or ResNet-50 encoder, pretrained on ImageNet, fine-tuned on Krestenitis at 256×256 tiles** is the recommended primary model:
- It is the architecture the benchmark's own authors found best-performing on this exact data — the strongest available prior for "what will actually work here" rather than a generic ImageNet-leaderboard argument.
- It trains in hours, not days, on a single consumer/free-tier GPU (Part 17), which matters for a student timeline.
- It is explainable (Grad-CAM/attention overlays are standard and easy to generate) — important since Part 10's assistant needs to describe *why* a detection was made.
- U-Net trains alongside it as a cheap baseline for comparison; SegFormer/SAM-OIL are documented as the SOTA ceiling to reference in the write-up, not blockers to a working system.
- **Do not** default to the largest/newest model "because it's 2026" — the benchmark's own controlled comparison already answered this question for this exact data regime, and small-data segmentation is precisely where architecture size stops helping and starts hurting (overfitting on ~1,000 training tiles).

### 4.4 Pipeline around the model
Preprocessing: calibration (radiometric, to sigma-nought) → speckle filtering (Lee or refined-Lee, or a learned denoiser as an ablation) → land masking → tiling with overlap → normalization. Postprocessing: morphological cleanup of predicted masks, polygonization (rasterio/shapely), minimum-area filtering to suppress speckle-scale false positives, and a **calibrated confidence score per polygon** (e.g., mean softmax probability over the polygon, or Monte-Carlo dropout variance) — this confidence is what Parts 8–10 consume; do not discard it after inference.

---

## PART 5 — TEMPORAL INTELLIGENCE

### 5.1 What "temporal intelligence" means here
Given segmentation outputs (polygons + confidence) from multiple passes over the same area, determine: is polygon B in scene *t+1* the same physical slick as polygon A in scene *t*? If yes, how has it changed (grown, shrunk, split, moved, disappeared)?

### 5.2 Association algorithm
This is a well-understood computer-vision problem (multi-object tracking), not one needing a novel algorithm:
1. **Candidate matching** between consecutive detections using a cost function combining: IoU of forecast-advected polygon (advect polygon A forward by the elapsed time using the *same* current/wind fields from Part 6, then compare to polygon B — not naive spatial overlap, since slicks move between passes) + centroid distance + area-ratio penalty.
2. **Assignment** via the Hungarian algorithm on the cost matrix (standard, exact, cheap at this scale — dozens of polygons per scene, not thousands).
3. **State classification** per matched/unmatched pair:
   - **Expansion/contraction**: area(t+1)/area(t) ratio beyond a threshold.
   - **Movement**: centroid displacement vector, converted to a drift speed/bearing, cross-checked against the physics-predicted displacement (large disagreement is itself a useful QA signal — flag for analyst review).
   - **Fragmentation**: one polygon at *t* matches multiple polygons at *t+1* (split assignment).
   - **Persistence vs. disappearance**: a polygon with no viable match — check confidence and cloud/incidence-angle metadata before concluding "disappeared" vs. "not re-observed" vs. "below detection threshold" (evaporation/dispersion is real, but so is a bad look angle).
4. **Rate of change**: store as a time series per tracked slick ID (area, centroid, mean confidence) — this is exactly what Part 10's assistant needs to answer "what changed since yesterday."

### 5.3 Honesty about coverage
Given ~6-day routine revisit (Part 3.3), most "temporal intelligence" for a real incident will rely on **emergency tasking** (multiple acquisitions within 24-48h during an active response, as CleanSeaNet does) rather than routine passes. Design the tracker to work correctly with irregular, sparse timestamps — do not assume evenly spaced observations.

---

## PART 6 — TRAJECTORY FORECASTING

### 6.1 Approach comparison

| Approach | Verdict for this project |
|---|---|
| Pure numerical/advection via **OpenDrift (OpenOil module)** or **PyGNOME** | **Adopt as the core engine.** Both are open-source, Python-integrable, operationally validated (Part 2.4), and already implement oil-specific weathering (evaporation, dispersion, emulsification) that a from-scratch model would take a full research program to reproduce credibly. |
| Pure ML (LSTM/transformer trajectory regression) | **Reject as primary approach.** No sufficient volume of ground-truthed real spill trajectories exists to train a competitive learned model; the closest analogous data-rich domain (AIS vessel tracks) does not transfer, since oil transport physics (wind drag factor, Stokes drift, weathering-dependent buoyancy) differs fundamentally from powered vessel motion. |
| **Hybrid physics + ML residual correction** | **Adopt as the research-grade extension.** Run OpenDrift as the backbone; where validated case studies exist (Part 3.4 `case_studies/`), train a small model to correct systematic bias (e.g., the documented GNOME under-prediction of spread when using forecast vs. analyzed currents) rather than to predict trajectories from scratch. This is realistic in scope and is a genuine, honest contribution. |
| Ensemble/Monte Carlo perturbation of forcing fields | **Adopt for uncertainty quantification** — run N particle-tracking realizations with perturbed wind/current fields (within their known forecast-error bounds) instead of one deterministic run; the spread of realizations *is* the uncertainty envelope. This directly mirrors GNOME's own "best guess vs. minimum regret" design philosophy (Part 2.4), generalized to a full probability field instead of two bounding cases. |

### 6.2 Forecast horizons and honest accuracy expectations
Produce 6h / 12h / 24h / 48h forecasts as requested, but **do not promise uniform accuracy across horizons** — met-ocean forecast skill (wind and current forecasts feeding the model) degrades with lead time, and this degradation should be *visible* in the output, not hidden:

| Horizon | Primary uncertainty driver | Expected qualitative reliability |
|---|---|---|
| 6h | Initial polygon geometry/position error, short-range wind forecast | Highest confidence; envelope should be tight |
| 12h | Compounding current-field forecast error | Good, moderate envelope growth |
| 24h | Current + wind forecast error accumulation, weathering uncertainty | Meaningful spread; treat point predictions as indicative, not precise |
| 48h | Compounding of all of the above + forecast-model own skill decay at CMEMS/GFS lead times | Wide envelope; communicate this explicitly as low-confidence guidance, not a forecast to plan cleanup logistics around alone |

### 6.3 Output format
Never output a single polyline. Output a **probability raster or a set of confidence-banded polygons** (e.g., 50%/80%/95% containment contours from the Monte Carlo ensemble) for each horizon, plus the deterministic "best guess" and "conservative/minimum regret" bounding cases in the GNOME tradition, so downstream consumers (Parts 7–10) always have both a headline answer and its uncertainty.

---

## PART 7 — IMPACT ANALYSIS

### 7.1 Asset layers (Part 3.2 sources)
Coastline, protected marine areas (WDPA), fisheries/aquaculture effort (Global Fishing Watch + any nationally available aquaculture registries), ports (OpenStreetMap POI extract or national AIS-derived port polygons), beaches, wetlands/mangroves (Global Mangrove Watch, if in scope), ecologically sensitive zones, and populated coastal segments (population-weighted coastline, e.g., via a gridded population product clipped to a coastal buffer).

### 7.2 Method: intersect the *probability field*, not just the deterministic line
Following the precedent in Part 2.5 (GNOME+CMEMS+ECMWF DSS producing concentration/time-of-impact fields), the impact layer should:
1. For each forecast horizon, spatially join the confidence-banded polygons (Part 6.3) against each asset layer using PostGIS `ST_Intersects`/`ST_Distance`.
2. For each asset touched, compute: probability of impact (from which confidence band it falls in), estimated time-to-impact (earliest horizon at which the asset enters any band), and exposure duration if computable.
3. Store per-asset, per-forecast-run results — this is what makes "why is this asset high risk" (Part 10) answerable from stored data rather than re-derived on the fly.

### 7.3 Honesty constraint
Static asset layers (WDPA, coastline) go stale slowly and are fine to cache; fisheries/vessel-effort layers are more dynamic and should be timestamped with their own data vintage in every output, since "no fishing activity shown" in a 2017-vintage historical layer is not the same claim as "no fishing activity now."

---

## PART 8 — RISK ENGINE

### 8.1 Why not a black-box learned risk score
A single AI-generated number with no visible formula fails the core requirement of a response-support tool: an analyst must be able to say *why* to a commander, a court, or a journalist. Precedent (Part 2.5) already exists for a transparent formula-based index (ERPN/RI) — follow that pattern.

### 8.2 Proposed transparent structure
A **weighted, factor-decomposed score**, not a neural network:

```
Risk(asset, horizon) =
    w1 · P(impact | asset, horizon)              [from Part 7 forecast intersection]
  + w2 · ImpactSeverity(asset_type)               [static lookup: e.g., protected area > open coast]
  + w3 · Proximity(asset, current_slick_edge)      [decays with distance]
  + w4 · ExpansionRate(slick)                      [from Part 5 temporal tracking]
  + w5 · (1 − ForecastConfidence(horizon))         [uncertainty penalty — an uncertain,
                                                      fast-approaching threat is treated
                                                      as higher-priority-to-monitor, not
                                                      lower-priority, even though we are
                                                      less sure]
  + w6 · EconomicExposure(asset)                    [fisheries effort density, population]
```
Each term is independently computable, independently inspectable, and independently pulled from a stored table (Part 13) — an analyst or the assistant (Part 10) can always decompose a score back into its terms. Weights (w1..w6) should be set via a documented, defensible process (e.g., analytic hierarchy process with domain-expert input, or simple sensitivity analysis) rather than tuned to make output numbers "look right" — and the weight-setting rationale belongs in the thesis, front and center, since it is the most scientifically defensible part of this component.

### 8.3 Calibration, not just weighting
Where possible (using the `case_studies/` folder, Part 3.4), sanity-check that historically severe incidents would have produced higher aggregate scores than historically minor ones under the chosen weighting — this is a weak but honest form of validation given how few labeled real incidents exist; say so explicitly rather than presenting it as rigorous calibration.

---

## PART 9 — RESPONSE DECISION SUPPORT

### 9.1 Scope discipline
This layer answers questions; it does not issue commands. Every output must read as "here is what the data supports," never "do X."

### 9.2 Question → data mapping

| Question | Answered from |
|---|---|
| Which area should be prioritized? | Rank stored `risk_assessment` rows (Part 13) by score, per active spill, most recent run |
| Which assets are most at risk? | Top-N rows from the same table, joined to asset metadata |
| How soon could they be affected? | `time_to_impact` field from Part 7 intersection, per horizon band |
| Why is an area high risk? | Decompose the Part 8 formula back into its stored terms — literally return the breakdown, not a re-generated explanation |
| What additional monitoring should be requested? | Rule-based: if forecast uncertainty (Part 6.3 envelope width) exceeds a threshold near a high-severity asset, flag "next acquisition recommended" with a suggested time window based on next satellite pass availability |
| What information is uncertain? | Explicitly surface: forecast confidence by horizon, detection confidence, data vintage of any static asset layer used |

### 9.3 Presentation discipline
Recommendations are always: (a) attributed to the specific data that produced them, (b) time-stamped with the data/model versions used, (c) accompanied by their own confidence, and (d) reversible/updatable as new observations arrive (Part 11) — never presented as a final verdict.

---

## PART 10 — AI ASSISTANT

### 10.1 Design principle: grounded retrieval, not free generation over imagery
The assistant must **never** reason directly from raw pixels or invent numbers. It answers by (1) parsing the user's question into a structured query against the system's own database (Part 13) — the same tables that already back the dashboard and API — (2) retrieving the relevant stored rows (detections, tracked slick history, forecast runs, risk decompositions), and (3) generating natural language that reports those retrieved values, with every number traceable to a row and timestamp. This is a **retrieval-augmented / tool-using** LLM pattern, not open-ended chat.

### 10.2 Example question handling

| Question | Tool call(s) behind the scenes |
|---|---|
| "Why is this spill high risk?" | Fetch `risk_assessment` row for spill_id → return the Part 8 factor breakdown in prose |
| "What changed since yesterday?" | Fetch `temporal_observation` rows for the tracked slick ID between the two timestamps → report area/position delta from Part 5 |
| "Which areas may be affected in the next 24 hours?" | Fetch `forecast_impact` rows filtered to horizon ≤ 24h, ordered by risk → list assets with time-to-impact |
| "Why did the predicted trajectory change?" | Diff the current forecast run's input forcing-field metadata against the previous run's (e.g., "the 24h current forecast update shifted, and forecast confidence dropped from 0.7 to 0.6") |
| "Show me the highest-risk assets" | Fetch top-N from `risk_assessment`, render as map layer + list |
| "How confident is the current detection?" | Return the stored per-polygon confidence score from Part 4.4, plus a plain-language band ("moderate confidence — consistent with either oil or a biogenic look-alike; recommend visual/analyst confirmation") |

### 10.3 Anti-hallucination guardrails
- If a query has no matching stored data (e.g., asked about a region with no recent scene), the assistant must say so explicitly rather than extrapolating.
- Every numeric claim in a response must be traceable to a specific database row/timestamp the assistant actually retrieved in that turn (log this for auditability).
- The assistant should never be allowed to *invent* a risk score, a coordinate, or a confidence value that doesn't exist in storage — this is a hard constraint on the tool/function-calling schema, not a prompting suggestion.

---

## PART 11 — DIGITAL-TWIN CONCEPT

### 11.1 Is a literal digital twin justified?
No — not in the strict sense (continuous, bidirectional, near-real-time sync between physical and virtual system). Given ~6-day routine satellite revisit and dependence on discrete forecast-model runs, this system cannot continuously mirror physical reality; it mirrors it at discrete update events. Claiming "digital twin" without qualification would overstate the system, which the project brief explicitly asks to avoid.

### 11.2 What is genuinely feasible and worth building: a **digital-twin-inspired state ledger**
A versioned, replayable representation with exactly the five states requested, each as an immutable, timestamped record rather than a mutable "current value":

```
CURRENT STATE    → the latest confirmed detection/segmentation for each active spill
     ↓
HISTORICAL STATE → the full, append-only sequence of past observations (Part 5) —
                     never overwritten, always queryable "as of" any past timestamp
     ↓
FORECAST STATE   → every forecast run stored with its own ID, input data vintage,
                     and horizon set — a new observation does not delete old
                     forecasts, it supersedes them, so you can always ask
                     "what did we predict yesterday vs. what actually happened"
     ↓
IMPACT STATE     → asset-intersection results, keyed to the forecast run that
                     produced them
     ↓
RESPONSE STATE   → the decision-support outputs (Part 9), keyed to the impact
                     state that produced them, with human-analyst annotations
                     (e.g., "confirmed by patrol aircraft") appendable but
                     never overwriting the machine-generated record
```
This gives the genuinely valuable digital-twin property — **full replayability and auditability of "what did the system know and when"** — without overclaiming real-time physical synchronization. This framing is also exactly what makes the forecast-accuracy self-evaluation in Part 16 possible (compare stored forecast state to later-arriving historical state).

---

## PART 12 — COMPLETE SYSTEM ARCHITECTURE

```
Sentinel-1 (Copernicus Data Space Ecosystem)
        │  scene search + download (scheduled or on-demand)
        ▼
INGESTION  ── stores raw SAFE product, registers scene metadata
        │
        ▼
PREPROCESSING  ── radiometric calibration → speckle filter → land mask → tiling
        │
        ▼
ML SEGMENTATION (DeepLabv3+)  ── per-tile inference → stitched mask → polygonization
        │                                                    │
        │                                          confidence per polygon
        ▼
TEMPORAL ASSOCIATION  ── match against prior tracked slicks (Part 5) → update/​create track
        │
        ├─────────────────────────────┐
        ▼                             ▼
TRAJECTORY FORECASTING          (feeds back to)
(OpenDrift/PyGNOME +             HISTORICAL STATE
 Monte Carlo ensemble,           (Part 11 ledger)
 forced by CMEMS currents/waves,
 ERA5/GFS wind)
        │
        ▼
GIS IMPACT ANALYSIS  ── PostGIS intersection: forecast bands × asset layers
        │
        ▼
RISK ENGINE  ── transparent weighted formula (Part 8), stored decomposed
        │
        ▼
RESPONSE DECISION SUPPORT  ── ranked, explainable recommendations (Part 9)
        │
        ├───────────────────────────────┐
        ▼                               ▼
POSTGRESQL / POSTGIS  ◄───────────  FASTAPI  ───────────►  REACT + MAPLIBRE DASHBOARD
(single source of truth,               │                    (Part 15)
 Part 13)                              ▼
                                AI ASSISTANT
                                (retrieval-grounded
                                 over the same DB,
                                 Part 10)
```
Every arrow into PostgreSQL/PostGIS is a write to an **immutable, versioned record** per Part 11; every arrow out (API, dashboard, assistant) reads the same tables, so there is exactly one source of truth in the whole system.

---

## PART 13 — DATABASE DESIGN

PostgreSQL + PostGIS. Core tables (columns abbreviated; add audit columns `created_at`, `created_by` throughout):

```sql
-- Raw satellite scenes
satellite_scenes (
  scene_id UUID PK, source TEXT, acquisition_time TIMESTAMPTZ,
  footprint GEOMETRY(POLYGON,4326), polarization TEXT[], mode TEXT,
  incidence_angle_range NUMRANGE, storage_path TEXT, ingestion_status TEXT
)

-- Preprocessed observation derived from a scene
observations (
  observation_id UUID PK, scene_id UUID FK, preprocessing_version TEXT,
  tile_grid_id TEXT, processed_at TIMESTAMPTZ
)

-- A single detected polygon within an observation
spill_detections (
  detection_id UUID PK, observation_id UUID FK,
  geom GEOMETRY(POLYGON,4326), area_km2 NUMERIC,
  predicted_class TEXT CHECK (predicted_class IN
     ('oil_spill','look_alike','ship','land','sea_surface')),
  confidence NUMERIC, model_version TEXT
)

-- Cross-scene tracked slick identity (Part 5)
tracked_slicks (
  track_id UUID PK, first_seen TIMESTAMPTZ, last_seen TIMESTAMPTZ, status TEXT
)
temporal_observations (
  id UUID PK, track_id UUID FK, detection_id UUID FK,
  area_delta NUMERIC, centroid_displacement_m NUMERIC,
  observed_state TEXT CHECK (observed_state IN
     ('expansion','contraction','fragmentation','persistence','disappearance'))
)

-- Environmental forcing data snapshots (cached CMEMS/ERA5/GFS pulls)
environmental_snapshots (
  snapshot_id UUID PK, variable TEXT, valid_time TIMESTAMPTZ,
  source TEXT, data_vintage TIMESTAMPTZ, storage_path TEXT
)

-- One forecast run (Part 6, Part 11 forecast state)
forecast_runs (
  forecast_run_id UUID PK, track_id UUID FK, run_time TIMESTAMPTZ,
  engine TEXT CHECK (engine IN ('opendrift','pygnome')), engine_version TEXT,
  forcing_snapshot_ids UUID[], ensemble_size INT
)
forecast_bands (
  id UUID PK, forecast_run_id UUID FK, horizon_hours INT,
  confidence_level NUMERIC,  -- e.g., 0.5 / 0.8 / 0.95
  geom GEOMETRY(POLYGON,4326)
)

-- Static/semi-static asset layers
assets (
  asset_id UUID PK, asset_type TEXT CHECK (asset_type IN
     ('protected_area','fishery','port','beach','wetland','coastal_population')),
  geom GEOMETRY, sensitivity_weight NUMERIC, data_vintage TIMESTAMPTZ, metadata JSONB
)

-- Impact state (Part 7, Part 11)
impact_assessments (
  id UUID PK, forecast_run_id UUID FK, asset_id UUID FK,
  horizon_hours INT, impact_probability NUMERIC, time_to_impact_hours NUMERIC
)

-- Risk state (Part 8, Part 11) — stores the full decomposed formula
risk_assessments (
  risk_id UUID PK, impact_assessment_id UUID FK, total_score NUMERIC,
  factor_breakdown JSONB,  -- {"impact_prob":.., "severity":.., "proximity":.., ...}
  weight_config_version TEXT
)

-- Response state (Part 9, Part 11)
response_recommendations (
  id UUID PK, risk_id UUID FK, recommendation_text TEXT,
  recommendation_type TEXT, analyst_annotation TEXT, analyst_id UUID NULL
)

-- Users / sessions (if multi-user)
users (user_id UUID PK, role TEXT, org TEXT)
analysis_sessions (session_id UUID PK, user_id UUID FK, started_at TIMESTAMPTZ,
                    active_track_ids UUID[])
```
Spatial indexes (`GIST`) on every `geom` column; a composite index on `(track_id, forecast_run_id, run_time)` for the assistant's "what changed / what did we predict then" queries (Part 10, Part 11).

---

## PART 14 — API DESIGN

FastAPI, versioned under `/api/v1`. Representative endpoints (not exhaustive):

| Endpoint | Method | Purpose | Request | Response | Errors |
|---|---|---|---|---|---|
| `/scenes` | GET | List/query ingested scenes | query params: bbox, date range | list of `satellite_scenes` | 400 invalid bbox |
| `/scenes/{id}/process` | POST | Trigger preprocessing+inference on a scene | scene_id | job_id (async) | 404 scene not found, 409 already processing |
| `/detections` | GET | Query spill detections | bbox, date range, min_confidence | GeoJSON FeatureCollection | 400 |
| `/tracks/{track_id}` | GET | Full history of a tracked slick | track_id | temporal_observations series | 404 |
| `/tracks/{track_id}/forecast` | POST | Run a new forecast for a track | engine, horizon list, ensemble_size | forecast_run_id | 422 missing forcing data |
| `/forecasts/{run_id}` | GET | Retrieve forecast bands | run_id | GeoJSON per horizon/confidence band | 404 |
| `/forecasts/{run_id}/impact` | GET | Retrieve asset impact assessment | run_id | list of `impact_assessments` joined to asset metadata | 404 |
| `/risk/{impact_id}` | GET | Retrieve decomposed risk score | impact_id | `risk_assessments` row incl. `factor_breakdown` | 404 |
| `/tracks/{track_id}/recommendations` | GET | Response decision-support output | track_id | ranked `response_recommendations` | 404 |
| `/assistant/query` | POST | NL question → grounded answer | free-text question, optional track_id context | answer text + cited row IDs/timestamps | 422 no matching data (returned as explicit "no data" response, not silent) |
| `/assets` | GET | Query asset layers | bbox, asset_type | GeoJSON | 400 |

All endpoints return standard error envelopes (`{"error": {"code", "message"}}`), and every response involving a forecast or risk value includes `model_version`/`weight_config_version`/`engine_version` fields so results are always reproducible and attributable (this is a direct consequence of the Part 11 ledger design, not an afterthought).

---

## PART 15 — FRONTEND

React + TypeScript + MapLibre (or Leaflet). Panel layout:

- **Interactive map** (center): base layers toggle (SAR scene overlay, current detections, historical track, forecast bands, risk heatmap, asset layers); time slider scrubbing through `HISTORICAL STATE`.
- **Timeline panel**: per-track area/confidence sparkline (from `temporal_observations`), click-to-jump to any past observation.
- **Forecast panel**: horizon selector (6/12/24/48h), confidence-band toggle (50/80/95%), visibly distinct styling for "best guess" vs. "conservative" bounds (echoing GNOME's own convention, Part 6.1) so users are never shown one line without its uncertainty.
- **Risk & assets panel**: ranked asset list with the Part 8 factor breakdown shown as a small stacked bar per asset (not just a single number) — every number here is clickable through to its source data.
- **Statistics panel**: current spill area, detection confidence, model/engine versions in use, data vintages of any static layer shown — always visible, never hidden in a tooltip, since staleness is a safety-relevant fact.
- **AI assistant panel**: chat interface, docked; every answer shows small inline citations back to the map/timeline elements it drew from (click a citation → map jumps to that feature).
- **Explanation panel**: expands on-demand from any risk score or forecast to show the full stored `factor_breakdown` / forcing-field metadata — this is the "explainability" requirement made literal and inspectable, not just a claim.

---

## PART 16 — MODEL EVALUATION

### 16.1 Segmentation
- **IoU / mean IoU** per class (oil, look-alike, ship, land, sea) — report per-class, not just mean, since oil-vs-look-alike IoU is the number that actually matters and averaging hides it.
- **Dice/F1**, **precision**, **recall** per class.
- **Pixel accuracy** as a secondary/sanity metric only (misleading alone given severe class imbalance — sea surface dominates pixel counts).
- Report on the **untouched Krestenitis test split** for benchmark comparability, and separately on **SOS-Sentinel** as a cross-domain generalization check — report both, with the gap between them stated explicitly as evidence of (or against) generalization.

### 16.2 Detection (event-level, not pixel-level)
Precision/recall/F1 on "was a real oil-spill instance detected at all" (polygon-level, with an IoU-overlap threshold to count a match), plus **false-positive rate specifically attributable to look-alikes** (a look-alike predicted as oil is a categorically different, more important error than a missed detection in open water, and should be reported separately).

### 16.3 Forecasting
- **Displacement error**: distance between predicted and observed centroid at each horizon, on the `case_studies/` validated incidents.
- **Trajectory error**: area of symmetric difference between predicted and observed slick polygon at each horizon (better than centroid-only, since it also penalizes wrong shape/spread, not just wrong position).
- **Uncertainty calibration**: for the Monte Carlo confidence bands, check empirically whether the "80% band" actually contains the observed outcome ~80% of the time across the (few) validated cases — with only a handful of real case studies available, report this as indicative, not statistically powered, and say so.

### 16.4 Risk
- **Sensitivity analysis** of the Part 8 weighting (how much does the ranking change under plausible weight perturbations) in place of formal calibration, given the shortage of labeled real-incident outcomes.
- **Explainability check**: for a sample of outputs, confirm a domain-non-expert can correctly reconstruct *why* an asset was ranked highly from the `factor_breakdown` alone — a qualitative but real evaluation of the explainability claim.

### 16.5 Avoiding data leakage
- **Geographic leakage**: never let tiles from the same raw scene appear in both train and test (Krestenitis's published split already respects this — preserve it; if you augment with your own scenes, split by *scene*, not by tile).
- **Temporal leakage**: for anything touching the tracker (Part 5) or forecast correction (Part 6.1 hybrid model), ensure training and evaluation incidents are chronologically separated (train on earlier incidents, evaluate on later ones) — never on random splits of temporally-linked observations from the same event.
- **Look-alike leakage**: if you construct your own curated-negative bank (Part 3.1) from the same handful of source scenes used elsewhere, explicitly track and disclose scene-level overlap with any other split.

---

## PART 17 — COMPUTATIONAL REQUIREMENTS

### 17.1 Hardware

| Tier | Spec | Notes |
|---|---|---|
| **Minimum (viable)** | 16 GB RAM, any modern CPU, free-tier cloud GPU for training bursts | Inference-only and dashboard work is CPU-feasible; training needs a GPU session |
| **Recommended** | 32 GB RAM, single 8–16 GB VRAM GPU (local or cloud) | Comfortable for DeepLabv3+/U-Net training at 256×256, batch size 8–16 |
| **Free/cloud options** | Google Colab (free tier T4, session-limited), Kaggle Notebooks (free weekly GPU quota, T4/P100), Copernicus Data Space Ecosystem's own free compute/JupyterHub for data access | Sufficient for this project's model sizes; budget for session-length limits (checkpoint frequently) |

### 17.2 Training strategy
- **Tile size**: 256×256 (matches the benchmark's own preprocessing, Part 3.1 — also keeps memory modest).
- **Batch size**: 8–16 on a 16 GB GPU with ResNet-34/50 backbone at mixed precision; drop to 4 with gradient accumulation on smaller GPUs.
- **Model size**: ResNet-34/50 encoder backbones are the sweet spot — large enough to match published DeepLabv3+ results, small enough to fine-tune from ImageNet weights in a few hours.
- **Storage**: raw Sentinel-1 scenes are large (hundreds of MB to a few GB per SAFE product); do not bulk-download the full archive — download on-demand per area/date of interest, and store only processed tiles + polygonized outputs long-term (megabytes, not gigabytes, per scene).

### 17.3 Prefer free/open wherever realistic
Every dataset and tool selected in Parts 3, 6 is free/open (Copernicus Data Space, CMEMS, ERA5/GFS, WDPA, Global Fishing Watch, OpenDrift, PyGNOME) — this was a selection constraint, not a coincidence, given the student-budget requirement.

---

## PART 18 — DEVELOPMENT ROADMAP

| Phase | Objective | Deliverables | Dependencies | Acceptance criteria |
|---|---|---|---|---|
| **0 — Research** | Finalize this document, confirm dataset/tool availability | This architecture doc, verified access to Copernicus/CMEMS/WDPA accounts | None | All Part 3 data sources confirmed reachable |
| **1 — Dataset** | Acquire and organize Krestenitis + SOS-Sentinel + a handful of raw scenes | `data/` structure populated per Part 3.4 | Phase 0 | Splits verified unmodified; at least 3 raw scenes downloaded and readable |
| **2 — Preprocessing** | Build calibration/speckle-filter/tiling pipeline | Reusable preprocessing module | Phase 1 | Visual QA on 10 sample tiles; land mask correctly excludes land pixels |
| **3 — Baseline segmentation** | Train DeepLabv3+ (+ U-Net comparison) | Trained checkpoints, inference script | Phase 2 | Beats a trivial threshold baseline on held-out test set |
| **4 — Evaluation** | Full Part 16.1–16.2 metrics, cross-domain test | Metrics report | Phase 3 | Per-class IoU reported, incl. oil-vs-look-alike confusion explicitly quantified |
| **5 — Temporal analysis** | Implement tracker (Part 5) | Tracking module + demo on ≥2 synthetic or real multi-pass sequences | Phase 3 | Correct association on a hand-verified toy sequence |
| **6 — Trajectory forecasting** | Integrate OpenDrift/PyGNOME + Monte Carlo ensemble | Forecast module producing confidence bands | Phase 5 (needs a tracked slick as input) | Runs end-to-end on ≥1 real validated case study; displacement error reported (Part 16.3) |
| **7 — Impact analysis** | PostGIS intersection against asset layers | Impact module | Phase 6, Part 3.2 assets loaded | Correctly flags at least one known asset near a real case-study trajectory |
| **8 — Risk engine** | Implement Part 8 formula + storage | Risk module, weight config documented | Phase 7 | Sensitivity analysis (Part 16.4) produces sane, monotonic behavior |
| **9 — FastAPI** | Implement Part 14 endpoints over the schema in Part 13 | Running API with OpenAPI docs | Phases 3–8 producing real data to serve | All endpoints return valid responses against seeded test data |
| **10 — Dashboard** | Build Part 15 frontend | Deployed React app | Phase 9 | Full pipeline visible end-to-end for at least one case study |
| **11 — AI assistant** | Implement grounded retrieval assistant (Part 10) | Working `/assistant/query` + chat UI | Phase 9 | Answers all six example questions correctly and refuses gracefully on out-of-data questions |
| **12 — Integration** | Wire ingestion scheduling, error handling, logging | End-to-end automated run on a fresh scene | All prior phases | A brand-new scene flows unattended from ingestion to dashboard display |
| **13 — Evaluation/demo** | Final metrics writeup, live or recorded demo on 1–2 real historical incidents | Report + demo | Phase 12 | Reproduces this document's Part 16 metrics; demo runs without manual intervention |

---

## PART 19 — FAILURE MODES & MITIGATIONS

| Failure mode | Mitigation |
|---|---|
| **SAR look-alikes cause false positives** | 5-class schema that explicitly labels look-alikes (Part 3.1); report look-alike-specific FP rate (Part 16.2); surface calibrated confidence, not a binary label, everywhere downstream |
| **Insufficient/imbalanced labels** | Reuse the established benchmark rather than collecting from scratch; use documented augmentation (GAN/diffusion-based, per Part 2.1) rather than naive oversampling alone; report per-class metrics so imbalance can't hide in an averaged number |
| **Speckle noise** | Standard SAR despeckling (Lee/refined-Lee) in preprocessing; treat over-aggressive filtering as its own risk (can erase thin slick edges) — validate visually, not just numerically |
| **Class imbalance** (sea surface pixels vastly outnumber oil pixels) | Weighted loss (e.g., focal or class-weighted cross-entropy/Dice); report per-class metrics, never rely on overall pixel accuracy |
| **Geographic distribution shift** | Explicit cross-domain evaluation on SOS-Sentinel (Part 16.1); document the gap honestly in the thesis rather than cherry-picking the benchmark number |
| **Temporal leakage** | Scene-level and chronological splitting discipline (Part 16.5) |
| **Inaccurate trajectory forecasts** | Use validated physics engines, not an untested learned model, as the backbone (Part 6.1); always show the "minimum regret"/wide band alongside the best guess; degrade stated confidence explicitly with horizon (Part 6.2) |
| **Poor/late environmental data** | Timestamp every forcing-field snapshot with its vintage (Part 13 `environmental_snapshots`); if CMEMS/GFS data for a needed time window is unavailable, fail the forecast explicitly (422, Part 14) rather than silently falling back to stale data |
| **Hallucinating AI assistant** | Hard retrieval-only architecture (Part 10.3) — the LLM never answers from parametric memory about a specific detection/forecast, only from retrieved rows; explicit "no data" responses when nothing matches |
| **False confidence in outputs generally** | Uncertainty is a first-class, stored, displayed field at every stage (detection confidence, forecast bands, risk-factor breakdown) — never collapse to a single number without its interval anywhere in the UI or API |
| **Computational limitations** | Architecture and tile-size choices (Part 17) explicitly selected to fit free-tier GPU budgets; checkpoint frequently against session limits |
| **API/data availability gaps** (Copernicus, CMEMS, GFW outages or rate limits) | Cache all pulled forcing/asset data locally with vintage timestamps (Part 13); design ingestion as retry-with-backoff, not a hard dependency that blocks the whole pipeline on one bad request |

---

## PART 20 — RESEARCH CONTRIBUTION

**"What is the strongest technically defensible contribution this project can make?"**

Not a new detection algorithm (DeepLabv3+ on this benchmark is already well-established) and not a new trajectory physics model (OpenDrift/GNOME already exist, validated, open-source). The defensible contribution is the **integration and honesty layer**: an open, reproducible, end-to-end pipeline that carries calibrated uncertainty from raw pixels through to a transparent, explainable, natural-language-accessible risk score — grounded throughout in a fully auditable, replayable state ledger (Part 11) — which does not currently exist as a single open system, academically or operationally.

### Three versions

**A. Realistic student implementation** *(recommended starting point)*
- DeepLabv3+ on Krestenitis only (skip SOS cross-domain training, keep it as eval-only).
- Trajectory forecasting via OpenDrift, single deterministic run + a simple 2–3-member perturbed ensemble (skip full hybrid physics+ML correction).
- Risk engine per Part 8, weights set by documented sensitivity analysis rather than expert elicitation.
- Dashboard covering current state + one forecast horizon + risk panel; assistant answering 3–4 of the 6 example question types.
- Evaluated end-to-end on 1 real historical case study.
- **This is a complete, defensible thesis/capstone on its own** — every part is real, working, and honestly evaluated; nothing is a stub.

**B. Strong hackathon implementation**
- Version A, plus: full 4-horizon Monte Carlo ensemble forecasting with confidence bands; full asset-layer set (protected areas + fisheries + coastline); all 6 assistant question types working; polished dashboard with the explanation panel. Skip the hybrid ML trajectory-correction research extension and the SAM-OIL/SegFormer stretch models — not needed to impress a hackathon panel, and both carry real risk of not converging in a 24–48h build window.

**C. Ambitious research prototype**
- Version B, plus: the hybrid physics+ML trajectory residual-correction model (Part 6.1) evaluated across multiple case studies with proper calibration reporting; SAM-OIL-style segmentation as a compared-against ceiling; multi-track, multi-region temporal association at scale; formal calibration/uncertainty-quantification writeup suitable for a standalone paper on the forecasting-uncertainty component specifically (this is the piece of the system with genuine, publishable research content, per Part 2.4).

### Recommendation
**Build Version A first, completely, before touching any part of B or C.** A fully working, honestly-evaluated, end-to-end system at Version A's scope is worth more — for a thesis, a portfolio, or a hackathon — than a partially working system that reaches for C's ambition and cannot finish the loop from pixels to explanation. Every part of B and C is an additive extension of the same architecture (nothing in this design requires rework to scale up), so nothing is wasted by starting narrow.

---

## Key sources consulted

- Krestenitis et al. (2019), *Oil Spill Identification from Satellite Images Using Deep Neural Networks*, Remote Sensing 11(15):1762 — benchmark dataset + DeepLabv3+ result: https://doi.org/10.3390/rs11151762
- Diffusion-based data augmentation for SAR oil-spill segmentation (2024): https://arxiv.org/pdf/2412.08116
- Cross-domain SAR oil-spill segmentation / geographic domain shift (2025): https://arxiv.org/pdf/2512.02290
- SAM-OIL: SAM-adapted composite oil-spill detection (2024): https://arxiv.org/pdf/2401.07502v2
- Copernicus Data Space Ecosystem (Sentinel-1 access): https://dataspace.copernicus.eu
- Copernicus Marine Service (currents, waves): https://data.marine.copernicus.eu
- PyGNOME (NOAA): https://github.com/noaa-orr-erd/pygnome
- OpenDrift / OpenOil (Dagestad et al. 2018, Geoscientific Model Development): https://doi.org/10.5194/gmd-11-1405-2018
- EMSA CleanSeaNet service overview: https://www.emsa.europa.eu
- Persian Gulf GNOME+CMEMS+ECMWF decision-support system (ERPN/RI risk indices): agris.fao.org record 65df02fa0f3e94b9e5d410e6
- GNOME vs. Sentinel-1A validation, Ennore port spill (2018): https://doi.org/10.1007/s12040-018-1015-3
- World Database on Protected Areas (WDPA/Protected Planet): https://www.protectedplanet.net
- Global Fishing Watch: https://globalfishingwatch.org
- Sentinel-1 constellation status (Wikipedia, cross-checked against ESA/EUSPA news): en.wikipedia.org/wiki/Sentinel-1, euspa.europa.eu
