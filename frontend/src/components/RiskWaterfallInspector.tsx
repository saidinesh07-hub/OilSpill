import React, { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import type { RiskAssessment } from '../types';

interface RiskWaterfallInspectorProps {
  riskAssessment?: RiskAssessment;
}

export const RiskWaterfallInspector: React.FC<RiskWaterfallInspectorProps> = ({
  riskAssessment,
}) => {
  const [showFormula, setShowFormula] = useState(false);

  if (!riskAssessment) {
    return (
      <div className="glass-panel rounded-xl p-4 text-xs text-slate-400 text-center">
        No active risk assessment selected.
      </div>
    );
  }

  const score = riskAssessment.total_risk_score;
  const category = riskAssessment.risk_category;
  const contrib = riskAssessment.factor_breakdown?.weighted_contributions || {
    impact_prob_pts: 25.0,
    sensitivity_pts: 22.0,
    proximity_pts: 14.5,
    expansion_pts: 8.0,
    uncertainty_pts: 6.5,
    economic_pts: 8.0,
  };

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case 'VERY_HIGH':
        return 'bg-red-500/20 text-red-400 border-red-500/40';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'MODERATE':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
    }
  };

  const factors = [
    { label: 'P(Impact)', points: contrib.impact_prob_pts, max: 28, color: 'bg-red-500' },
    { label: 'Ecological Sensitivity', points: contrib.sensitivity_pts, max: 22, color: 'bg-emerald-500' },
    { label: 'Proximity Decay', points: contrib.proximity_pts, max: 18, color: 'bg-orange-500' },
    { label: 'Slick Growth Rate', points: contrib.expansion_pts, max: 12, color: 'bg-cyan-500' },
    { label: 'Forecast Uncertainty', points: contrib.uncertainty_pts, max: 10, color: 'bg-purple-500' },
    { label: 'Economic Exposure', points: contrib.economic_pts, max: 10, color: 'bg-blue-500' },
  ];

  return (
    <div className="glass-panel rounded-xl p-4 space-y-3.5 border border-slate-700/80">
      {/* Header & Total Score */}
      <div className="flex items-center justify-between border-b border-slate-700/60 pb-2.5">
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Explainable Risk Engine
          </h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${getCategoryBadge(category)}`}>
            {category} RISK
          </span>
          <span className="text-base font-extrabold text-slate-100 font-mono">
            {score.toFixed(1)}<span className="text-xs font-normal text-slate-400">/100</span>
          </span>
        </div>
      </div>

      {/* 6-Factor Decomposed Waterfall Contributions */}
      <div className="space-y-2">
        <div className="text-[11px] font-semibold text-slate-300 flex justify-between">
          <span>Contributing Risk Factors (Decomposed Points):</span>
          <button
            onClick={() => setShowFormula(!showFormula)}
            className="text-blue-400 hover:text-blue-300 text-[10px] flex items-center space-x-1"
          >
            <span>Formula Inspector</span>
            {showFormula ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>

        <div className="space-y-1.5">
          {factors.map((f, i) => {
            const pct = Math.min(100, Math.max(0, (f.points / f.max) * 100));
            return (
              <div key={i} className="text-xs">
                <div className="flex justify-between text-[11px] text-slate-300 mb-0.5">
                  <span>{f.label}</span>
                  <span className="font-mono font-semibold text-slate-200">
                    +{f.points.toFixed(1)} <span className="text-[10px] text-slate-500">/ {f.max}pts</span>
                  </span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${f.color} transition-all duration-500`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Expandable Inspectable Formula */}
      {showFormula && (
        <div className="bg-slate-900/90 rounded-lg p-2.5 border border-slate-800 text-[10px] font-mono text-slate-300 space-y-1.5">
          <div className="font-bold text-cyan-400">Analytical Hierarchy Process (AHP) Weight Schema:</div>
          <div className="text-slate-400 leading-relaxed">
            Risk = 0.28·P(impact) + 0.22·Severity + 0.18·Proximity + 0.12·Expansion + 0.10·(1-Confidence) + 0.10·Economic
          </div>
          <div className="text-[9px] text-slate-500">
            Schema Version: {riskAssessment.weight_config_version} • All terms normalized [0..1]
          </div>
        </div>
      )}

      {/* Grounded Natural Language Explanation Prose */}
      <div className="bg-blue-950/20 border border-blue-900/40 rounded-lg p-2.5 text-xs text-slate-300 leading-relaxed">
        <p>{riskAssessment.explanation_text}</p>
      </div>
    </div>
  );
};
