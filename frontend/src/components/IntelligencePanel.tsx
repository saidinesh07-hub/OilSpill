import { Server, Ship, Factory, AlertTriangle, Satellite } from 'lucide-react';

export const IntelligencePanel = ({ data, incidentName }: { data: any; incidentName: string }) => {
  if (!data) {
    return (
      <div className="flex flex-col bg-slate-800/50 p-4 rounded-lg border border-slate-700 w-full mb-4">
        <div className="text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider">Intelligence Report</div>
        <div className="text-xs text-slate-400">Search a location to run analysis.</div>
      </div>
    );
  }

  const products = data.satellite?.products || [];
  const vessels = data.vessels?.vessels || [];
  const infrastructure = data.infrastructure?.infrastructure || [];
  const sources = data.possible_sources || [];
  const warnings = data.warnings || [];
  const isDemo = data.mode === 'DEMO';

  return (
    <div className="flex flex-col bg-slate-800/50 p-4 rounded-lg border border-slate-700 w-full mb-4 space-y-3">
      <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
        <Server className="w-4 h-4 text-blue-400" />
        {isDemo ? 'DEMO / SYNTHETIC' : 'REAL'} Intelligence: {incidentName}
      </div>

      <div className="bg-slate-900/50 p-3 rounded">
        <h4 className="text-xs font-semibold text-slate-400 flex items-center gap-1 mb-2">
          <Satellite className="w-3.5 h-3.5" /> SENTINEL-1
        </h4>
        <p className="text-[11px] text-slate-300 mb-2">{data.satellite?.message}</p>
        {products.length === 0 ? (
          <p className="text-xs text-amber-300">{data.satellite?.message || 'No satellite products.'}</p>
        ) : (
          <ul className="text-[10px] space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
            {products.slice(0, 5).map((p: any) => (
              <li key={p.product_id || p.scene_id} className="border-b border-slate-800 pb-1 text-slate-300">
                <div className="font-semibold text-slate-100">{p.scene_name || p.title}</div>
                <div>ID: {p.product_id || p.scene_id}</div>
                <div>Acquired: {p.acquisition_time || 'n/a'}</div>
                <div>Polarization: {p.polarisation || (p.polarization || []).join(',')}</div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-slate-900/50 p-3 rounded">
        <h4 className="text-xs font-semibold text-slate-400 mb-2">SPILL CANDIDATES</h4>
        {(data.spill_candidates || []).length === 0 ? (
          <p className="text-xs text-slate-500">
            No spill polygon produced. Catalogue search does not invent oil-spill geometry.
          </p>
        ) : (
          <p className="text-xs text-slate-300">
            {(data.spill_candidates || []).length} candidate(s)
            {isDemo ? ' — DEMO / SYNTHETIC' : ''}
          </p>
        )}
      </div>

      <div className="bg-slate-900/50 p-3 rounded">
        <h4 className="text-xs font-semibold text-slate-400 flex items-center gap-1 mb-2">
          <Ship className="w-3.5 h-3.5" /> VESSELS
        </h4>
        <p className="text-[10px] text-slate-400 mb-1">{data.vessels?.message}</p>
        {vessels.length === 0 ? (
          <p className="text-xs text-amber-300">{data.vessels?.message || 'LIVE VESSEL DATA UNAVAILABLE'}</p>
        ) : (
          <ul className="text-xs space-y-1 max-h-28 overflow-y-auto custom-scrollbar">
            {vessels.slice(0, 10).map((v: any, i: number) => (
              <li key={i} className="flex justify-between border-b border-slate-800 pb-1">
                <span className="text-slate-300 font-medium">{v.name}</span>
                <span className="text-slate-500">{v.source}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-slate-900/50 p-3 rounded">
        <h4 className="text-xs font-semibold text-slate-400 flex items-center gap-1 mb-2">
          <Factory className="w-3.5 h-3.5" /> INFRASTRUCTURE
        </h4>
        <p className="text-[10px] text-slate-400 mb-1">{data.infrastructure?.message}</p>
        {infrastructure.length === 0 ? (
          <p className="text-xs text-slate-500">{data.infrastructure?.message || 'Unavailable'}</p>
        ) : (
          <ul className="text-xs space-y-1 max-h-28 overflow-y-auto custom-scrollbar">
            {infrastructure.slice(0, 10).map((inf: any, i: number) => (
              <li key={i} className="flex justify-between border-b border-slate-800 pb-1">
                <span className="text-slate-300 font-medium">{inf.name}</span>
                <span className="text-slate-400 text-[10px]">{inf.type}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-slate-900/50 p-3 rounded">
        <h4 className="text-xs font-semibold text-slate-400 flex items-center gap-1 mb-2">
          <AlertTriangle className="w-3.5 h-3.5" /> POSSIBLE SOURCE
        </h4>
        <p className="text-[10px] text-slate-500 mb-2">
          Spatial association only. Not a claim that any object caused a spill.
        </p>
        <ul className="text-xs space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
          {sources.slice(0, 6).map((src: any, i: number) => (
            <li key={i} className="border border-slate-700 bg-slate-800/40 p-2 rounded">
              <div className="flex justify-between items-start mb-1">
                <span className="font-semibold text-slate-200">{src.object_name}</span>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase bg-slate-800 text-slate-400">
                  {src.confidence}
                </span>
              </div>
              <div className="text-[10px] text-slate-400">
                {src.category}
                {src.distance_km != null ? ` | ${src.distance_km} km` : ''}
              </div>
              <div className="text-[10px] text-slate-300 mt-1">{src.evidence}</div>
            </li>
          ))}
        </ul>
      </div>

      {warnings.length > 0 && (
        <div className="text-[10px] text-amber-200 space-y-1">
          {warnings.map((w: string, i: number) => (
            <div key={i}>• {w}</div>
          ))}
        </div>
      )}
    </div>
  );
};
