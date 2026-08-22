import React from 'react';
import { ShieldCheck, Anchor, Eye, AlertOctagon, Info } from 'lucide-react';
import type { ResponseRecommendation } from '../types';

interface DecisionSupportPanelProps {
  recommendations: ResponseRecommendation[];
}

export const DecisionSupportPanel: React.FC<DecisionSupportPanelProps> = ({
  recommendations,
}) => {
  const getActionIcon = (action: string) => {
    switch (action) {
      case 'CONTAINMENT_DEPLOYMENT':
        return <Anchor className="w-4 h-4 text-red-400" />;
      case 'AERIAL_VERIFICATION':
        return <Eye className="w-4 h-4 text-cyan-400" />;
      case 'SHORELINE_DEFENSE':
        return <ShieldCheck className="w-4 h-4 text-amber-400" />;
      default:
        return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div className="glass-panel rounded-xl p-4 space-y-3 border border-slate-700/80">
      <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Prioritized Response Guidance
          </h3>
        </div>
        <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
          Decision Support Advisory
        </span>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto custom-scrollbar pr-1">
        {recommendations.length === 0 ? (
          <div className="text-xs text-slate-400 text-center py-4">
            No active emergency response recommendations generated.
          </div>
        ) : (
          recommendations.map((rec) => (
            <div
              key={rec.id}
              className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 space-y-1.5 text-xs"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600/30 border border-blue-500/50 flex items-center justify-center font-bold text-[10px] text-blue-400">
                    #{rec.priority_rank}
                  </span>
                  <div className="flex items-center space-x-1 font-bold text-slate-200">
                    {getActionIcon(rec.action_category)}
                    <span>{rec.action_category.replace(/_/g, ' ')}</span>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-cyan-400 bg-slate-800 px-2 py-0.5 rounded">
                  Window: {rec.time_window_hours.toFixed(1)}h
                </span>
              </div>

              <p className="text-slate-300 text-[11px] leading-relaxed">
                {rec.recommendation_text}
              </p>

              <div className="text-[10px] text-slate-500 italic">
                <b>Reasoning:</b> {rec.reasoning}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Advisory Disclaimer */}
      <div className="text-[9px] text-slate-500 border-t border-slate-800 pt-2 flex items-center space-x-1.5">
        <AlertOctagon className="w-3 h-3 text-amber-500 shrink-0" />
        <span>
          Advisory guidance for incident commanders. Does not autonomously dispatch operational units.
        </span>
      </div>
    </div>
  );
};
