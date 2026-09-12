import React from 'react';
import { Compass, Wind, Waves, Gauge, ShieldAlert } from 'lucide-react';
import type { ForecastRun } from '../types';

interface ForecastControlsProps {
  forecastRun?: ForecastRun;
  environmentalProvenance?: any;
  selectedHorizonHours: number;
  onSelectHorizon?: (h: number) => void;
  visibleConfidenceLevels: number[];
  onToggleConfidenceLevel: (level: number) => void;
}

export const ForecastControls: React.FC<ForecastControlsProps> = ({
  forecastRun,
  environmentalProvenance,
  selectedHorizonHours,
  onSelectHorizon,
  visibleConfidenceLevels,
  onToggleConfidenceLevel,
}) => {
  const horizons = [6, 12, 24, 48];

  return (
    <div className="glass-panel rounded-xl p-4 space-y-4 border border-slate-700/80">
      <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
        <div className="flex items-center space-x-2">
          <Compass className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Trajectory Forecasting Subsystem
          </h3>
        </div>
        <span className="text-[10px] text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
          Lagrangian Ensemble (N=50)
        </span>
      </div>

      {/* Horizon Selection Buttons */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-[11px] font-semibold text-slate-300 block">
            Forecast Lead Time (Hours Ahead):
          </label>
          <span className="text-[10px] text-indigo-400 font-bold">
            Selected: +{selectedHorizonHours}h
          </span>
        </div>
        <div className="grid grid-cols-4 gap-1.5 text-xs">
          {horizons.map((h) => (
            <button
              key={h}
              onClick={() => onSelectHorizon && onSelectHorizon(h)}
              className={`px-2 py-1 rounded font-bold transition ${
                selectedHorizonHours === h
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-sm'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              +{h}h
            </button>
          ))}
        </div>
      </div>

      {/* Uncertainty Envelope Contours Toggle */}
      <div className="space-y-1.5">
        <label className="text-[11px] font-semibold text-slate-300 block">
          Containment Probability Envelopes:
        </label>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <button
            onClick={() => onToggleConfidenceLevel(0.50)}
            className={`px-2.5 py-1.5 rounded-lg border font-semibold flex flex-col items-center justify-center transition ${
              visibleConfidenceLevels.includes(0.50)
                ? 'bg-pink-950/60 border-pink-500 text-pink-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <span className="text-[10px] text-pink-400 uppercase">50% Core</span>
            <span>Best Guess</span>
          </button>

          <button
            onClick={() => onToggleConfidenceLevel(0.80)}
            className={`px-2.5 py-1.5 rounded-lg border font-semibold flex flex-col items-center justify-center transition ${
              visibleConfidenceLevels.includes(0.80)
                ? 'bg-blue-950/60 border-blue-500 text-blue-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <span className="text-[10px] text-blue-400 uppercase">80% Band</span>
            <span>Standard</span>
          </button>

          <button
            onClick={() => onToggleConfidenceLevel(0.95)}
            className={`px-2.5 py-1.5 rounded-lg border font-semibold flex flex-col items-center justify-center transition ${
              visibleConfidenceLevels.includes(0.95)
                ? 'bg-purple-950/60 border-purple-500 text-purple-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <span className="text-[10px] text-purple-400 uppercase">95% Outer</span>
            <span>Min Regret</span>
          </button>
        </div>
      </div>

      {/* MetOcean Forcing Physics Telemetry */}
      <div className="bg-slate-900/90 rounded-lg p-2.5 border border-slate-800 space-y-2 text-xs">
        <div className="text-[11px] font-bold text-slate-300 flex items-center justify-between">
          <span>MetOcean Transport Parameters</span>
          <span className="text-cyan-400 font-mono">
            {forecastRun?.engine_version || 'CMEMS + GFS'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
          <div className="flex items-center space-x-1.5">
            <Waves className="w-3.5 h-3.5 text-blue-400" />
            <span>Surface Current:</span>
            <span className="font-bold text-slate-200 font-mono">0.24 m/s</span>
          </div>

          <div className="flex items-center space-x-1.5">
            <Wind className="w-3.5 h-3.5 text-teal-400" />
            <span>10m Wind Leeway:</span>
            <span className="font-bold text-slate-200 font-mono">3.0% (15° Cor)</span>
          </div>

          <div className="flex items-center space-x-1.5">
            <Gauge className="w-3.5 h-3.5 text-indigo-400" />
            <span>Wave Stokes Drift:</span>
            <span className="font-bold text-slate-200 font-mono">0.04 m/s</span>
          </div>

          <div className="flex items-center space-x-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span>Diffusion Coeff:</span>
            <span className="font-bold text-slate-200 font-mono">2.0 m²/s</span>
          </div>
        </div>

        {environmentalProvenance && (
          <div className="mt-3 pt-3 border-t border-slate-700/60 space-y-2">
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
              Environmental Forcing Provenance
            </div>
            
            {['currents', 'winds'].map(type => {
              const prov = environmentalProvenance[type];
              if (!prov) return null;
              
              const isLive = prov.data_mode === 'LIVE_API';
              const isDemo = prov.data_mode === 'DEMO_DATA';
              
              let badgeColor = 'bg-slate-800 text-slate-400 border-slate-700';
              if (isLive) badgeColor = 'bg-emerald-950/50 text-emerald-400 border-emerald-500/50';
              else if (isDemo) badgeColor = 'bg-amber-950/50 text-amber-400 border-amber-500/50';
              else if (prov.data_mode === 'CACHED') badgeColor = 'bg-blue-950/50 text-blue-400 border-blue-500/50';
              
              return (
                <div key={type} className="flex flex-col gap-0.5 bg-slate-900/50 p-1.5 rounded">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-slate-300 font-semibold capitalize">{type}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-bold ${badgeColor}`}>
                      {prov.data_mode}
                    </span>
                  </div>
                  <div className="text-[9px] text-slate-500 flex flex-col">
                    <span><span className="text-slate-400">Source:</span> {prov.source}</span>
                    <span><span className="text-slate-400">Details:</span> {prov.data_provenance}</span>
                    <span><span className="text-slate-400">Retrieved:</span> {new Date(prov.data_vintage).toLocaleString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
