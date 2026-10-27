import React from 'react';
import { BarChart3, PieChart, Globe2 } from 'lucide-react';
import { StatsResponse } from '../types';

interface ChartsSectionProps {
  stats: StatsResponse | null;
  loading: boolean;
}

export const ChartsSection: React.FC<ChartsSectionProps> = ({ stats, loading }) => {
  if (loading || !stats) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-64 bg-slate-900/60 border border-slate-800 rounded-xl p-4 animate-pulse">
            <div className="h-4 w-32 bg-slate-800 rounded mb-4"></div>
            <div className="h-40 bg-slate-800/40 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  const maxHourlyCount = Math.max(...stats.timeseries.map(t => t.count), 1);
  const totalDistribution = stats.distribution.reduce((acc, d) => acc + d.count, 0) || 1;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* 1. Actividad Horaria (Últimas 24h) */}
      <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            Sismos por Hora (Últimas 24h)
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            {stats.timeseries.length} intervalos
          </span>
        </div>

        <div className="h-36 flex items-end gap-1.5 pt-2">
          {stats.timeseries.slice(-12).map((item, idx) => {
            const heightPct = Math.round((item.count / maxHourlyCount) * 100);
            return (
              <div key={idx} className="flex-1 flex flex-col items-center h-full justify-end group relative">
                {/* Tooltip flotante */}
                <div className="absolute -top-7 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 text-[10px] text-white px-1.5 py-0.5 rounded shadow pointer-events-none whitespace-nowrap z-10">
                  {item.count} sismos (M máx {item.max_mag})
                </div>
                <div
                  style={{ height: `${Math.max(8, heightPct)}%` }}
                  className="w-full bg-gradient-to-t from-blue-600 to-indigo-400 rounded-t-sm hover:brightness-125 transition-all"
                ></div>
                <span className="text-[9px] text-slate-500 mt-1 font-mono truncate w-full text-center">
                  {item.hour.split(' ')[1] || item.hour.slice(-5)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Distribución por Magnitud */}
      <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <PieChart className="w-4 h-4 text-amber-400" />
            Distribución por Energía
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            Total {totalDistribution}
          </span>
        </div>

        <div className="space-y-2.5">
          {stats.distribution.map((item, idx) => {
            const pct = Math.round((item.count / totalDistribution) * 100);
            let barColor = 'bg-blue-500';
            if (item.range_label.includes('Fuerte')) barColor = 'bg-red-500';
            else if (item.range_label.includes('Moderado')) barColor = 'bg-amber-500';
            else if (item.range_label.includes('Menor')) barColor = 'bg-emerald-500';

            return (
              <div key={idx}>
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-slate-300">{item.range_label}</span>
                  <span className="font-semibold text-slate-400 font-mono">
                    {item.count} ({pct}%)
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${barColor} rounded-full transition-all duration-500`}
                    style={{ width: `${pct}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Regiones con Mayor Actividad */}
      <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <Globe2 className="w-4 h-4 text-emerald-400" />
            Zonas de Mayor Actividad
          </span>
          <span className="text-[10px] text-slate-500 font-mono">Top 5</span>
        </div>

        <div className="space-y-2">
          {stats.top_regions.slice(0, 5).map((reg, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40 border border-slate-800 hover:bg-slate-800/70 transition-colors"
            >
              <div className="flex items-center space-x-2 truncate">
                <span className="text-[11px] font-bold text-slate-500 font-mono w-4">
                  #{idx + 1}
                </span>
                <span className="text-xs text-slate-200 font-medium truncate">
                  {reg.region}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-mono font-semibold">
                  {reg.count} sismos
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-amber-300 font-mono font-bold">
                  M {reg.max_mag.toFixed(1)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
