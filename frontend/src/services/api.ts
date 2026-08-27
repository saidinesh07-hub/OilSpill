import type {
  SatelliteScene,
  TrackedSlick,
  ForecastRun,
  Asset,
  ImpactAssessment,
  RiskAssessment,
  ResponseRecommendation,
  AssistantQueryResponse,
} from '../types';

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData?.detail?.error?.message || `API Error: ${res.statusText}`);
  }

  const json = await res.json();
  return json.data !== undefined ? json.data : json;
}

export const apiService = {
  // Health
  getHealth: () => fetchJson<any>('/health'),

  // Scenes
  getScenes: () => fetchJson<SatelliteScene[]>('/scenes'),
  getScene: (id: string) => fetchJson<SatelliteScene>(`/scenes/${id}`),

  // Detections
  getDetectionsGeoJSON: (minConfidence: number = 0.0) =>
    fetchJson<any>(`/detections/geojson?min_confidence=${minConfidence}`),

  // Tracks
  getTracks: () => fetchJson<TrackedSlick[]>('/tracks'),
  getTrack: (trackId: string) => fetchJson<TrackedSlick>(`/tracks/${trackId}`),
  getTrackHistory: (trackId: string) => fetchJson<any[]>(`/tracks/${trackId}/history`),

  // Forecasts
  getLatestForecast: (trackId?: string) =>
    fetchJson<ForecastRun>(`/forecasts/latest${trackId ? `?track_id=${trackId}` : ''}`),
  getForecastGeoJSON: (forecastRunId: string, horizonHours?: number, confidenceLevel?: number) => {
    const params = new URLSearchParams();
    if (horizonHours !== undefined) params.append('horizon_hours', horizonHours.toString());
    if (confidenceLevel !== undefined) params.append('confidence_level', confidenceLevel.toString());
    return fetchJson<any>(`/forecasts/${forecastRunId}/geojson?${params.toString()}`);
  },

  // Environmental
  getMetOceanSummary: () => fetchJson<any>('/environmental/metocean_summary'),

  // Assets
  getAssets: () => fetchJson<Asset[]>('/assets'),
  getAssetsGeoJSON: (assetType?: string) =>
    fetchJson<any>(`/assets/geojson${assetType ? `?asset_type=${assetType}` : ''}`),

  // Impact & Risk
  getImpacts: (forecastRunId: string) => fetchJson<ImpactAssessment[]>(`/impacts/${forecastRunId}`),
  getRiskAssessment: (impactId: string) => fetchJson<RiskAssessment>(`/risk/${impactId}`),
  getTrackRecommendations: (trackId: string) =>
    fetchJson<ResponseRecommendation[]>(`/recommendations/${trackId}`),
  getRiskSensitivity: () => fetchJson<any>('/risk/analysis/sensitivity'),

  // AI Assistant
  queryAssistant: (question: string, trackId?: string) =>
    fetchJson<AssistantQueryResponse>('/assistant/query', {
      method: 'POST',
      body: JSON.stringify({ question, track_id: trackId }),
    }),

  // Pipeline Seeding
  seedCaseStudies: () =>
    fetchJson<any>('/pipeline/case_studies/seed', {
      method: 'POST',
    }),
    
  // Intelligence Report
  getIntelligence: (incidentId: string | number) => 
    fetchJson<any>(`/location/${incidentId}/intelligence`),
    
  // Unified Location Analysis
  analyzeLocation: (lat: number, lon: number, name: string, mode: 'DEMO' | 'REAL') =>
    fetchJson<any>('/location/analyze', {
      method: 'POST',
      body: JSON.stringify({ latitude: lat, longitude: lon, name, mode }),
    }),
};
