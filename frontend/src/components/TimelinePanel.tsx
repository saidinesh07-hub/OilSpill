import React from 'react';
import { Clock, Calendar, TrendingUp } from 'lucide-react';
import type { TrackedSlick } from '../types';

interface TimelinePanelProps {
  activeTrack?: TrackedSlick;
  selectedHorizonHours: number;
  onSelectHorizon: (h: number) => void;
  currentStep: number;
  onSelectStep: (stepIndex: number) => void;
}

export const TimelinePanel: React.FC<TimelinePanelProps> = ({
  activeTrack,
  selectedHorizonHours,
  onSelectHorizon,
  currentStep,
  onSelectStep,
}) => {
  const temporalObs = activeTrack?.temporal_observations || [];
  const horizons = [6, 12, 24, 48];

  return (
    <div className="glass-panel border-t border-slate-700/80 px-6 py-3 flex items-center justify-between z-20">
      {/* Time Controls & Status */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Temporal Intelligence Scrubber
          </span>
        </div>

        {/* Historical Passes Buttons */}
        <div className="flex items-center space-x-1.5 bg-slate-900/90 border border-slate-800 rounded-lg p-1">
          {temporalObs.map((obs, idx) => (
            <button
              key={obs.id}
              onClick={() => onSelectStep(idx)}
              className={`px-3 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition ${
                currentStep === idx
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              <Calendar className="w-3 h-3" />
              <span>Pass {idx + 1} ({new Date(obs.observation_time).toLocaleDateString()})</span>
              <span className="text-[10px] px-1 py-0.2 bg-slate-800 rounded text-cyan-300">
                {obs.area_km2.toFixed(1)} km²
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Trajectory Forecast Horizons Selector */}
      <div className="flex items-center space-x-3">
        <span className="text-xs text-slate-400 font-semibold flex items-center space-x-1">
          <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
          <span>Forecast Horizon:</span>
        </span>
        <div className="flex items-center space-x-1 bg-slate-900/90 border border-slate-800 rounded-lg p-1">
          {horizons.map((h) => (
            <button
              key={h}
              onClick={() => onSelectHorizon(h)}
              className={`px-3 py-1 rounded text-xs font-bold transition ${
                selectedHorizonHours === h
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              +{h} Hours
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
