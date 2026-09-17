import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { Layers, Compass } from 'lucide-react';
import type { SpillDetection, ForecastBand, Asset, TrackedSlick, SatelliteScene, CorrelationCandidate } from '../types';

// Utility for candidate marker colors based on classification
const getCandidateColor = (classification: string) => {
  if (classification === 'HIGHLY_RELEVANT') return '#ef4444'; // Red
  if (classification === 'POTENTIALLY_RELEVANT') return '#f59e0b'; // Amber
  return '#94a3b8'; // Slate
};

interface MapDashboardProps {
  scene?: SatelliteScene;
  detections: SpillDetection[];
  activeTrack?: TrackedSlick;
  forecastBands: ForecastBand[];
  assets: Asset[];
  selectedHorizonHours: number;
  visibleConfidenceLevels: number[];
  visibleLayers: {
    footprint: boolean;
    detections: boolean;
    forecast: boolean;
    assets: boolean;
    trackHistory: boolean;
    vessels?: boolean;
    infrastructure?: boolean;
    candidates?: boolean;
  };
  onToggleLayer: (layerKey: string) => void;
  onSelectFeature?: (feature: any) => void;
  onSelectCandidate?: (candidate: CorrelationCandidate) => void;
  flyToCoords?: [number, number] | null;
  incidentCoords?: [number, number];
  intelligenceData?: any;
  candidates?: CorrelationCandidate[];
  activeCandidate?: CorrelationCandidate | null;
}

