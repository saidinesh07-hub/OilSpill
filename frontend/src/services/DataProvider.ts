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
}

export class RealDataProvider extends BaseDataProvider {
  getMode(): 'DEMO' | 'REAL' {
    return 'REAL';
  }
}
