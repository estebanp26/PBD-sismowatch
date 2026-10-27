import React, { useState } from 'react';
import { FileText, Download, Sparkles, RefreshCw, Calendar, Cpu, CheckCircle } from 'lucide-react';
import { AIExecutiveReport, UserSession } from '../types';
import { api } from '../services/api';

interface ReportsSectionProps {
  reports: AIExecutiveReport[];
  session: UserSession | null;
  onRefresh: () => void;
  loading: boolean;
}

export const ReportsSection: React.FC<ReportsSectionProps> = ({
  reports,
  session,
  onRefresh,
  loading
}) => {
  const [selectedReportId, setSelectedReportId] = useState<number | null>(
    reports.length > 0 ? reports[0].id : null
  );
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isExportingCSV, setIsExportingCSV] = useState(false);
  const [isExportingPDF, setIsExportingPDF] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const selectedReport = reports.find(r => r.id === (selectedReportId || reports[0]?.id)) || reports[0];

  const handleRegenerate = async () => {
    if (session?.role !== 'admin') return;
    try {
      setIsRegenerating(true);
      setActionMessage('Disparando regeneración de análisis con IA en Airflow...');
      const res = await api.regenerateReport();
      setActionMessage(res.message);
      setTimeout(() => {
        onRefresh();
        setActionMessage(null);
      }, 4000);
    } catch (err: any) {
      setActionMessage(`Error: ${err.message}`);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      setIsExportingCSV(true);
      await api.exportCSV();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsExportingCSV(false);
    }
  };

  const handleExportPDF = async () => {
    try {
      setIsExportingPDF(true);
      await api.exportPDF(selectedReport?.id);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsExportingPDF(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Cabecera y Botones de Acción */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/70 border border-slate-800 p-4 rounded-2xl shadow-xl">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            Reportes Ejecutivos Asistidos por IA (Qwen 2.5)
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Análisis narrativos diarios generados con cifras 100% calculadas determinísticamente en SQL y guardrails anti-alucinación.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Botón de Exportar CSV */}
          <button
            onClick={handleExportCSV}
            disabled={isExportingCSV}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700/80 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5 text-blue-400" />
            <span>{isExportingCSV ? 'Descargando...' : 'Exportar CSV'}</span>
          </button>

          {/* Botón de Exportar PDF */}
          <button
            onClick={handleExportPDF}
            disabled={isExportingPDF || !selectedReport}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700/80 transition-colors disabled:opacity-50"
          >
            <FileText className="w-3.5 h-3.5 text-red-400" />
            <span>{isExportingPDF ? 'Generando PDF...' : 'Descargar PDF'}</span>
          </button>

          {/* Botón exclusivo de Administrador: Regenerar reporte con IA */}
          {session?.role === 'admin' && (
            <button
              onClick={handleRegenerate}
              disabled={isRegenerating}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium shadow-md shadow-indigo-600/30 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
              <span>{isRegenerating ? 'Regenerando...' : 'Regenerar con IA'}</span>
            </button>
          )}
        </div>
      </div>

      {actionMessage && (
        <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-xl text-xs text-blue-300">
          {actionMessage}
        </div>
      )}

      {/* Contenido: Selector histórico a la izquierda y Reporte a la derecha */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Historial de Reportes */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 shadow-xl">
          <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider mb-3 flex items-center gap-1.5">
            <Calendar className="w-4 h-4 text-blue-400" />
            Historial de Reportes
          </h3>

          <div className="space-y-2">
            {loading && reports.length === 0 ? (
              [...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-slate-800/50 rounded-xl animate-pulse"></div>
              ))
            ) : reports.length === 0 ? (
              <div className="text-xs text-slate-500 p-4 text-center">
                No hay reportes generados aún.
              </div>
            ) : (
              reports.map(r => (
                <button
                  key={r.id}
                  onClick={() => setSelectedReportId(r.id)}
                  className={`w-full text-left p-3 rounded-xl transition-all border ${
                    selectedReport?.id === r.id
                      ? 'bg-blue-600/15 border-blue-500/40 text-white'
                      : 'bg-slate-800/30 border-slate-800/80 text-slate-400 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="text-xs font-semibold text-slate-200 truncate">
                    {r.title}
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1 font-mono">
                    <span>{r.report_date}</span>
                    <span className="text-[10px] text-indigo-400">{r.generated_by_model}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Vista del Reporte Seleccionado */}
        <div className="lg:col-span-3 bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl">
          {selectedReport ? (
            <div className="space-y-6">
              {/* Encabezado del reporte */}
              <div className="border-b border-slate-800 pb-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <h3 className="text-xl font-bold text-white tracking-tight">
                    {selectedReport.title}
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 font-mono">
                      <Cpu className="w-3 h-3" /> Modelo: {selectedReport.generated_by_model}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono">
                      <CheckCircle className="w-3 h-3" /> Cifras Auditadas
                    </span>
                  </div>
                </div>
                <div className="text-xs text-slate-400 mt-1 font-mono">
                  Fecha de Generación: {selectedReport.report_date} ({new Date(selectedReport.created_at).toLocaleString()})
                </div>
              </div>

              {/* Narrativa generada por IA */}
              <div className="space-y-3.5 text-slate-300 text-sm leading-relaxed">
                {selectedReport.summary_text.split('\n\n').map((paragraph, idx) => (
                  <p key={idx} className="bg-slate-800/30 p-3.5 rounded-xl border border-slate-800/80">
                    {paragraph}
                  </p>
                ))}
              </div>

              {/* Tabla de Métricas Verificadas por Código */}
              <div>
                <h4 className="text-xs font-bold uppercase text-slate-400 tracking-wider mb-2.5">
                  Verdad Fundamental (Métricas Calculadas en SQL)
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5">
                  <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Total Sismos</div>
                    <div className="text-sm font-bold text-white font-mono">
                      {selectedReport.metrics_snapshot.total_events ?? 'N/A'}
                    </div>
                  </div>
                  <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Magnitud Máx.</div>
                    <div className="text-sm font-bold text-amber-400 font-mono">
                      M {selectedReport.metrics_snapshot.max_magnitude ?? 'N/A'}
                    </div>
                  </div>
                  <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Magnitud Prom.</div>
                    <div className="text-sm font-bold text-blue-400 font-mono">
                      M {selectedReport.metrics_snapshot.avg_magnitude ?? 'N/A'}
                    </div>
                  </div>
                  <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Alertas Tsunami</div>
                    <div className="text-sm font-bold text-red-400 font-mono">
                      {selectedReport.metrics_snapshot.tsunami_alerts ?? 0}
                    </div>
                  </div>
                  <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Profundidad Med.</div>
                    <div className="text-sm font-bold text-slate-300 font-mono">
                      {selectedReport.metrics_snapshot.avg_depth_km ?? 'N/A'} km
                    </div>
                  </div>
                  <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Score Calidad</div>
                    <div className="text-sm font-bold text-emerald-400 font-mono">
                      {selectedReport.metrics_snapshot.quality_score ?? 100}%
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-slate-500 text-sm">
              Seleccione un reporte del historial para visualizar su contenido detallado.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
