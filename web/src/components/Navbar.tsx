import React from 'react';
import { Activity, Shield, LogOut, Radio } from 'lucide-react';
import { UserSession } from '../types';

interface NavbarProps {
  session: UserSession | null;
  activeTab: 'dashboard' | 'events' | 'reports' | 'pipeline' | 'chatbot' | 'lineage';
  setActiveTab: (tab: 'dashboard' | 'events' | 'reports' | 'pipeline' | 'chatbot' | 'lineage') => void;
  onLogout: () => void;
  isLive: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  session,
  activeTab,
  setActiveTab,
  onLogout,
  isLive
}) => {
  return (
    <header className="sticky top-0 z-50 bg-[#0F172A]/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo y Marca */}
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-tr from-blue-600 to-indigo-500 p-2 rounded-xl shadow-lg shadow-blue-500/20">
              <Activity className="w-6 h-6 text-white animate-pulse" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
                Sismo<span className="text-blue-500">Watch</span>
              </span>
              <span className="text-xs text-slate-400 block -mt-1 font-mono">
                Global Seismic Intel
              </span>
            </div>

            {/* Badge de Tiempo Real "EN VIVO" */}
            <div className="hidden sm:flex items-center space-x-1.5 ml-4 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
              <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 live-pulse-badge' : 'bg-amber-500'}`}></span>
              <Radio className="w-3.5 h-3.5" />
              <span>{isLive ? 'EN VIVO (SSE)' : 'RECONECTANDO'}</span>
            </div>
          </div>

          {/* Navegación por pestañas */}
          {session && (
            <nav className="flex items-center space-x-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800/80">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'dashboard'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('events')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'events'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                Eventos
              </button>
              <button
                onClick={() => setActiveTab('reports')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'reports'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                Reportes IA
              </button>
              <button
                onClick={() => setActiveTab('pipeline')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'pipeline'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                {session.role === 'admin' ? 'Salud Pipeline' : 'Salud Pipeline'}
              </button>
              <button
                onClick={() => setActiveTab('chatbot')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === 'chatbot'
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm shadow-blue-500/20'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <span>Asistente IA</span>
                <span className="px-1.5 py-0.2 rounded bg-indigo-500/30 text-indigo-300 text-[10px] font-mono">Chat</span>
              </button>
              {session.role === 'admin' && (
                <button
                  onClick={() => setActiveTab('lineage')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                    activeTab === 'lineage'
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  <span>Linaje y Flujo</span>
                  <span className="px-1.5 py-0.2 rounded bg-blue-500/30 text-blue-300 text-[10px] font-mono">OM</span>
                </button>
              )}
            </nav>
          )}

          {/* Perfil de usuario y Logout */}
          <div className="flex items-center space-x-3">
            {session ? (
              <div className="flex items-center space-x-3">
                <div className="text-right hidden md:block">
                  <div className="text-xs font-medium text-slate-200">
                    {session.fullName || session.username}
                  </div>
                  <div className="flex items-center justify-end space-x-1">
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                        session.role === 'admin'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                          : 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                      }`}
                    >
                      {session.role}
                    </span>
                  </div>
                </div>

                <button
                  onClick={onLogout}
                  title="Cerrar Sesión"
                  className="p-2 rounded-lg bg-slate-800/80 hover:bg-red-500/20 hover:text-red-400 text-slate-400 transition-colors border border-slate-700/60"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <Shield className="w-4 h-4 text-slate-500" />
                <span>Acceso Restringido</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
