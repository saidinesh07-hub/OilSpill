import { apiService } from './api';
import { demoPayload } from './demoData';

export interface DataProvider {
  initialize(lat: number, lon: number, name: string): Promise<void>;
  getMode(): 'DEMO' | 'REAL';
  
  // Data access methods
  getSatelliteData(): any;
  getOceanographicData(): any;
  getMeteorologicalData(): any;
  getAisData(): any;
  getSpillDetection(): any;
  getPrediction(): any;
  getAssets(): any;
  getImpacts(): any;
  getRecommendations(): any;
  getActiveTrack(): any;
  getPossibleSources(): any;
  getStageStatus(): any;
  getWarnings(): string[];
  
  // For raw payload access if needed by old components
  getRawPayload(): any;
  
  // Dynamic API calls
  getMaritimeVessels(minLat?: number, maxLat?: number, minLon?: number, maxLon?: number): Promise<any>;
  getSpillIntelligence(spillId: string): Promise<any>;
}

abstract class BaseDataProvider implements DataProvider {
  protected data: any = null;
  
  abstract getMode(): 'DEMO' | 'REAL';
  
  async initialize(lat: number, lon: number, name: string): Promise<void> {
    try {
      // Assuming apiService.analyzeLocation supports passing the mode.
      const response = await apiService.analyzeLocation(lat, lon, name, this.getMode());
      if (response && response.data) {
        this.data = response.data;
      } else {
        throw new Error("Invalid response from server");
      }
    } catch (err) {
      console.error(`Error initializing ${this.getMode()} provider:`, err);
      throw err;
    }
  }

  getSatelliteData() { return this.data?.satellite?.products || []; }
  getOceanographicData() { return this.data?.weather || null; }
  getMeteorologicalData() { return this.data?.weather || null; } // Often combined
  getAisData() { return this.data?.vessels?.vessels || []; }
  getSpillDetection() { return this.data?.spill_candidates || []; }
  getPrediction() { return this.data?.forecast_bands || []; }
  getAssets() { return this.data?.assets || []; }
  getImpacts() { return this.data?.impacts || []; }
  getRecommendations() { return this.data?.recommendations || []; }
  getActiveTrack() { return this.data?.active_track || null; }
  getPossibleSources() { return this.data?.possible_sources || []; }
  getStageStatus() { return this.data?.stage_status || {}; }
  getWarnings() { return this.data?.warnings || []; }
  getRawPayload() { return this.data; }
  
  abstract getMaritimeVessels(minLat?: number, maxLat?: number, minLon?: number, maxLon?: number): Promise<any>;
  abstract getSpillIntelligence(spillId: string): Promise<any>;
}

export class DemoDataProvider extends BaseDataProvider {
  getMode(): 'DEMO' | 'REAL' {
    return 'DEMO';
  }

  async initialize(lat: number, lon: number, name: string): Promise<void> {
    try {
      // Offline deterministic DEMO data, no API calls
      console.log(`[DEMO MODE] Loading synthetic payload for ${name} at ${lat}, ${lon}`);
      this.data = JSON.parse(JSON.stringify(demoPayload));
    } catch (err) {
      console.error(`Error initializing ${this.getMode()} provider:`, err);
      throw err;
    }
  }

  async getMaritimeVessels(_minLat?: number, _maxLat?: number, _minLon?: number, _maxLon?: number): Promise<any> {
    // Demo implementation
    return {
      status: 'SUCCESS',
      provider: 'DEMO_DATA',
      fallback_used: true,
      fallback_reason: 'DEMO_MODE',
      retrieved_at: new Date().toISOString(),
      vessel_count: 3,
      vessels: [
        {
          mmsi: '999000111',
          name: 'DEMO TANKER ALPHA',
          vessel_type: 'Tanker',
          latitude: 13.26,
          longitude: 80.36,
          speed_knots: 12.5,
          course_deg: 45,
          provider: 'DEMO_DATA',
          data_status: 'DEMO',
          freshness: { source: 'DEMO_DATA', retrieved_at: new Date().toISOString(), freshness_status: 'FRESH' }
        },
        {
          mmsi: '999000222',
          name: 'DEMO CARGO BETA',
          vessel_type: 'Cargo',
          latitude: 13.20,
          longitude: 80.40,
          speed_knots: 15.0,
          course_deg: 180,
          provider: 'DEMO_DATA',
          data_status: 'DEMO',
          freshness: { source: 'DEMO_DATA', retrieved_at: new Date().toISOString(), freshness_status: 'RECENT' }
        },
        {
          mmsi: '999000333',
          name: 'DEMO PASSENGER GAMMA',
          vessel_type: 'Passenger',
          latitude: 13.30,
          longitude: 80.30,
          speed_knots: 20.0,
          course_deg: 90,
          provider: 'DEMO_DATA',
          data_status: 'DEMO',
          freshness: { source: 'DEMO_DATA', retrieved_at: new Date().toISOString(), freshness_status: 'STALE' }
        }
      ]
    };
  }

