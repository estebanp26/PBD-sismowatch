import {
  EarthquakeEvent,
  KPISummary,
  StatsResponse,
  AIExecutiveReport,
  PipelineStatus,
  UserSession,
  ChatQueryResponse,
  LineageResponse
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function getStoredSession(): UserSession | null {
  const data = localStorage.getItem('sismowatch_session');
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function saveSession(session: UserSession): void {
  localStorage.setItem('sismowatch_session', JSON.stringify(session));
}

export function clearSession(): void {
  localStorage.removeItem('sismowatch_session');
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const session = getStoredSession();
  const headers = new Headers(options.headers || {});

  if (session?.token) {
    headers.set('Authorization', `Bearer ${session.token}`);
  }

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearSession();
    window.dispatchEvent(new Event('auth:unauthorized'));
    throw new Error('Sesión expirada o no autorizada. Por favor inicie sesión nuevamente.');
  }

  if (!response.ok) {
    let errorDetail = 'Error al comunicarse con el servidor';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // Ignorar fallo de parseo JSON
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Autenticación
  login: async (username: string, password: string): Promise<UserSession> => {
    const data = await request<{
      access_token: string;
      role: 'admin' | 'viewer';
      username: string;
      full_name?: string;
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });

    const session: UserSession = {
      token: data.access_token,
      role: data.role,
      username: data.username,
      fullName: data.full_name
    };
    saveSession(session);
    return session;
  },

  // KPIs y Estadísticas
  getKPIs: () => request<KPISummary>('/api/kpis'),
  getStats: () => request<StatsResponse>('/api/stats/timeseries'),

  // Eventos sísmicos
  getEvents: (params?: {
    page?: number;
    page_size?: number;
    min_mag?: number;
    max_mag?: number;
    region?: string;
    tsunami_only?: boolean;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.min_mag !== undefined) searchParams.set('min_mag', params.min_mag.toString());
    if (params?.max_mag !== undefined) searchParams.set('max_mag', params.max_mag.toString());
    if (params?.region) searchParams.set('region', params.region);
    if (params?.tsunami_only) searchParams.set('tsunami_only', 'true');

    return request<{
      items: EarthquakeEvent[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    }>(`/api/events?${searchParams.toString()}`);
  },

  // Reportes
  getReports: () => request<AIExecutiveReport[]>('/api/reports'),
  
  exportCSV: async () => {
    const session = getStoredSession();
    const res = await fetch(`${API_BASE}/api/reports/export?format=csv`, {
      headers: session?.token ? { Authorization: `Bearer ${session.token}` } : {}
    });
    if (!res.ok) throw new Error('Error al descargar archivo CSV');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sismowatch_export_${Date.now()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  },

  exportPDF: async (reportId?: number) => {
    const session = getStoredSession();
    const endpoint = reportId 
      ? `/api/reports/export?format=pdf&report_id=${reportId}` 
      : `/api/reports/export?format=pdf`;
    
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: session?.token ? { Authorization: `Bearer ${session.token}` } : {}
    });
    if (!res.ok) throw new Error('Error al generar archivo PDF');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sismowatch_informe_${Date.now()}.pdf`;
    a.click();
    window.URL.revokeObjectURL(url);
  },

  // Asistente IA Chatbot (Silver & Gold)
  queryChatbot: (message: string, history?: Array<{ sender: string; text: string }>) => {
    return request<ChatQueryResponse>('/api/chat/query', {
      method: 'POST',
      body: JSON.stringify({ message, history })
    });
  },

  getChatSuggestions: () => request<string[]>('/api/chat/suggestions'),

  // Metadatos y Linaje (OpenMetadata)
  getDataLineage: () => request<LineageResponse>('/api/metadata/lineage'),

  // Pipeline y Calidad
  getPipelineStatus: () => request<PipelineStatus>('/api/pipeline/status'),

  // Acciones de Administración (Protegidas)
  launchBackfill: (daysBack: number, minMagnitude: number) => {
    return request<{ status: string; dag_run_id: string; message: string }>('/api/admin/backfill', {
      method: 'POST',
      body: JSON.stringify({ days_back: daysBack, min_magnitude: minMagnitude })
    });
  },

  regenerateReport: () => {
    return request<{ status: string; dag_run_id: string; message: string }>('/api/admin/reports/regenerate', {
      method: 'POST'
    });
  }
};
