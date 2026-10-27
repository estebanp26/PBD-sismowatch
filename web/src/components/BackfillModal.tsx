import React, { useState } from 'react';
import { X, History, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../services/api';

interface BackfillModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const BackfillModal: React.FC<BackfillModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [daysBack, setDaysBack] = useState(30);
  const [minMagnitude, setMinMagnitude] = useState(2.5);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setFeedback(null);
      const res = await api.launchBackfill(daysBack, minMagnitude);
      setFeedback({ type: 'success', message: `${res.message} (DAG Run ID: ${res.dag_run_id})` });
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 3000);
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0F172A] border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        {/* Cabecera */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-blue-600/10 border border-blue-500/30 rounded-xl text-blue-400">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Lanzar Backfill Histórico</h3>
              <p className="text-xs text-slate-400">Ejecución del DAG dag_historical_backfill</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Días hacia atrás a consultar (Ventana temporal)
            </label>
            <input
              type="number"
              min="1"
              max="365"
              value={daysBack}
              onChange={e => setDaysBack(parseInt(e.target.value) || 1)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 font-mono"
              required
            />
            <span className="text-[11px] text-slate-500 mt-0.5 block">
              Se consultará desde hoy hacia atrás {daysBack} días desde la API de USGS.
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Magnitud mínima de filtrado
            </label>
            <input
              type="number"
              step="0.1"
              min="1.0"
              max="9.0"
              value={minMagnitude}
              onChange={e => setMinMagnitude(parseFloat(e.target.value) || 2.5)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 font-mono"
              required
            />
            <span className="text-[11px] text-slate-500 mt-0.5 block">
              Garantiza que solo se extraigan sismos con energía igual o superior a M {minMagnitude}.
            </span>
          </div>

          {feedback && (
            <div
              className={`p-3 rounded-lg text-xs flex items-center space-x-2 border ${
                feedback.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-red-500/10 border-red-500/30 text-red-300'
              }`}
            >
              {feedback.type === 'success' ? (
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
          )}

          <div className="pt-2 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-blue-600/30 transition-all disabled:opacity-50"
            >
              {loading ? 'Disparando...' : 'Iniciar Backfill'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
