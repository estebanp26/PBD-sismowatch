export interface EarthquakeEvent {
  id: string;
  mag: number;
  place: string;
  time: string;
  updated?: string;
  url?: string;
  status: string;
  tsunami: number;
  sig?: number;
  mag_type?: string;
  type?: string;
  title?: string;
  longitude: number;
  latitude: number;
  depth_km: number;
  is_updated?: boolean;
}

export interface KPISummary {
  events_last_24h: number;
  max_magnitude_24h: number;
  avg_magnitude_24h: number;
  tsunami_alerts_24h: number;
  quality_score: number;
  last_event_time: string | null;
  data_freshness_minutes: number;
  last_pipeline_run: string | null;
}

export interface TimeSeriesPoint {
  hour: string;
  count: number;
  max_mag: number;
}

export interface MagnitudeDistribution {
  range_label: string;
  count: number;
}

export interface RegionActivity {
  region: string;
  count: number;
  max_mag: number;
}

export interface StatsResponse {
  timeseries: TimeSeriesPoint[];
  distribution: MagnitudeDistribution[];
  top_regions: RegionActivity[];
}

export interface AIExecutiveReport {
  id: number;
  report_date: string;
  title: string;
  summary_text: string;
  top_regions: Array<{ region: string; count: number; max_mag: number }>;
  metrics_snapshot: Record<string, any>;
  generated_by_model: string;
  created_at: string;
}

export interface QualityMetricItem {
  rule_name: string;
  records_evaluated: number;
  records_passed: number;
  records_failed: number;
  score_pct: number;
  status: string;
  executed_at: string;
}

export interface PipelineStatus {
  dags_status: Record<string, string>;
  overall_quality_score: number;
  freshness_minutes: number;
  quality_rules: QualityMetricItem[];
  view_mode?: 'summary' | 'detail';
  last_update: string;
}

export interface UserSession {
  token: string;
  username: string;
  fullName?: string;
  role: 'admin' | 'viewer';
}

export interface ChatQueryResponse {
  reply: string;
  data?: any;
  source_layer?: string;
  query_sql?: string | null;
  execution_time_ms: number;
  cached?: boolean;
  suggested_questions?: string[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  sourceLayer?: string;
  querySql?: string | null;
  executionTimeMs?: number;
  cached?: boolean;
}

export interface LineageNode {
  id: string;
  type: string;
  name: string;
  layer: string;
  description: string;
  record_count?: number | null;
  details?: Record<string, any>;
}

export interface LineageResponse {
  service_name: string;
  description: string;
  openmetadata_url: string;
  openmetadata_compose_file: string;
  nodes: LineageNode[];
  edges: Array<{ from: string; to: string }>;
  last_updated: string;
}


