import React from 'react';
import { Target, Clock, MapPin } from 'lucide-react';
import type { ImpactAssessment } from '../types';

interface AssetImpactTableProps {
  impacts: ImpactAssessment[];
  onSelectImpact?: (impact: ImpactAssessment) => void;
  onFlyTo?: (coords: [number, number]) => void;
}

export const AssetImpactTable: React.FC<AssetImpactTableProps> = ({
  impacts,
  onSelectImpact,
  onFlyTo,
}) => {
  const getExposureBadge = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-400 border-red-500/40';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'MODERATE':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="glass-panel rounded-xl p-4 space-y-3 border border-slate-700/80">
      <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
        <div className="flex items-center space-x-2">
          <Target className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Threatened Coastal Assets & Arrival Windows
          </h3>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">
          {impacts.length} Assets Analyzed
        </span>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar pr-1">
        {impacts.length === 0 ? (
          <div className="text-xs text-slate-400 text-center py-4">
            No coastal assets currently in trajectory intersection path.
          </div>
        ) : (
          impacts.map((imp) => {
            const asset = imp.asset;
            return (
              <div
                key={imp.id}
                onClick={() => onSelectImpact && onSelectImpact(imp)}
                className="bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-slate-700 rounded-lg p-2.5 cursor-pointer transition space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1.5 font-bold text-slate-100 text-xs">
                    <span>{asset?.name || 'Coastal Zone'}</span>
                    {asset && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onFlyTo) onFlyTo([asset.centroid_lon, asset.centroid_lat]);
                        }}
                        className="text-slate-400 hover:text-cyan-400"
                        title="Jump to asset on map"
                      >
                        <MapPin className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${getExposureBadge(imp.exposure_level)}`}>
                    {imp.exposure_level}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-400">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3 text-indigo-400" />
                    <span>Arrival:</span>
                    <span className="font-bold text-slate-200 font-mono">
                      {imp.earliest_time_to_impact_hours.toFixed(1)}h
                    </span>
                  </div>

                  <div>
                    <span>Impact Prob:</span>{' '}
                    <span className="font-bold text-amber-400 font-mono">
                      {(imp.impact_probability * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div>
                    <span>Distance:</span>{' '}
                    <span className="font-bold text-slate-200 font-mono">
                      {imp.distance_to_slick_km.toFixed(1)} km
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
