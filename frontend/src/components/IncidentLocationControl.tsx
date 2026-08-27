import React, { useState } from 'react';
import { MapPin, Search, Server, ShieldAlert } from 'lucide-react';

interface IncidentLocationControlProps {
  currentLocationName?: string;
  currentCoords?: [number, number];
  dataMode?: string;
  isLoading?: boolean;
  errorMessage?: string;
  onLocationChange: (lat: number, lon: number, name: string) => void;
}

export const IncidentLocationControl: React.FC<IncidentLocationControlProps> = ({
  currentLocationName,
  currentCoords,
  dataMode = 'DEMO_DATA',
  isLoading = false,
  errorMessage,
  onLocationChange,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [localError, setLocalError] = useState('');

  const handleSearch = async () => {
    setLocalError('');
    const q = searchQuery.trim();
    if (!q) {
      setLocalError('Enter a place name or lat, lon');
      return;
    }

    const coordsMatch = q.match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/);
    if (coordsMatch) {
      onLocationChange(parseFloat(coordsMatch[1]), parseFloat(coordsMatch[2]), q);
      return;
    }

    try {
      const res = await fetch(`/api/v1/location/geocode?q=${encodeURIComponent(q)}`);
      const json = await res.json();
      if (!json.success || !json.data?.latitude) {
        setLocalError(json.data?.message || 'Location not found');
        return;
      }
      onLocationChange(json.data.latitude, json.data.longitude, json.data.name || q);
    } catch {
      setLocalError('Geocoding request failed');
    }
  };

  const bannerError = localError || errorMessage || '';
  const isRealMode = dataMode === 'REAL' || dataMode === 'REAL_DATA';
  const coordLabel = currentCoords
    ? `${currentCoords[0].toFixed(4)}, ${currentCoords[1].toFixed(4)}`
    : '';

  return (
    <div className="flex flex-col bg-slate-800/80 p-3 rounded-lg border border-slate-700 w-[300px]">
      <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1">
        <MapPin className="w-3.5 h-3.5 text-blue-400" />
        INCIDENT LOCATION
      </div>

      <div className="flex gap-2 mb-2">
        <input
          type="text"
          placeholder="Any place or lat, lon"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              void handleSearch();
            }
          }}
          className="flex-1 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-400"
        />
        <button
          type="button"
          onClick={() => {
            void handleSearch();
          }}
          disabled={isLoading}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded px-2 py-1 flex items-center justify-center transition-colors"
        >
          <Search className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="text-[10px] text-slate-300 mb-2">
        <span className="font-semibold text-slate-100">Selected: </span>
        {currentLocationName || 'Search a location to begin'}
        <br />
        <span className="text-slate-400">{coordLabel}</span>
      </div>

      {isRealMode ? (
        <div className="text-[10px] p-1.5 rounded text-center font-bold flex items-center justify-center gap-1 bg-emerald-900/50 text-emerald-400 border border-emerald-800">
          <Server className="w-3 h-3" />
          REAL DATA MODE
        </div>
      ) : (
        <div className="text-[10px] p-1.5 rounded text-center font-bold flex items-center justify-center gap-1 bg-blue-900/50 text-blue-400 border border-blue-800">
          <ShieldAlert className="w-3 h-3" />
          DEMO / SYNTHETIC DATA
        </div>
      )}

      {bannerError ? (
        <div className="mt-2 text-[10px] text-amber-300 bg-amber-950/40 border border-amber-800 rounded p-1.5">
          {bannerError}
        </div>
      ) : null}
    </div>
  );
};
