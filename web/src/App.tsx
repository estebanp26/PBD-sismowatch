import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { KpiCards } from './components/KpiCards';
import { SeismicMap } from './components/SeismicMap';
import { ChartsSection } from './components/ChartsSection';
import { LiveEventFeed } from './components/LiveEventFeed';
import { ReportsSection } from './components/ReportsSection';
import { PipelineStatusView } from './components/PipelineStatus';
import { ChatbotSection } from './components/ChatbotSection';
import { DataLineageSection } from './components/DataLineageSection';
import { BackfillModal } from './components/BackfillModal';
import { LoginModal } from './components/LoginModal';
import {
  EarthquakeEvent,
  KPISummary,
  StatsResponse,
  AIExecutiveReport,
  PipelineStatus as PipelineStatusType,
  UserSession
} from './types';
import { api, getStoredSession, clearSession } from './services/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const App: React.FC = () => {
  const [session, setSession] = useState<UserSession | null>(getStoredSession());
  const [activeTab, setActiveTab] = useState<'dashboard' | 'events' | 'reports' | 'pipeline' | 'chatbot' | 'lineage'>('dashboard');
  const [isLive, setIsLive] = useState(false);

  // Estados de datos
  const [kpis, setKpis] = useState<KPISummary | null>(null);
  const [events, setEvents] = useState<EarthquakeEvent[]>([]);
  const [totalEvents, setTotalEvents] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [reports, setReports] = useState<AIExecutiveReport[]>([]);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusType | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<EarthquakeEvent | null>(null);

  // Filtros
  const [minMag, setMinMag] = useState<number | undefined>(undefined);
  const [region, setRegion] = useState('');
  const [tsunamiOnly, setTsunamiOnly] = useState(false);

  // Estados de carga y error
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Modales de administración
  const [isBackfillOpen, setIsBackfillOpen] = useState(false);

  // Escuchar desautenticación automática
  useEffect(() => {
    const handleUnauthorized = () => {
      setSession(null);
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  // Carga de datos inicial
  useEffect(() => {
    if (session) {
      loadAllData();
    }
  }, [session, page, minMag, region, tsunamiOnly]);

  // Conexión en tiempo real con Server-Sent Events (SSE)
  useEffect(() => {
    if (!session?.token) {
      setIsLive(false);
      return;
    }

    let eventSource: EventSource | null = null;
    let reconnectTimeout: any = null;

    const connectSSE = () => {
      try {
        // En navegadores estándar EventSource no acepta headers personalizados directamente en GET,
        // por lo que usamos el endpoint /api/stream con token o cookie
        eventSource = new EventSource(`${API_BASE}/api/stream?token=${session.token}`);

        eventSource.onopen = () => {
          setIsLive(true);
          setErrorMessage(null);
        };

        eventSource.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            if (data.type === 'seismic_update' && Array.isArray(data.events)) {
              setEvents(prev => {
                // Combinar eventos nuevos al inicio sin duplicar por ID
                const existingIds = new Set(prev.map(ev => ev.id));
                const newItems = data.events.filter((ev: EarthquakeEvent) => !existingIds.has(ev.id));
                return [...newItems, ...prev].slice(0, 50);
              });
            }
          } catch (err) {
            // Ignorar parseos no JSON
          }
        };

        eventSource.onerror = () => {
          setIsLive(false);
          eventSource?.close();
          // Reintentar conexión automática en 5 segundos
          reconnectTimeout = setTimeout(connectSSE, 5000);
        };
      } catch (err) {
        setIsLive(false);
      }
    };

    connectSSE();

    return () => {
      if (eventSource) eventSource.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [session]);

  const loadAllData = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);

      const [kpiRes, eventsRes, statsRes, reportsRes, pipeRes] = await Promise.allSettled([
        api.getKPIs(),
        api.getEvents({ page, page_size: 20, min_mag: minMag, region, tsunami_only: tsunamiOnly }),
        api.getStats(),
        api.getReports(),
        api.getPipelineStatus()
      ]);

      if (kpiRes.status === 'fulfilled') setKpis(kpiRes.value);
      if (eventsRes.status === 'fulfilled') {
        setEvents(eventsRes.value.items);
        setTotalEvents(eventsRes.value.total);
        setTotalPages(eventsRes.value.total_pages);
      }
      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      if (reportsRes.status === 'fulfilled') setReports(reportsRes.value);
      if (pipeRes.status === 'fulfilled') setPipelineStatus(pipeRes.value);

    } catch (err: any) {
      setErrorMessage(err.message || 'Error cargando datos del sistema.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    clearSession();
    setSession(null);
  };

  // Si no hay sesión activa: Mostrar Login (Visitante sin login no puede ver nada)
  if (!session) {
    return <LoginModal onLoginSuccess={newSession => setSession(newSession)} />;
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col">
      <Navbar
        session={session}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onLogout={handleLogout}
        isLive={isLive}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Banner de Error si ocurre algún fallo */}
        {errorMessage && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-300 flex items-center justify-between">
            <span>{errorMessage}</span>
            <button
              onClick={loadAllData}
              className="px-2.5 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded font-semibold text-[11px]"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* PESTAÑA: DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            <KpiCards kpis={kpis} loading={loading} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Mapa Sísmico Interactivo (Ocupa 2 columnas en desktop) */}
              <div className="lg:col-span-2">
                <SeismicMap
                  events={events}
                  selectedEvent={selectedEvent}
                  onSelectEvent={ev => setSelectedEvent(ev)}
                />
              </div>

              {/* Feed rápido en tiempo real */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between shadow-xl h-[420px]">
                <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
                  <span className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 live-pulse-badge"></span>
                    Últimas Detecciones
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {events.length} mostrados
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                  {events.slice(0, 10).map(ev => (
                    <div
                      key={ev.id}
                      onClick={() => setSelectedEvent(ev)}
                      className={`p-2 rounded-xl border text-xs cursor-pointer transition-all ${
                        selectedEvent?.id === ev.id
                          ? 'bg-blue-600/20 border-blue-500/50'
                          : 'bg-slate-800/40 border-slate-800 hover:bg-slate-800/80'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`font-mono font-bold ${ev.mag >= 6.0 ? 'text-red-400' : ev.mag >= 4.5 ? 'text-amber-400' : 'text-emerald-400'}`}>
                          M {ev.mag.toFixed(1)}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {new Date(ev.time).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="text-slate-300 font-medium truncate mt-0.5">
                        {ev.place}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Gráficos de Estadísticas */}
            <ChartsSection stats={stats} loading={loading} />
          </div>
        )}

        {/* PESTAÑA: EVENTOS */}
        {activeTab === 'events' && (
          <LiveEventFeed
            events={events}
            total={totalEvents}
            page={page}
            pageSize={20}
            totalPages={totalPages}
            onPageChange={setPage}
            minMag={minMag}
            setMinMag={setMinMag}
            region={region}
            setRegion={setRegion}
            tsunamiOnly={tsunamiOnly}
            setTsunamiOnly={setTsunamiOnly}
            selectedEvent={selectedEvent}
            onSelectEvent={setSelectedEvent}
            loading={loading}
          />
        )}

        {/* PESTAÑA: REPORTES IA */}
        {activeTab === 'reports' && (
          <ReportsSection
            reports={reports}
            session={session}
            onRefresh={loadAllData}
            loading={loading}
          />
        )}

        {/* PESTAÑA: SALUD PIPELINE */}
        {activeTab === 'pipeline' && (
          <PipelineStatusView
            status={pipelineStatus}
            session={session}
            onOpenBackfill={() => setIsBackfillOpen(true)}
            onRefresh={loadAllData}
            loading={loading}
          />
        )}

        {/* PESTAÑA: ASISTENTE IA CHATBOT */}
        {activeTab === 'chatbot' && (
          <ChatbotSection session={session} />
        )}

        {/* PESTAÑA: LINAJE Y GOBERNANZA MEDALLION (OPENMETADATA) */}
        {activeTab === 'lineage' && (
          <DataLineageSection session={session} />
        )}
      </main>

      {/* Modales de Administración */}
      <BackfillModal
        isOpen={isBackfillOpen}
        onClose={() => setIsBackfillOpen(false)}
        onSuccess={loadAllData}
      />
    </div>
  );
};
