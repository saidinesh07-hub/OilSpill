import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ForecastControls } from '../components/ForecastControls';

describe('ForecastControls Provenance Rendering', () => {
  it('visibly distinguishes DEMO data from LIVE data', () => {
    const mockProvenanceDemo = {
      currents: {
        source: 'Copernicus Marine',
        data_mode: 'DEMO_DATA',
        data_provenance: 'SYNTHETIC',
        data_vintage: '2026-09-13T00:00:00Z'
      },
      winds: {
        source: 'NOAA GFS',
        data_mode: 'LIVE_API',
        data_provenance: 'Live CDS/GFS API',
        data_vintage: '2026-09-13T00:00:00Z'
      }
    };

    render(
      <ForecastControls 
        selectedHorizonHours={48} 
        visibleConfidenceLevels={[0.5, 0.8, 0.95]} 
        onToggleConfidenceLevel={() => {}} 
        environmentalProvenance={mockProvenanceDemo}
      />
    );
    
    // The panel should render "Environmental Forcing Provenance"
    expect(screen.getByText(/Environmental Forcing Provenance/i)).toBeTruthy();
    
    // It should render both data_modes distinctly
    expect(screen.getByText('DEMO_DATA')).toBeTruthy();
    expect(screen.getByText('LIVE_API')).toBeTruthy();
    
    // Check for source information
    expect(screen.getByText('Copernicus Marine')).toBeTruthy();
    expect(screen.getByText('NOAA GFS')).toBeTruthy();
  });
});