  async getSpillIntelligence(spillId: string): Promise<any> {
    const fb_geom = {
        "type": "Polygon",
        "coordinates": [[
            [80.30, 13.22],
            [80.39, 13.21],
            [80.41, 13.27],
            [80.32, 13.26],
            [80.30, 13.22],
        ]]
    };
    
    return {
      spill_id: spillId,
      mode: 'DEMO',
      evaluated_at: new Date().toISOString(),
      candidates: [
        {
          mmsi: '999000111',
          name: 'DEMO TANKER ALPHA',
          correlation_score: 85,
          classification: 'HIGHLY_RELEVANT',
          provenance: 'DEMO_DATA',
          latitude: 13.26,
          longitude: 80.36,
          vessel_type: 'Tanker',
          timestamp: new Date().toISOString(),
          evidence: {
            spatial_proximity: { distance_km: 1.2, score: 25 },
            temporal_proximity: { difference_hours: 0.5, score: 25 },
            pre_spill_presence: { present_before_detection: true, score: 15 },
            movement_data_quality: { score: 10 },
            vessel_type: { type: 'tanker', score: 10 },
            freshness: { status: 'FRESH', score: 10 }
          }
        }
      ],
      forecast_bands: [
          {
              "id": "demo-band-1",
              "forecast_run_id": "demo-run-1",
              "horizon_hours": 24,
              "confidence_level": 0.95,
              "target_time": new Date(Date.now() + 24*3600*1000).toISOString(),
              "geom_geojson": fb_geom,
              "area_km2": 8.4,
              "centroid_lat": 13.25,
              "centroid_lon": 80.35,
              "mean_speed_kmh": 1.1
          }
      ],
      active_track: {
          "track_id": "demo-track-1",
          "slick_name": "DEMO SLICK ALPHA",
          "current_status": "ACTIVE",
          "total_area_km2": 4.2,
          "current_centroid_lat": 13.25,
          "current_centroid_lon": 80.35,
          "drift_speed_kmh": 1.1,
          "drift_heading_deg": 45.0,
      },
      assets: [
          {
              "asset_id": "demo-asset-1",
              "name": "DEMO Coral Reef",
              "asset_type": "protected_area",
              "geom_geojson": {
                  "type": "Point",
                  "coordinates": [80.39, 13.26]
              },
              "centroid_lat": 13.26,
              "centroid_lon": 80.39,
              "sensitivity_weight": 4.5,
              "data_source": "DEMO",
              "data_vintage": "2023-01-01T00:00:00Z",
              "properties": {}
          }
      ],
      impacts: [
          {
              "id": "demo-impact-1",
              "forecast_run_id": "demo-run-1",
              "asset_id": "demo-asset-1",
              "horizon_hours": 24,
              "impact_probability": 0.85,
              "earliest_time_to_impact_hours": 14,
              "distance_to_slick_km": 2.5,
              "intersected_area_km2": 1.2,
              "exposure_level": "HIGH",
              "asset": {
                  "asset_id": "demo-asset-1",
                  "name": "DEMO Coral Reef",
                  "asset_type": "protected_area",
                  "centroid_lat": 13.26,
                  "centroid_lon": 80.39
              }
          }
      ],
      recommendations: [
          {
              "id": "demo-rec-1",
              "risk_id": "demo-risk-1",
              "priority_rank": 1,
              "action_category": "CONTAINMENT",
              "recommendation_text": "Deploy containment booms near DEMO Coral Reef",
              "reasoning": "High probability of impact within 14 hours.",
              "time_window_hours": 12
          }
      ]
    };
  }
}

export class RealDataProvider extends BaseDataProvider {
  getMode(): 'DEMO' | 'REAL' {
    return 'REAL';
  }

  async getMaritimeVessels(minLat?: number, maxLat?: number, minLon?: number, maxLon?: number): Promise<any> {
    return apiService.getVessels(minLat, maxLat, minLon, maxLon);
  }

  async getSpillIntelligence(spillId: string): Promise<any> {
    return apiService.getSpillIntelligence(spillId);
  }
}
