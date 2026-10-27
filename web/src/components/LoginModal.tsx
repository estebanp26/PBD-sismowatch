import React, { useState } from 'react';
import { Activity, Lock, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { UserSession } from '../types';

interface LoginModalProps {
  onLoginSuccess: (session: UserSession) => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const session = await api.login(username, password);
      onLoginSuccess(session);
    } catch (err: any) {
      setError(err.message || 'Error de autenticación');
    } finally {
      setLoading(false);
    }
  };

  const setCredentials = (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0B0F19]">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6">
        {/* Logo */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 bg-blue-600/10 border border-blue-500/30 rounded-2xl text-blue-400 mb-1">
            <Activity className="w-8 h-8 animate-pulse" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Sismo<span className="text-blue-500">Watch</span>
          </h1>
          <p className="text-xs text-slate-400">
            Monitoreo sísmico global en tiempo casi real con IA y calidad gobernada.
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Usuario
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Ingrese su usuario..."
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Contraseña
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-600/30 transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
          >
            <Lock className="w-3.5 h-3.5" />
            <span>{loading ? 'Validando...' : 'Iniciar Sesión'}</span>
          </button>
        </form>

        {/* Cuentas de demostración preconfiguradas */}
        <div className="pt-4 border-t border-slate-800 text-center space-y-2">
          <span className="text-[11px] text-slate-500 block uppercase tracking-wider font-semibold">
            Cuentas de Acceso Preconfiguradas
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setCredentials('admin', 'AdminSecurePass2026!')}
              className="p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors"
            >
              <div className="text-[11px] font-bold text-amber-400">Rol ADMIN</div>
              <div className="text-[10px] text-slate-400 font-mono">admin / AdminSecurePass2026!</div>
            </button>
            <button
              type="button"
              onClick={() => setCredentials('viewer', 'ViewerSecurePass2026!')}
              className="p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors"
            >
              <div className="text-[11px] font-bold text-blue-400">Rol VIEWER</div>
              <div className="text-[10px] text-slate-400 font-mono">viewer / ViewerSecurePass2026!</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
