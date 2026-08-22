export interface SatelliteScene {
  scene_id: string;
  scene_name: string;
  source: string;
  sensor_mode: string;
  polarization: string[];
  acquisition_time: string;
  footprint_geojson: any;
  bbox: number[];
  is_synthetic: boolean;
  ingestion_status: string;
}

export interface SpillDetection {
  detection_id: string;
  observation_id: string;
  geom_geojson: any;
  centroid_lat: number;
  centroid_lon: number;
  area_km2: number;
  perimeter_km: number;
  predicted_class: 'oil_spill' | 'look_alike' | 'ship' | 'land' | 'sea_surface';
  confidence: number;
  lookalike_risk_score: number;
  morphology_features: {
    circularity: number;
    is_elongated_plume: boolean;
    pixel_count: number;
  };
  model_version: string;
  created_at: string;
}

export interface TemporalObservation {
  id: string;
  track_id: string;
  detection_id: string;
  observation_time: string;
  area_km2: number;
  area_delta_km2: number;
  centroid_displacement_m: number;
  observed_state: 'EXPANSION' | 'CONTRACTION' | 'FRAGMENTATION' | 'PERSISTENCE' | 'DISAPPEARANCE';
  advection_iou_match: number;
  detection?: SpillDetection;
}

export interface TrackedSlick {
  track_id: string;
  slick_name: string;
  first_seen: string;
  last_seen: string;
  current_status: string;
  total_area_km2: number;
  current_centroid_lat: number;
  current_centroid_lon: number;
  drift_speed_kmh: number;
  drift_heading_deg: number;
  growth_rate_km2_per_hr: number;
  latest_detection_id?: string;
  temporal_observations: TemporalObservation[];
}

export interface ForecastBand {
  id: string;
  forecast_run_id: string;
  horizon_hours: number;
  target_time: string;
  confidence_level: number; // 0.50, 0.80, 0.95
  geom_geojson: any;
  area_km2: number;
  centroid_lat: number;
  centroid_lon: number;
  mean_speed_kmh: number;
}

export interface ForecastRun {
  forecast_run_id: string;
  track_id: string;
  run_time: string;
  engine: string;
  engine_version: string;
  ensemble_size: number;
  wind_drift_factor: number;
  wind_deflection_angle_deg: number;
  diffusion_coefficient: number;
  summary: any;
  bands: ForecastBand[];
}

export interface Asset {
  asset_id: string;
  name: string;
  asset_type: 'protected_area' | 'fishery' | 'port' | 'beach' | 'wetland' | 'coastal_population';
  geom_geojson: any;
  centroid_lat: number;
  centroid_lon: number;
  sensitivity_weight: number;
  data_source: string;
  data_vintage: string;
  properties: any;
}

export interface ImpactAssessment {
  id: string;
  forecast_run_id: string;
  asset_id: string;
  horizon_hours: number;
  impact_probability: number;
  earliest_time_to_impact_hours: number;
  distance_to_slick_km: number;
  intersected_area_km2: number;
  exposure_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'NEGLIGIBLE';
  asset?: Asset;
}

export interface FactorBreakdown {
  weights: Record<string, number>;
  normalized_terms: {
    impact_prob: number;
    sensitivity: number;
    proximity: number;
    expansion: number;
    uncertainty: number;
    economic: number;
  };
  weighted_contributions: {
    impact_prob_pts: number;
    sensitivity_pts: number;
    proximity_pts: number;
    expansion_pts: number;
    uncertainty_pts: number;
    economic_pts: number;
  };
}

export interface RiskAssessment {
  risk_id: string;
  impact_assessment_id: string;
  total_risk_score: number;
  risk_category: 'VERY_HIGH' | 'HIGH' | 'MODERATE' | 'LOW';
  factor_impact_probability: number;
  factor_asset_sensitivity: number;
  factor_proximity: number;
  factor_slick_expansion: number;
  factor_forecast_uncertainty: number;
  factor_economic_exposure: number;
  factor_breakdown: FactorBreakdown;
  explanation_text: string;
  weight_config_version: string;
  calculated_at: string;
  impact?: ImpactAssessment;
}

export interface ResponseRecommendation {
  id: string;
  risk_id: string;
  priority_rank: number;
  action_category: string;
  recommendation_text: string;
  reasoning: string;
  time_window_hours: number;
  analyst_review_status: string;
  created_at: string;
}

export interface GroundedCitation {
  entity_type: string;
  entity_id: string;
  label: string;
  source_table: string;
  data_timestamp: string;
  value_snippet: string;
  coordinates?: [number, number];
}

export interface AssistantQueryResponse {
  answer: string;
  intent_detected: string;
  is_grounded: boolean;
  grounding_confidence: number;
  citations: GroundedCitation[];
  retrieved_data_summary: Record<string, any>;
  suggested_followups: string[];
}