export const MapDashboard: React.FC<MapDashboardProps> = ({
  scene,
  detections,
  activeTrack,
  forecastBands,
  assets,
  selectedHorizonHours,
  visibleConfidenceLevels,
  visibleLayers,
  onToggleLayer,
  onSelectFeature,
  onSelectCandidate,
  flyToCoords,
  incidentCoords,
  intelligenceData,
  candidates = [],
  activeCandidate,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layersGroupRef = useRef<{ [key: string]: L.LayerGroup }>({});

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Center on incident or fallback to Ennore
    const map = L.map(mapContainerRef.current, {
      center: incidentCoords || [13.25, 80.35],
      zoom: 11,
      zoomControl: false,
      attributionControl: false,
    });

    // Esri Dark Gray Base for premium scientific aesthetics (no API key required)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 16,
      attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Initialize Layer Groups
    layersGroupRef.current = {
      footprint: L.layerGroup().addTo(map),
      detections: L.layerGroup().addTo(map),
      forecast: L.layerGroup().addTo(map),
      assets: L.layerGroup().addTo(map),
      trackHistory: L.layerGroup().addTo(map),
      vessels: L.layerGroup().addTo(map),
      candidates: L.layerGroup().addTo(map),
      infrastructure: L.layerGroup().addTo(map),
      aoi: L.layerGroup().addTo(map),
    };

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Handle Fly-To requests (e.g. from Assistant citations)
  useEffect(() => {
    if (mapInstanceRef.current && flyToCoords) {
      mapInstanceRef.current.flyTo([flyToCoords[1], flyToCoords[0]], 13, { duration: 1.2 });
    }
  }, [flyToCoords]);

  // Render Satellite Scene Footprint
  useEffect(() => {
    const group = layersGroupRef.current.footprint;
    if (!group) return;
    group.clearLayers();

    if (visibleLayers.footprint && scene?.footprint_geojson) {
      if (scene.quicklook_local && scene.bbox) {
        const bounds: L.LatLngBoundsExpression = [
          [scene.bbox[1], scene.bbox[0]], // minLat, minLon
          [scene.bbox[3], scene.bbox[2]], // maxLat, maxLon
        ];
        const imageOverlay = L.imageOverlay(scene.quicklook_local, bounds, {
          opacity: 0.8,
          alt: 'SAR Quicklook',
        });
        group.addLayer(imageOverlay);
      } else {
        const footprintLayer = L.geoJSON(scene.footprint_geojson, {
          style: {
            color: '#38bdf8',
            weight: 1.5,
            dashArray: '4, 4',
            fillColor: '#0284c7',
            fillOpacity: 0.05,
          },
        });
        footprintLayer.bindTooltip(
          `<b>${scene.scene_name}</b><br/>Sensor: ${scene.source}<br/>Acquisition: ${new Date(scene.acquisition_time).toUTCString()}`,
          { sticky: true }
        );
        group.addLayer(footprintLayer);
      }
    }
  }, [scene, visibleLayers.footprint]);

  // Render Observed Spill Detections
  useEffect(() => {
    const group = layersGroupRef.current.detections;
    if (!group) return;
    group.clearLayers();

    if (visibleLayers.detections && detections.length > 0) {
      detections.forEach((det) => {
        const isOil = det.predicted_class === 'oil_spill';
        const color = isOil ? '#ef4444' : '#f59e0b';
        const fillCol = isOil ? '#dc2626' : '#d97706';

        const layer = L.geoJSON(det.geom_geojson, {
          style: {
            color: color,
            weight: 2.5,
            fillColor: fillCol,
            fillOpacity: isOil ? 0.65 : 0.45,
            className: isOil ? 'pulsing-slick' : '',
          },
        });

        layer.bindPopup(`
          <div class="p-2 space-y-1.5 text-xs">
            <div class="flex items-center space-x-1 font-bold ${isOil ? 'text-red-400' : 'text-amber-400'}">
              <span>${isOil ? 'CONFIRMED OIL SPILL' : 'LOOK-ALIKE CANDIDATE'}</span>
            </div>
            <div><b>Area:</b> ${det.area_km2.toFixed(2)} km² (Geodetic WGS84)</div>
            <div><b>Confidence:</b> ${(det.confidence * 100).toFixed(0)}%</div>
            <div><b>Look-Alike Risk:</b> ${(det.lookalike_risk_score * 100).toFixed(0)}%</div>
            <div><b>Circularity:</b> ${det.morphology_features?.circularity?.toFixed(2) || 'N/A'}</div>
            <div><b>Model:</b> ${det.model_version}</div>
          </div>
        `);

        layer.on('click', () => {
          if (onSelectFeature) onSelectFeature(det);
        });

        group.addLayer(layer);
      });
    }
  }, [detections, visibleLayers.detections, onSelectFeature]);

  // Render Forecast Uncertainty Bands
  useEffect(() => {
    const group = layersGroupRef.current.forecast;
    if (!group) return;
    group.clearLayers();

    if (visibleLayers.forecast && forecastBands.length > 0) {
      // Filter by selected horizon hours
      const filtered = forecastBands.filter(
        (b) =>
          b.horizon_hours === selectedHorizonHours &&
          visibleConfidenceLevels.includes(b.confidence_level)
      );

      // Sort so highest confidence (95% outer) renders first, 50% core renders on top
      filtered.sort((a, b) => b.confidence_level - a.confidence_level);

      filtered.forEach((band) => {
        let strokeColor = '#818cf8';
        let fillColor = '#6366f1';
        let fillOpacity = 0.25;
        let dashArray = 'none';

        if (band.confidence_level === 0.95) {
          // Conservative / Minimum Regret Outer Envelope
          strokeColor = '#a855f7';
          fillColor = '#9333ea';
          fillOpacity = 0.15;
          dashArray = '5, 5';
        } else if (band.confidence_level === 0.80) {
          strokeColor = '#3b82f6';
          fillColor = '#2563eb';
          fillOpacity = 0.30;
        } else if (band.confidence_level === 0.50) {
          // Best Guess Core
          strokeColor = '#ec4899';
          fillColor = '#db2777';
          fillOpacity = 0.50;
        }

        const layer = L.geoJSON(band.geom_geojson, {
          style: {
            color: strokeColor,
            weight: 2,
            dashArray: dashArray,
            fillColor: fillColor,
            fillOpacity: fillOpacity,
          },
        });

        layer.bindTooltip(
          `<b>Forecast Horizon: +${band.horizon_hours}h</b><br/>Confidence Envelope: ${(band.confidence_level * 100).toFixed(0)}%<br/>Predicted Spread Area: ${band.area_km2.toFixed(1)} km²`,
          { sticky: true }
        );

        group.addLayer(layer);
      });
    }
  }, [forecastBands, selectedHorizonHours, visibleConfidenceLevels, visibleLayers.forecast]);

  // Render Coastal Sensitive Assets
  useEffect(() => {
    const group = layersGroupRef.current.assets;
    if (!group) return;
    group.clearLayers();

    if (visibleLayers.assets && assets.length > 0) {
      assets.forEach((asset) => {
        let color = '#22c55e'; // green default
        if (asset.asset_type === 'protected_area') color = '#10b981'; // Emerald
        else if (asset.asset_type === 'fishery') color = '#06b6d4'; // Cyan
        else if (asset.asset_type === 'beach') color = '#eab308'; // Yellow
        else if (asset.asset_type === 'port') color = '#64748b'; // Slate
        else if (asset.asset_type === 'coastal_population') color = '#f97316'; // Orange

        const layer = L.geoJSON(asset.geom_geojson, {
          style: {
            color: color,
            weight: 1.8,
            fillColor: color,
            fillOpacity: 0.22,
          },
        });

        layer.bindPopup(`
          <div class="p-2 space-y-1 text-xs">
            <div class="font-bold text-slate-100">${asset.name}</div>
            <div class="text-[10px] uppercase font-semibold text-cyan-400">
              Type: ${asset.asset_type.replace('_', ' ')}
            </div>
            <div><b>Sensitivity Weight:</b> ${asset.sensitivity_weight} / 5.0</div>
            <div><b>Data Source:</b> ${asset.data_source}</div>
            <div><b>Vintage:</b> ${new Date(asset.data_vintage).toLocaleDateString()}</div>
          </div>
        `);

        group.addLayer(layer);
      });
    }
  }, [assets, visibleLayers.assets]);

  // Render Real AIS Vessels
  useEffect(() => {
    const group = layersGroupRef.current.vessels;
    if (!group) return;
    group.clearLayers();

    if (visibleLayers.vessels && intelligenceData?.analysis?.vessels?.vessels) {
      const vessels = intelligenceData.analysis.vessels.vessels;
      const seenMmsi = new Set();
      vessels.forEach((v: any) => {
        if (!v.latitude || !v.longitude || seenMmsi.has(v.mmsi)) return;
        seenMmsi.add(v.mmsi);
        
        const marker = L.circleMarker([v.latitude, v.longitude], {
          radius: 4,
          color: '#f8fafc',
          weight: 1,
          fillColor: '#94a3b8',
          fillOpacity: 0.8,
        });

        marker.bindPopup(`
          <div class="p-2 text-xs">
            <div class="font-bold text-slate-100">${v.name || 'Unknown Vessel'}</div>
            <div><b>MMSI:</b> ${v.mmsi}</div>
            <div><b>Type:</b> ${v.vessel_type || 'Unknown'}</div>
            <div><b>Speed:</b> ${v.speed ? v.speed + ' kn' : 'N/A'}</div>
            <div><b>Course:</b> ${v.heading ? v.heading + '°' : 'N/A'}</div>
            <div class="text-emerald-400 mt-1"><b>Reported:</b> ${new Date(v.timestamp).toLocaleString()}</div>
          </div>
        `);
        group.addLayer(marker);
      });
    }
  }, [intelligenceData, visibleLayers.vessels]);

  // Render Backtrack / Estimated Source Zone
  useEffect(() => {
    const group = layersGroupRef.current.trackHistory;
    if (!group) return;
    // Don't clearLayers here if trackHistory is also used by mock tracks, but since we are in REAL mode, mock tracks are empty.
    
    if (visibleLayers.trackHistory && intelligenceData?.analysis?.backtrack?.status === 'COMPLETED') {
      const backtrack = intelligenceData.analysis.backtrack;
      if (backtrack.source_lat && backtrack.source_lon) {
         const circle = L.circle([backtrack.source_lat, backtrack.source_lon], {
           radius: 3000, // 3km uncertainty radius
           color: '#f59e0b',
           weight: 2,
           dashArray: '5,5',
           fillColor: '#fcd34d',
           fillOpacity: 0.15
         });
         circle.bindTooltip(`<b>Estimated Source Zone</b><br/>Confidence: ${backtrack.confidence}`, { sticky: true });
         group.addLayer(circle);

         // Draw line from slick centroid to source zone
         const slick = intelligenceData?.analysis?.spill_candidates?.[0];
         if (slick && slick.centroid_lat && slick.centroid_lon) {
           const line = L.polyline([[slick.centroid_lat, slick.centroid_lon], [backtrack.source_lat, backtrack.source_lon]], {
             color: '#f59e0b',
             weight: 1.5,
             dashArray: '4,4'
           });
           group.addLayer(line);
         }
      }
    }
  }, [intelligenceData, visibleLayers.trackHistory]);

  // Render Track History & Kinematic Drift Vectors
  useEffect(() => {
    const group = layersGroupRef.current.trackHistory;
    if (!group) return;
    group.clearLayers();

    if (visibleLayers.trackHistory && activeTrack?.temporal_observations?.length) {
      const obs = activeTrack.temporal_observations;
      const sorted = [...obs].sort(
        (a, b) => new Date(a.observation_time).getTime() - new Date(b.observation_time).getTime()
      );

      const latlngs: [number, number][] = [];
      sorted.forEach((o) => {
        if (o.detection) {
          latlngs.push([o.detection.centroid_lat, o.detection.centroid_lon]);

          // Marker for historical point
          const marker = L.circleMarker([o.detection.centroid_lat, o.detection.centroid_lon], {
            radius: 5,
            color: '#38bdf8',
            fillColor: '#0284c7',
            fillOpacity: 0.9,
          });
          marker.bindTooltip(
            `<b>${new Date(o.observation_time).toLocaleDateString()}</b><br/>Area: ${o.area_km2.toFixed(2)} km²<br/>State: ${o.observed_state}`,
            { sticky: true }
          );
          group.addLayer(marker);
        }
      });

      if (latlngs.length >= 2) {
        const polyline = L.polyline(latlngs, {
          color: '#38bdf8',
          weight: 2.5,
          dashArray: '6, 6',
        });
        group.addLayer(polyline);
      }
    }
  }, [activeTrack, visibleLayers.trackHistory]);

  // Render Correlated Spill Candidates
  useEffect(() => {
    const group = layersGroupRef.current.candidates;
    if (!group) return;
    group.clearLayers();

    if (visibleLayers.candidates && candidates.length > 0) {
      candidates.forEach((cand, index) => {
        if (!cand.latitude || !cand.longitude) return;

        const isSelected = activeCandidate?.mmsi === cand.mmsi;
        const color = getCandidateColor(cand.classification);
        const rank = index + 1;
        
        // Custom SVG icon for Candidates
        const svgIcon = `
          <svg width="${isSelected ? 32 : 24}" height="${isSelected ? 32 : 24}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="${color}" fill-opacity="${isSelected ? 0.9 : 0.7}" stroke="${isSelected ? '#fff' : '#000'}" stroke-width="2"/>
            <text x="12" y="16" font-size="10" font-weight="bold" fill="white" text-anchor="middle" font-family="sans-serif">${rank}</text>
          </svg>
        `;

        const icon = L.divIcon({
          html: svgIcon,
          className: 'bg-transparent',
          iconSize: isSelected ? [32, 32] : [24, 24],
          iconAnchor: isSelected ? [16, 16] : [12, 12],
        });

        const marker = L.marker([cand.latitude, cand.longitude], {
          icon: icon,
          zIndexOffset: isSelected ? 1000 : 500,
        });

        marker.on('click', () => {
          if (onSelectCandidate) onSelectCandidate(cand);
        });

        // Add tooltip instead of popup so clicking selects it for the sidebar
        marker.bindTooltip(
          `<b>#${rank} ${cand.name}</b><br/>Score: ${cand.correlation_score.toFixed(0)} - ${cand.classification.replace('_', ' ')}`,
          { direction: 'top', offset: [0, -10] }
        );

        group.addLayer(marker);
      });
    }
  }, [candidates, activeCandidate, visibleLayers.candidates, onSelectCandidate]);

  return (
    <div className="relative w-full h-full min-h-[500px] flex-1">
      {/* Map Container */}
      <div ref={mapContainerRef} className="w-full h-full absolute inset-0 z-0" />

      {/* Floating Layer Toggle Menu */}
      <div className="absolute top-4 right-4 glass-panel rounded-xl p-3 z-10 text-xs shadow-xl border border-slate-700/80 w-56">
        <div className="flex items-center space-x-1.5 font-bold text-slate-200 border-b border-slate-700/60 pb-2 mb-2">
          <Layers className="w-4 h-4 text-blue-400" />
          <span>Intelligence Layers</span>
        </div>

        <div className="space-y-1.5">
          <label className="flex items-center space-x-2 cursor-pointer hover:text-blue-300 transition">
            <input
              type="checkbox"
              checked={visibleLayers.footprint}
              onChange={() => onToggleLayer('footprint')}
              className="rounded bg-slate-900 border-slate-700 text-blue-500 focus:ring-0"
            />
            <span className="flex-1">SAR Scene Footprint</span>
            <span className="w-2 h-2 rounded-full bg-sky-400"></span>
          </label>

          <label className="flex items-center space-x-2 cursor-pointer hover:text-blue-300 transition">
            <input
              type="checkbox"
              checked={visibleLayers.detections}
              onChange={() => onToggleLayer('detections')}
              className="rounded bg-slate-900 border-slate-700 text-red-500 focus:ring-0"
            />
            <span className="flex-1">Active Slicks & Lookalikes</span>
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
          </label>

          <label className="flex items-center space-x-2 cursor-pointer hover:text-blue-300 transition">
            <input
              type="checkbox"
              checked={visibleLayers.forecast}
              onChange={() => onToggleLayer('forecast')}
              className="rounded bg-slate-900 border-slate-700 text-indigo-500 focus:ring-0"
            />
            <span className="flex-1">Forecast Trajectory Envelopes</span>
            <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
          </label>

          <label className="flex items-center space-x-2 cursor-pointer hover:text-blue-300 transition">
            <input
              type="checkbox"
              checked={visibleLayers.assets}
              onChange={() => onToggleLayer('assets')}
              className="rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-0"
            />
            <span className="flex-1">Coastal Assets & MPAs</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          </label>

          <label className="flex items-center space-x-2 cursor-pointer hover:text-blue-300 transition">
            <input
              type="checkbox"
              checked={visibleLayers.trackHistory}
              onChange={() => onToggleLayer('trackHistory')}
              className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
            />
            <span className="flex-1">Historical Drift Track</span>
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          </label>
          
          <label className="flex items-center space-x-2 cursor-pointer hover:text-blue-300 transition">
            <input
              type="checkbox"
              checked={visibleLayers.vessels}
              onChange={() => onToggleLayer('vessels')}
              className="rounded bg-slate-900 border-slate-700 text-slate-500 focus:ring-0"
            />
            <span className="flex-1">AIS Vessels</span>
            <span className="w-2 h-2 rounded-full bg-slate-400"></span>
          </label>
          
          <label className="flex items-center space-x-2 cursor-pointer hover:text-blue-300 transition">
            <input
              type="checkbox"
              checked={visibleLayers.candidates}
              onChange={() => onToggleLayer('candidates')}
              className="rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0"
            />
            <span className="flex-1">Correlation Candidates</span>
            <span className="w-2 h-2 rounded-full bg-amber-400"></span>
          </label>
        </div>
      </div>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-6 left-6 glass-panel rounded-xl p-3 z-10 text-[11px] shadow-xl border border-slate-700/80 max-w-xs">
        <div className="font-bold text-slate-300 mb-1.5 flex items-center space-x-1">
          <Compass className="w-3.5 h-3.5 text-blue-400" />
          <span>SAR Classification & Risk Legend</span>
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-slate-400">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-red-500/80 border border-red-400"></span>
            <span>Confirmed Oil</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-amber-500/80 border border-amber-400"></span>
            <span>Look-Alike</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-pink-500/60 border border-pink-400"></span>
            <span>50% Best Guess</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-purple-500/30 border border-purple-400 border-dashed"></span>
            <span>95% Min Regret</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-emerald-500/50 border border-emerald-400"></span>
            <span>Marine Protected</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-cyan-500/50 border border-cyan-400"></span>
            <span>Fisheries/Aquaculture</span>
          </div>
        </div>
      </div>
    </div>
  );
};
