import React from 'react';
import { CheckCircle, ShieldAlert, Navigation } from 'lucide-react';
import type { CorrelationCandidate } from '../types';

interface CorrelationPanelProps {
  candidate: CorrelationCandidate;
  onClose?: () => void;
}

export const CorrelationPanel: React.FC<CorrelationPanelProps> = ({ candidate, onClose }) => {
  const { evidence } = candidate;

  // Formatting helpers
  const classificationColor = 
    candidate.classification === 'HIGHLY_RELEVANT' ? 'text-red-400' : 
    candidate.classification === 'POTENTIALLY_RELEVANT' ? 'text-amber-400' : 'text-slate-400';

  const classificationBg = 
    candidate.classification === 'HIGHLY_RELEVANT' ? 'bg-red-500/20 border-red-500/50' : 
    candidate.classification === 'POTENTIALLY_RELEVANT' ? 'bg-amber-500/20 border-amber-500/50' : 'bg-slate-500/20 border-slate-500/50';

  return (
    <div className="flex flex-col bg-slate-800/90 p-4 rounded-lg border border-slate-700 shadow-xl w-full">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-bold text-slate-100 text-sm tracking-wide uppercase">Correlation Analysis</h3>
          <p className="text-xs text-slate-400">{candidate.name} ({candidate.mmsi || 'N/A'})</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        )}
      </div>

      <div className={`p-3 rounded border mb-4 flex items-center justify-between ${classificationBg}`}>
        <div>
          <div className="text-[10px] text-slate-300 uppercase tracking-widest font-semibold mb-0.5">Correlation Score</div>
          <div className={`text-2xl font-black ${classificationColor}`}>
            {candidate.correlation_score.toFixed(0)} <span className="text-sm font-normal text-slate-400">/ 100</span>
          </div>
        </div>
        <div className={`text-xs font-bold px-2 py-1 rounded bg-slate-900/50 ${classificationColor}`}>
          {candidate.classification.replace('_', ' ')}
        </div>
      </div>

      <div className="space-y-3 mb-4">
        <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 border-b border-slate-700/50 pb-1">Evidence Breakdown</h4>
        
        {/* Spatial */}
        {evidence.spatial_proximity && (
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-300">Spatial Proximity</span>
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-[10px]">{evidence.spatial_proximity.distance_km.toFixed(1)} km</span>
              <span className="font-mono text-blue-300 w-8 text-right">{evidence.spatial_proximity.score}/30</span>
            </div>
          </div>
        )}

        {/* Temporal */}
        {evidence.temporal_proximity && (
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-300">Temporal Proximity</span>
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-[10px]">{evidence.temporal_proximity.difference_hours.toFixed(1)} hrs</span>
              <span className="font-mono text-blue-300 w-8 text-right">{evidence.temporal_proximity.score}/25</span>
            </div>
          </div>
        )}

        {/* Pre-spill presence */}
        {evidence.pre_spill_presence && (
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-300">Pre-spill Presence</span>
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-[10px]">{evidence.pre_spill_presence.present_before_detection ? 'Yes' : 'No'}</span>
              <span className="font-mono text-blue-300 w-8 text-right">{evidence.pre_spill_presence.score}/15</span>
            </div>
          </div>
        )}

        {/* Movement */}
        {evidence.movement_data_quality && (
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-300">Movement Data Quality</span>
            <span className="font-mono text-blue-300 w-8 text-right">{evidence.movement_data_quality.score}/10</span>
          </div>
        )}

        {/* Type */}
        {evidence.vessel_type && (
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-300">Vessel Type</span>
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-[10px] capitalize">{evidence.vessel_type.type}</span>
              <span className="font-mono text-blue-300 w-8 text-right">{evidence.vessel_type.score}/10</span>
            </div>
          </div>
        )}

        {/* Freshness */}
        {evidence.freshness && (
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-300">Data Freshness</span>
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-[10px]">{evidence.freshness.status}</span>
              <span className="font-mono text-blue-300 w-8 text-right">{evidence.freshness.score}/10</span>
            </div>
          </div>
        )}
      </div>

      <div className="bg-slate-900/60 p-3 rounded-md mb-4 border border-slate-700/50">
        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Why this vessel is relevant</h4>
        <ul className="text-xs text-slate-300 space-y-1">
          {evidence.pre_spill_presence?.present_before_detection && (
            <li className="flex gap-1.5 items-start"><CheckCircle className="w-3.5 h-3.5 text-emerald-400 mt-0.5" /> Present before spill detection</li>
          )}
          {evidence.spatial_proximity && (
            <li className="flex gap-1.5 items-start"><Navigation className="w-3.5 h-3.5 text-sky-400 mt-0.5" /> {evidence.spatial_proximity.distance_km.toFixed(1)} km from detected slick</li>
          )}
          {evidence.temporal_proximity && (
            <li className="flex gap-1.5 items-start"><CheckCircle className="w-3.5 h-3.5 text-blue-400 mt-0.5" /> Observation within {evidence.temporal_proximity.difference_hours.toFixed(1)} hours of detection</li>
          )}
          {evidence.vessel_type && evidence.vessel_type.type.toLowerCase().includes('tanker') && (
            <li className="flex gap-1.5 items-start"><CheckCircle className="w-3.5 h-3.5 text-purple-400 mt-0.5" /> High-risk vessel classification (Tanker)</li>
          )}
        </ul>
      </div>

      <div className="mt-auto bg-amber-900/20 border border-amber-700/50 rounded p-2.5 flex items-start gap-2">
        <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-[10px] text-amber-200 leading-snug">
          <b>Analyst Warning:</b> Correlation indicates evidence consistency and does not establish causality. Do not use for attribution without external authoritative confirmation.
        </p>
      </div>
    </div>
  );
};
