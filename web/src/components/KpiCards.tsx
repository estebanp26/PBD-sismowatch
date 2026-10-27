import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, Clock, Flame, Waves } from 'lucide-react';
import { KPISummary } from '../types';

interface KpiCardsProps {
  kpis: KPISummary | null;
  loading: boolean;
}

export const KpiCards: React.FC<KpiCardsProps> = ({ kpis, loading }) => {
  if (loading || !kpis) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 animate-pulse">
            <div className="h-3 w-16 bg-slate-800 rounded mb-2"></div>
            <div className="h-7 w-24 bg-slate-700 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  const items = [
    {
      title: 'Eventos (24h)',
      value: kpis.events_last_24h.toLocaleString(),
      subtext: 'Registrados en Curated',
      icon: Activity,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20'
    },
    {
      title: 'Magnitud Máx.',
      value: `M ${kpis.max_magnitude_24h.toFixed(1)}`,
      subtext: 'Mayor pico de energía',
      icon: Flame,
      color: kpis.max_magnitude_24h >= 6.0 ? 'text-red-400' : 'text-amber-400',
      bgColor: kpis.max_magnitude_24h >= 6.0 ? 'bg-red-500/10' : 'bg-amber-500/10',
      borderColor: kpis.max_magnitude_24h >= 6.0 ? 'border-red-500/30' : 'border-amber-500/20'
    },
    {
      title: 'Magnitud Promedio',
      value: `M ${kpis.avg_magnitude_24h.toFixed(2)}`,
      subtext: 'Media geométrica 24h',
      icon: AlertTriangle,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10',
      borderColor: 'border-indigo-500/20'
    },
    {
      title: 'Alertas Tsunami',
      value: kpis.tsunami_alerts_24h.toString(),
      subtext: kpis.tsunami_alerts_24h > 0 ? '¡Alerta Activa!' : 'Sin amenazas',
      icon: Waves,
      color: kpis.tsunami_alerts_24h > 0 ? 'text-red-400 animate-bounce' : 'text-slate-400',
      bgColor: kpis.tsunami_alerts_24h > 0 ? 'bg-red-500/20' : 'bg-slate-800/40',
      borderColor: kpis.tsunami_alerts_24h > 0 ? 'border-red-500/40' : 'border-slate-700/40'
    },
    {
      title: 'Calidad de Datos',
      value: `${kpis.quality_score.toFixed(1)}%`,
      subtext: 'Reglas Pandera aprobadas',
      icon: CheckCircle2,
      color: kpis.quality_score >= 90 ? 'text-emerald-400' : 'text-amber-400',
      bgColor: kpis.quality_score >= 90 ? 'bg-emerald-500/10' : 'bg-amber-500/10',
      borderColor: kpis.quality_score >= 90 ? 'border-emerald-500/20' : 'border-amber-500/20'
    },
    {
      title: 'Frescura del Dato',
      value: `${kpis.data_freshness_minutes}m`,
      subtext: 'Demora último sismo',
      icon: Clock,
      color: kpis.data_freshness_minutes <= 30 ? 'text-emerald-400' : 'text-amber-400',
      bgColor: 'bg-slate-800/40',
      borderColor: 'border-slate-700/40'
    }
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
      {items.map((item, idx) => {
        const Icon = item.icon;
        return (
          <div
            key={idx}
            className={`p-3.5 rounded-xl border ${item.borderColor} ${item.bgColor} backdrop-blur-sm transition-all hover:translate-y-[-2px]`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                {item.title}
              </span>
              <Icon className={`w-4 h-4 ${item.color}`} />
            </div>
            <div className={`text-xl font-bold tracking-tight text-white mb-0.5`}>
              {item.value}
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              {item.subtext}
            </div>
          </div>
        );
      })}
    </div>
  );
};
