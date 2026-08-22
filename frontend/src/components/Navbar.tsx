import React from 'react';
import { Shield, Database, RefreshCw, AlertTriangle } from 'lucide-react';

interface NavbarProps {
  activeSlickName?: string;
  totalAreaKm2?: number;
  driftSpeedKmh?: number;
  driftHeadingDeg?: number;
  status?: string;
  isSynthetic?: boolean;
  onRefresh?: () => void;
  onSeedDemo?: () => void;
  isLoading?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeSlickName = 'Slick-S1A-Ennore-01',
  totalAreaKm2 = 0,
  driftSpeedKmh = 0,
  driftHeadingDeg = 0,
  status = 'ACTIVE',
  isSynthetic = false,
  onRefresh,
  onSeedDemo,
  isLoading = false,
}) => {
  return (
    <header className="glass-panel border-b border-slate-700/80 px-6 py-3 flex items-center justify-between z-30">
      {/* Brand & System Title */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/30">
          <Shield className="w-6 h-6 text-slate-950 font-bold" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-lg font-bold tracking-wider text-slate-100 uppercase">
              Oil Spill Intelligence System
            </h1>
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
              v1.0 RESEARCH GRADE
            </span>
          </div>
          <p className="text-xs text-slate-400 flex items-center space-x-2">
            <span>Sentinel-1 SAR IW Dual-Pol</span>
            <span>•</span>
            <span>EPSG:4326 (WGS84)</span>
            <span>•</span>
            <span>CMEMS Hydrodynamic Forcing</span>
          </p>
        </div>
      </div>

      {/* Incident Status Badge */}
      <div className="hidden md:flex items-center space-x-6">
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-4 py-1.5 flex items-center space-x-4">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Active Incident</span>
            <span className="text-sm font-bold text-slate-200">{activeSlickName}</span>
          </div>
          <div className="h-6 w-px bg-slate-700" />
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Surface Extent</span>
            <span className="text-sm font-bold text-cyan-400">{totalAreaKm2.toFixed(2)} km²</span>
          </div>
          <div className="h-6 w-px bg-slate-700" />
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Drift Kinematics</span>
            <span className="text-sm font-bold text-amber-400">
              {driftSpeedKmh.toFixed(2)} km/h @ {driftHeadingDeg.toFixed(0)}°
            </span>
          </div>
          <div className="h-6 w-px bg-slate-700" />
          <div className="flex items-center space-x-1.5">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
            </span>
            <span className="text-xs font-bold uppercase tracking-wide text-red-400">{status}</span>
          </div>
        </div>

        {isSynthetic && (
          <div className="flex items-center space-x-1 bg-amber-500/20 text-amber-400 border border-amber-500/40 px-2.5 py-1 rounded text-xs font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>DEMO / SYNTHETIC DATA</span>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onSeedDemo}
          disabled={isLoading}
          className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-200 transition"
          title="Reload Ennore Port 2017 multi-pass Sentinel-1 scenario"
        >
          <Database className="w-3.5 h-3.5 text-blue-400" />
          <span>Load Case Study</span>
        </button>

        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded-lg text-xs font-semibold text-white shadow-md shadow-blue-600/30 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Sync State</span>
        </button>
      </div>
    </header>
  );
};
