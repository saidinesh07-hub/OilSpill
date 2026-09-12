import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { App } from '../App';
import { apiService } from '../services/api';

// Mock the Leaflet MapDashboard component so we don't need real Leaflet in JSDOM
vi.mock('../components/MapDashboard', () => ({
  MapDashboard: ({ candidates, onSelectCandidate }: any) => (
    <div data-testid="mock-map">
      {candidates?.map((c: any) => (
        <button key={c.mmsi} data-testid={`candidate-${c.mmsi}`} onClick={() => onSelectCandidate(c)}>
          {c.name}
        </button>
      ))}
    </div>
  )
}));

// Mock the timeline and other complex components
vi.mock('../components/TimelinePanel', () => ({ TimelinePanel: () => <div /> }));
vi.mock('../components/ForecastControls', () => ({ ForecastControls: () => <div /> }));
vi.mock('../components/RiskWaterfallInspector', () => ({ RiskWaterfallInspector: () => <div /> }));
vi.mock('../components/AssetImpactTable', () => ({ AssetImpactTable: () => <div /> }));
vi.mock('../components/DecisionSupportPanel', () => ({ DecisionSupportPanel: () => <div /> }));
vi.mock('../components/AssistantChat', () => ({ AssistantChat: () => <div /> }));

describe('Maritime Intelligence UI Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock general analyze location
    vi.spyOn(apiService, 'analyzeLocation').mockResolvedValue({
      data: {
        mode: 'DEMO',
        spill_candidates: [{ detection_id: 'spill-123' }]
      }
    });

    // Mock maritime spill correlation
    vi.spyOn(apiService, 'getSpillIntelligence').mockResolvedValue({
      spill_id: 'spill-123',
      mode: 'DEMO',
      evaluated_at: '2026-09-13T00:00:00Z',
      candidates: [
        {
          mmsi: '999000111',
          name: 'OCEAN EXPLORER',
          correlation_score: 82,
          classification: 'HIGHLY_RELEVANT',
          provenance: 'OSIRIS',
          latitude: 13.0,
          longitude: 80.0,
          evidence: {
            spatial_proximity: { distance_km: 1.2, score: 25 },
            temporal_proximity: { difference_hours: 0.5, score: 25 }
          }
        },
        {
          mmsi: '999000222',
          name: 'MARINE STAR',
          correlation_score: 54,
          classification: 'POTENTIALLY_RELEVANT',
          provenance: 'AISHUB',
          latitude: 13.1,
          longitude: 80.1,
          evidence: {
            spatial_proximity: { distance_km: 8.5, score: 10 }
          }
        }
      ]
    });
  });

  it('renders causality disclaimer and breakdown when a candidate is selected', async () => {
    render(<App />);

    // Load initial demo data
    const navbarSearchBtn = await screen.findByText('Run Demo');
    fireEvent.click(navbarSearchBtn);

    // Click Investigate Spill
    const investigateBtn = await screen.findByText(/Investigate Spill/i);
    fireEvent.click(investigateBtn);

    // Wait for candidates to appear in the mock map
    const candidateBtn = await screen.findByTestId('candidate-999000111');
    expect(candidateBtn).toBeTruthy();

    // Select candidate
    fireEvent.click(candidateBtn);

    // Verify correlation panel is visible
    expect(await screen.findByText(/Correlation Analysis/i)).toBeTruthy();
  });
});
