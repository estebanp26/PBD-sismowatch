import React from 'react';
import {
  CheckCircle2,
  Clock,
  Database,
  History,
  RefreshCw,
  Shield
} from 'lucide-react';
import { PipelineStatus, QualityMetricItem, UserSession } from '../types';

interface PipelineStatusProps {
  status: PipelineStatus | null;
  session: UserSession | null;
  onOpenBackfill: () => void;
  onRefresh: () => void;
  loading: boolean;
}

export const PipelineStatusView: React.FC<PipelineStatusProps> = ({
  status,
  session,
  onOpenBackfill,
  onRefresh,
  loading
}) => {
  const isAdmin = session?.role === 'admin';

  if (loading || !status) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-32 bg-slate-900/60 border border-slate-800 rounded-xl p-4 animate-pulse"></div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Cabecera y Resumen de Estado */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/70 border border-slate-800 p-4 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-400" />
              Estado del Pipeline y Calidad
            </h2>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase font-mono tracking-wider ${
                isAdmin
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                  : 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
              }`}
            >
              {isAdmin ? 'Vista Detallada (Admin)' : 'Vista Resumen (Viewer)'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            {isAdmin
              ? 'Supervisión detallada de DAGs y compuertas de calidad Pandera.'
              : 'Supervisión de salud del pipeline y resumen operativo de calidad de datos.'}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={onRefresh}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700/80 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
            <span>Actualizar</span>
          </button>

          {/* Botón exclusivo de Administrador: Lanzar Backfill */}
          {isAdmin && (
            <button
              onClick={onOpenBackfill}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium shadow-md shadow-blue-600/30 transition-all"
            >
              <History className="w-3.5 h-3.5" />
              <span>Lanzar Backfill</span>
            </button>
          )}
        </div>
      </div>

      {/* Tarjetas de Salud Global (Visibles para Viewer y Admin) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Puntaje Global de Calidad</div>
            <div className="text-2xl font-bold text-white font-mono">
              {status.overall_quality_score.toFixed(1)}%
            </div>
            <div className="text-[11px] text-emerald-400">Compuertas Pandera Activas</div>
          </div>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
          <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Frescura del Pipeline</div>
            <div className="text-2xl font-bold text-white font-mono">
              {status.freshness_minutes}m
            </div>
            <div className="text-[11px] text-slate-400">Retraso vs último evento USGS</div>
          </div>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
          <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Arquitectura Medallón</div>
            <div className="text-base font-bold text-white">S3 Lakehouse + Postgres</div>
            <div className="text-[11px] text-indigo-400">raw &rarr; staging &rarr; curated</div>
          </div>
        </div>
      </div>

      {/* Estado de los DAGs en Airflow (Resumen operativo visible para Viewer y Admin) */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider mb-4">
          Orquestación en Apache Airflow (LocalExecutor)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(status.dags_status).map(([dagId, sched]) => (
            <div
              key={dagId}
              className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 live-pulse-badge"></span>
                  <span className="text-[10px] uppercase font-bold text-emerald-400 font-mono">
                    ACTIVO
                  </span>
                </div>
                <div className="text-xs font-semibold text-slate-200 font-mono break-all">
                  {dagId}
                </div>
              </div>
              <div className="text-[11px] text-slate-400 mt-2 font-mono">
                {String(sched)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* VISTA PARA VIEWER (USUARIO CORRIENTE): RESUMEN OPERATIVO */}
      {!isAdmin && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex items-start space-x-4 shadow-xl">
          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-2xl text-blue-400 flex-shrink-0">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              Resumen Operativo de Calidad
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-mono">
                Rol: Viewer (Usuario General)
              </span>
            </h3>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              El pipeline de datos se encuentra activo y saludable. Todos los eventos presentados en el Dashboard y en los Reportes han superado satisfactoriamente las compuertas de calidad.
            </p>
            <div className="mt-3 text-[11px] text-slate-500 flex items-center gap-1.5 font-mono">
              <span>🔒 La auditoría granular de reglas evaluadas y controles de backfill están reservados para el perfil Administrador.</span>
            </div>
          </div>
        </div>
      )}

      {/* VISTA EXCLUSIVA PARA ADMIN: DETALLE DE AUDITORÍA DE CALIDAD PANDERA */}
      {isAdmin && (
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="p-4 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase text-slate-300 tracking-wider">
              Auditoría Detallada de Reglas de Calidad (Pandera)
            </h3>
            <span className="text-xs text-slate-500 font-mono">
              {status.quality_rules.length} ejecuciones registradas
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/50 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Regla de Calidad</th>
                  <th className="px-4 py-3 text-center">Evaluados</th>
                  <th className="px-4 py-3 text-center">Aprobados</th>
                  <th className="px-4 py-3 text-center">Rechazados</th>
                  <th className="px-4 py-3 text-center">Puntaje</th>
                  <th className="px-4 py-3 text-center">Resultado</th>
                  <th className="px-4 py-3 text-right">Ejecutado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                {(status.quality_rules || []).map((rule: QualityMetricItem, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3 font-semibold text-slate-100 font-sans">
                      {rule.rule_name}
                    </td>
                    <td className="px-4 py-3 text-center text-slate-300">{rule.records_evaluated}</td>
                    <td className="px-4 py-3 text-center text-emerald-400 font-bold">{rule.records_passed}</td>
                    <td className="px-4 py-3 text-center text-red-400 font-bold">{rule.records_failed}</td>
                    <td className="px-4 py-3 text-center font-bold">{rule.score_pct.toFixed(1)}%</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                          rule.status === 'PASSED'
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : rule.status === 'WARNING'
                            ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                            : 'bg-red-500/15 text-red-400 border border-red-500/30'
                        }`}
                      >
                        {rule.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-slate-500 text-[11px]">
                      {new Date(rule.executed_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
