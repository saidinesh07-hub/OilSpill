import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { MapDashboard } from './components/MapDashboard';
import { TimelinePanel } from './components/TimelinePanel';
import { ForecastControls } from './components/ForecastControls';
import { RiskWaterfallInspector } from './components/RiskWaterfallInspector';
import { AssetImpactTable } from './components/AssetImpactTable';
import { DecisionSupportPanel } from './components/DecisionSupportPanel';
import { AssistantChat } from './components/AssistantChat';
import { apiService } from './services/api';
import type {
  SatelliteScene,
  SpillDetection,
  TrackedSlick,
  ForecastRun,
  ForecastBand,
  Asset,
  ImpactAssessment,
  RiskAssessment,
  ResponseRecommendation,
} from './types';

export function App() {
  // State
  const [selectedScene, setSelectedScene] = useState<SatelliteScene | undefined>();
  const [detections, setDetections] = useState<SpillDetection[]>([]);
  const [activeTrack, setActiveTrack] = useState<TrackedSlick | undefined>();
  const [forecastRun, setForecastRun] = useState<ForecastRun | undefined>();
  const [forecastBands, setForecastBands] = useState<ForecastBand[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [impacts, setImpacts] = useState<ImpactAssessment[]>([]);
  const [selectedRisk, setSelectedRisk] = useState<RiskAssessment | undefined>();
  const [recommendations, setRecommendations] = useState<ResponseRecommendation[]>([]);

  // Map & Controls State
  const [selectedHorizonHours, setSelectedHorizonHours] = useState<number>(24);
  const [visibleConfidenceLevels, setVisibleConfidenceLevels] = useState<number[]>([0.50, 0.80, 0.95]);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [flyToCoords, setFlyToCoords] = useState<[number, number] | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const [visibleLayers, setVisibleLayers] = useState({
    footprint: true,
    detections: true,
    forecast: true,
    assets: true,
    trackHistory: true,
  });

  const toggleLayer = (layerKey: string) => {
    setVisibleLayers((prev: any) => ({
      ...prev,
      [layerKey]: !prev[layerKey],
    }));
  };

  const toggleConfidenceLevel = (level: number) => {
    setVisibleConfidenceLevels((prev) =>
      prev.includes(level) ? prev.filter((l) => l !== level) : [...prev, level]
    );
  };

  // Initial Data Fetch
  const loadData = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch Tracks & Scenes
      const [trackList, sceneList, assetList] = await Promise.all([
        apiService.getTracks(),
        apiService.getScenes(),
        apiService.getAssets(),
      ]);

      setAssets(assetList);

      const targetTrack = trackList[0];
      setActiveTrack(targetTrack);
      setSelectedScene(sceneList[0]);

      if (targetTrack) {
        // 2. Fetch Latest Forecast for Track
        const fRun = await apiService.getLatestForecast(targetTrack.track_id);
        setForecastRun(fRun);
        if (fRun?.bands) {
          setForecastBands(fRun.bands);
        }

        // 3. Fetch Impacts and Recommendations
        if (fRun?.forecast_run_id) {
          const impactList = await apiService.getImpacts(fRun.forecast_run_id);
          setImpacts(impactList);

          if (impactList.length > 0) {
            const riskData = await apiService.getRiskAssessment(impactList[0].id).catch(() => undefined);
            setSelectedRisk(riskData);
          }
        }

        const recs = await apiService.getTrackRecommendations(targetTrack.track_id).catch(() => []);
        setRecommendations(recs);

        // 4. Extract detections from temporal observations
        const dets = targetTrack.temporal_observations
          ?.map((o) => o.detection)
          .filter(Boolean) as SpillDetection[];
        setDetections(dets || []);
      }
    } catch (err) {
      console.error('Failed to load system state:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSeedDemo = async () => {
    setIsLoading(true);
    try {
      await apiService.seedCaseStudies();
      await loadData();
    } catch (err) {
      console.error('Failed to seed case study:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectImpact = async (imp: ImpactAssessment) => {
    try {
      const riskData = await apiService.getRiskAssessment(imp.id);
      setSelectedRisk(riskData);
      if (imp.asset) {
        setFlyToCoords([imp.asset.centroid_lon, imp.asset.centroid_lat]);
      }
    } catch (err) {
      console.error('Failed to load risk detail:', err);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#070b14] text-slate-100">
      {/* Top Navigation */}
      <Navbar
        activeSlickName={activeTrack?.slick_name}
        totalAreaKm2={activeTrack?.total_area_km2}
        driftSpeedKmh={activeTrack?.drift_speed_kmh}
        driftHeadingDeg={activeTrack?.drift_heading_deg}
        status={activeTrack?.current_status}
        isSynthetic={selectedScene?.is_synthetic}
        onRefresh={loadData}
        onSeedDemo={handleSeedDemo}
        isLoading={isLoading}
      />

      {/* Main Content Dashboard */}
      <div className="flex-1 flex overflow-hidden">
        {/* Center: Geospatial Map View */}
        <div className="flex-1 flex flex-col relative">
          <MapDashboard
            scene={selectedScene}
            detections={detections}
            activeTrack={activeTrack}
            forecastBands={forecastBands}
            assets={assets}
            selectedHorizonHours={selectedHorizonHours}
            visibleConfidenceLevels={visibleConfidenceLevels}
            visibleLayers={visibleLayers}
            onToggleLayer={toggleLayer}
            onSelectFeature={(feat) => {
              if (feat.centroid_lon && feat.centroid_lat) {
                setFlyToCoords([feat.centroid_lon, feat.centroid_lat]);
              }
            }}
            flyToCoords={flyToCoords}
          />

          {/* Bottom Time Scrubber */}
          <TimelinePanel
            activeTrack={activeTrack}
            selectedHorizonHours={selectedHorizonHours}
            onSelectHorizon={setSelectedHorizonHours}
            currentStep={currentStep}
            onSelectStep={setCurrentStep}
          />
        </div>

        {/* Right Intelligence & Decision Support Sidebar */}
        <div className="w-[440px] flex flex-col glass-panel border-l border-slate-700/80 p-4 space-y-4 overflow-y-auto custom-scrollbar z-20">
          {/* 1. Trajectory Forecasting Controls */}
          <ForecastControls
            forecastRun={forecastRun}
            selectedHorizonHours={selectedHorizonHours}
            onSelectHorizon={setSelectedHorizonHours}
            visibleConfidenceLevels={visibleConfidenceLevels}
            onToggleConfidenceLevel={toggleConfidenceLevel}
          />

          {/* 2. Explainable Risk Inspector */}
          <RiskWaterfallInspector riskAssessment={selectedRisk} />

          {/* 3. Threatened Assets & Arrival Windows */}
          <AssetImpactTable
            impacts={impacts}
            onSelectImpact={handleSelectImpact}
            onFlyTo={(coords) => setFlyToCoords(coords)}
          />

          {/* 4. Prioritized Decision Support Guidance */}
          <DecisionSupportPanel recommendations={recommendations} />

          {/* 5. Grounded AI Assistant */}
          <AssistantChat
            activeTrackId={activeTrack?.track_id}
            onFlyTo={(coords) => setFlyToCoords(coords)}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
