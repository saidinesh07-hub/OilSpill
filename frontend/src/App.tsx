import { useState, useEffect, useMemo } from 'react';
import { Navbar } from './components/Navbar';
import { MapDashboard } from './components/MapDashboard';
import { TimelinePanel } from './components/TimelinePanel';
import { ForecastControls } from './components/ForecastControls';
import { RiskWaterfallInspector } from './components/RiskWaterfallInspector';
import { AssetImpactTable } from './components/AssetImpactTable';
import { DecisionSupportPanel } from './components/DecisionSupportPanel';
import { AssistantChat } from './components/AssistantChat';
import { DemoDataProvider, RealDataProvider } from './services/DataProvider';
import type { DataProvider } from './services/DataProvider';
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

import { IncidentLocationControl } from './components/IncidentLocationControl';
import { IntelligencePanel } from './components/IntelligencePanel';

export function App() {
  // State
  const [selectedScene, setSelectedScene] = useState<SatelliteScene | undefined>();
  const [detections, setDetections] = useState<SpillDetection[]>([]);
  const [activeTrack, setActiveTrack] = useState<TrackedSlick | undefined>();
  const [forecastRun] = useState<ForecastRun | undefined>();
  const [forecastBands, setForecastBands] = useState<ForecastBand[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [impacts, setImpacts] = useState<ImpactAssessment[]>([]);
  const [selectedRisk, setSelectedRisk] = useState<RiskAssessment | undefined>();
  const [recommendations, setRecommendations] = useState<ResponseRecommendation[]>([]);

  // Location State
  const [incidentCoords, setIncidentCoords] = useState<[number, number] | undefined>(undefined);
  const [incidentName, setIncidentName] = useState('');
  
  // GLOBAL MODE
  const [dataMode, setDataMode] = useState<'DEMO' | 'REAL'>('DEMO');
  const [intelligenceData, setIntelligenceData] = useState<any>(null);

  // Map & Controls State
  const [selectedHorizonHours, setSelectedHorizonHours] = useState<number>(24);
  const [visibleConfidenceLevels, setVisibleConfidenceLevels] = useState<number[]>([0.50, 0.80, 0.95]);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [flyToCoords, setFlyToCoords] = useState<[number, number] | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const [visibleLayers, setVisibleLayers] = useState({
    footprint: true,
    detections: true,
    forecast: true,
    assets: true,
    trackHistory: true,
    vessels: true,
    infrastructure: true,
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

  const provider: DataProvider = useMemo(() => {
    return dataMode === 'DEMO' ? new DemoDataProvider() : new RealDataProvider();
  }, [dataMode]);

  const loadData = async (lat: number, lon: number, name: string) => {
    setIsLoading(true);
    setIncidentCoords([lat, lon]);
    setIncidentName(name);
    setFlyToCoords([lon, lat]);
    
    // Clear previous state
    setSelectedScene(undefined);
    setDetections([]);
    setActiveTrack(undefined);
    setForecastBands([]);
    setAssets([]);
    setImpacts([]);
    setSelectedRisk(undefined);
    setRecommendations([]);
    setIntelligenceData(null);

    try {
      await provider.initialize(lat, lon, name);
      
      const payload = provider.getRawPayload();
      setIntelligenceData(payload);

      const satelliteData = provider.getSatelliteData();
      if (satelliteData && satelliteData.length > 0) {
        setSelectedScene(satelliteData[0]);
      }
      
      setDetections(provider.getSpillDetection() || []);
      
      const track = provider.getActiveTrack();
      setActiveTrack(track || undefined);
      
      setForecastBands(provider.getPrediction() || []);
      setAssets(provider.getAssets() || []);
      setImpacts(provider.getImpacts() || []);
      setRecommendations(provider.getRecommendations() || []);

      const impactsList = provider.getImpacts();
      if (impactsList && impactsList.length > 0) {
         setSelectedRisk(undefined);
      }
    } catch (err: any) {
      console.error(err);
      if (dataMode === 'REAL') alert(err.message || "REAL DATA UNAVAILABLE. Backend error.");
    } finally {
      setIsLoading(false);
    }
  };

  // Re-fetch data if mode changes but we have a location
  useEffect(() => {
    if (incidentCoords && incidentName) {
       loadData(incidentCoords[0], incidentCoords[1], incidentName);
    }
  }, [dataMode]);

  const handleLocationChange = (lat: number, lon: number, name: string) => {
      // Location search uses the global DEMO/REAL mode from Navbar, not a local override.
      void loadData(lat, lon, name);
  };

  const handleSeedDemo = async () => {
    setDataMode('DEMO');
    // For a demo, simulate clicking Ennore port
    loadData(13.23, 80.33, 'Ennore Port (DEMO)');
  };

  const handleSelectImpact = async (imp: ImpactAssessment) => {
     if (imp.asset) {
       setFlyToCoords([imp.asset.centroid_lon, imp.asset.centroid_lat]);
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
        onRefresh={() => incidentCoords && loadData(incidentCoords[0], incidentCoords[1], incidentName)}
        onSeedDemo={handleSeedDemo}
        isLoading={isLoading}
        currentMode={dataMode}
        onModeToggle={() => setDataMode(m => m === 'DEMO' ? 'REAL' : 'DEMO')}
      />

      {/* Main Content Dashboard */}
      <div className="flex-1 flex overflow-hidden">
        {/* Center: Geospatial Map View */}
        <div className="flex-1 flex flex-col relative">
          <div className="absolute top-4 left-4 z-20">
            <IncidentLocationControl 
              currentLocationName={incidentName}
              currentCoords={incidentCoords}
              dataMode={dataMode}
              onLocationChange={handleLocationChange}
            />
          </div>
          <MapDashboard
            scene={selectedScene}
            detections={detections}
            activeTrack={activeTrack}
            forecastBands={forecastBands}
            assets={assets}
            intelligenceData={intelligenceData}
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
            incidentCoords={incidentCoords || [20.5937, 78.9629]} // Center of India as fallback
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
          
          <IntelligencePanel data={intelligenceData} incidentName={incidentName} />

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
