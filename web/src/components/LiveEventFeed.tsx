import React from 'react';
import { Filter, Search, Waves, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';
import { EarthquakeEvent } from '../types';

interface LiveEventFeedProps {
  events: EarthquakeEvent[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  onPageChange: (newPage: number) => void;
  minMag: number | undefined;
  setMinMag: (val: number | undefined) => void;
  region: string;
  setRegion: (val: string) => void;
  tsunamiOnly: boolean;
  setTsunamiOnly: (val: boolean) => void;
  selectedEvent: EarthquakeEvent | null;
  onSelectEvent: (event: EarthquakeEvent) => void;
  loading: boolean;
}

export const LiveEventFeed: React.FC<LiveEventFeedProps> = ({
  events,
  total,
  page,
  totalPages,
  onPageChange,
  minMag,
  setMinMag,
  region,
  setRegion,
  tsunamiOnly,
  setTsunamiOnly,
  selectedEvent,
  onSelectEvent,
  loading
}) => {
  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
      {/* Barra de Filtros */}
      <div className="p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-900/90">
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Filtros y Búsqueda
          </span>
          <span className="text-xs text-slate-500 font-mono">
            ({total} eventos encontrados)
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Búsqueda por región */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar región (ej. Chile, Japan)..."
              value={region}
              onChange={e => setRegion(e.target.value)}
              className="bg-slate-800 border border-slate-700/80 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-48"
            />
          </div>

          {/* Filtro de Magnitud Mínima */}
          <select
            value={minMag ?? ''}
            onChange={e => setMinMag(e.target.value ? parseFloat(e.target.value) : undefined)}
            className="bg-slate-800 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">Todas las magnitudes</option>
            <option value="2.5">M &ge; 2.5+</option>
            <option value="4.0">M &ge; 4.0+ (Moderados)</option>
            <option value="5.5">M &ge; 5.5+ (Fuertes)</option>
            <option value="6.5">M &ge; 6.5+ (Mayores)</option>
          </select>

          {/* Toggle Solo Alertas de Tsunami */}
          <label className="flex items-center space-x-1.5 cursor-pointer bg-slate-800/80 border border-slate-700/80 px-2.5 py-1.5 rounded-lg text-xs text-slate-300 hover:text-white">
            <input
              type="checkbox"
              checked={tsunamiOnly}
              onChange={e => setTsunamiOnly(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-red-500 focus:ring-0"
            />
            <Waves className="w-3.5 h-3.5 text-red-400" />
            <span>Solo Tsunamis</span>
          </label>
        </div>
      </div>

      {/* Tabla de Eventos */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-800/50 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="px-4 py-3">Magnitud</th>
              <th className="px-4 py-3">Ubicación</th>
              <th className="px-4 py-3">Profundidad</th>
              <th className="px-4 py-3">Fecha y Hora (UTC)</th>
              <th className="px-4 py-3 text-center">Tsunami</th>
              <th className="px-4 py-3 text-center">Estado</th>
              <th className="px-4 py-3 text-right">Detalle</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {loading ? (
              [...Array(6)].map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 w-12 bg-slate-800 rounded"></div></td>
                  <td className="px-4 py-3"><div className="h-4 w-44 bg-slate-800 rounded"></div></td>
                  <td className="px-4 py-3"><div className="h-4 w-16 bg-slate-800 rounded"></div></td>
                  <td className="px-4 py-3"><div className="h-4 w-32 bg-slate-800 rounded"></div></td>
                  <td className="px-4 py-3 text-center"><div className="h-4 w-8 bg-slate-800 rounded mx-auto"></div></td>
                  <td className="px-4 py-3 text-center"><div className="h-4 w-12 bg-slate-800 rounded mx-auto"></div></td>
                  <td className="px-4 py-3 text-right"><div className="h-4 w-6 bg-slate-800 rounded ml-auto"></div></td>
                </tr>
              ))
            ) : events.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                  No se encontraron eventos sísmicos con los filtros seleccionados.
                </td>
              </tr>
            ) : (
              events.map(ev => {
                const isSelected = selectedEvent?.id === ev.id;
                let magColor = 'text-blue-400 bg-blue-500/10 border-blue-500/30';
                if (ev.mag >= 6.0) magColor = 'text-red-400 bg-red-500/10 border-red-500/30 font-bold';
                else if (ev.mag >= 4.5) magColor = 'text-amber-400 bg-amber-500/10 border-amber-500/30 font-semibold';
                else if (ev.mag >= 3.0) magColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';

                return (
                  <tr
                    key={ev.id}
                    onClick={() => onSelectEvent(ev)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-blue-600/20 hover:bg-blue-600/30'
                        : 'hover:bg-slate-800/40'
                    }`}
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono border ${magColor}`}>
                        M {ev.mag.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-100 max-w-xs truncate">
                      {ev.place}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap font-mono text-slate-400">
                      {ev.depth_km.toFixed(1)} km
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                      {new Date(ev.time).toLocaleString('es-ES', { timeZone: 'UTC' })} UTC
                    </td>
                    <td className="px-4 py-3 text-center whitespace-nowrap">
                      {ev.tsunami === 1 ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
                          <Waves className="w-3 h-3" /> ALERTA
                        </span>
                      ) : (
                        <span className="text-slate-600 font-mono">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center whitespace-nowrap">
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                        {ev.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {ev.url && (
                        <a
                          href={ev.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="inline-block p-1 text-slate-400 hover:text-blue-400 transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      <div className="p-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 bg-slate-900/90">
        <div>
          Página <span className="text-slate-200 font-bold">{page}</span> de{' '}
          <span className="text-slate-200 font-bold">{totalPages}</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
