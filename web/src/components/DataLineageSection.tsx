import React, { useState, useEffect } from 'react';
import {
  GitFork,
  Database,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Layers,
  RefreshCw,
  ExternalLink,
  Info,
  Server,
  FileCode,
  HardDrive
} from 'lucide-react';
import { LineageResponse, LineageNode, UserSession } from '../types';
import { api } from '../services/api';

interface DataLineageSectionProps {
  session: UserSession | null;
}

export const DataLineageSection: React.FC<DataLineageSectionProps> = ({ session: _session }) => {
  const [lineage, setLineage] = useState<LineageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null);
  const [showJsonSpec, setShowJsonSpec] = useState(false);

  const fetchLineage = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDataLineage();
      setLineage(data);
      if (data.nodes.length > 0 && !selectedNode) {
        setSelectedNode(data.nodes[7]); // Seleccionar curated por defecto
      }
    } catch (err: any) {
      setError(err.message || 'Error al cargar el linaje de datos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLineage();
  }, []);

  const getLayerColor = (layer: string) => {
    switch (layer.toLowerCase()) {
      case 'fuente externa':
        return 'from-amber-500/20 to-amber-600/10 border-amber-500/40 text-amber-400';
      case 'bronze':
        return 'from-orange-600/20 to-amber-700/10 border-amber-600/40 text-amber-300';
      case 'silver':
        return 'from-slate-400/20 to-slate-500/10 border-slate-400/40 text-slate-300';
      case 'calidad':
        return 'from-emerald-500/20 to-teal-600/10 border-emerald-500/40 text-emerald-400';
      case 'gold':
        return 'from-yellow-400/20 to-amber-500/10 border-yellow-400/40 text-yellow-300';
      case 'orquestación':
        return 'from-cyan-500/20 to-blue-600/10 border-cyan-500/40 text-cyan-400';
      case 'consumo':
        return 'from-blue-600/20 to-indigo-600/10 border-blue-500/40 text-blue-400';
      default:
        return 'from-slate-700/20 to-slate-800/10 border-slate-700 text-slate-300';
    }
  };

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'api':
        return <ExternalLink className="w-4 h-4 text-amber-400" />;
      case 'pipeline':
        return <Cpu className="w-4 h-4 text-cyan-400" />;
      case 'datalake':
        return <HardDrive className="w-4 h-4 text-orange-400" />;
      case 'table':
        return <Database className="w-4 h-4 text-blue-400" />;
      case 'quality_gate':
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case 'service':
        return <Server className="w-4 h-4 text-indigo-400" />;
      case 'dashboard':
        return <Layers className="w-4 h-4 text-purple-400" />;
      default:
        return <GitFork className="w-4 h-4 text-slate-400" />;
    }
  };

  if (loading && !lineage) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-28 bg-slate-900/60 border border-slate-800 rounded-2xl"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-44 bg-slate-900/60 border border-slate-800 rounded-2xl"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Cabecera Principal */}
      <div className="bg-slate-900/70 border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="p-2.5 bg-blue-500/10 border border-blue-500/30 rounded-xl text-blue-400">
              <GitFork className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                Linaje de Datos y Gobernanza Medallion
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/40 font-mono">
                  OpenMetadata Spec
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Trazabilidad integral de activos de datos: Ingesta USGS, Lago Bronze MinIO, Silver Staging, Compuerta Pandera y Curated Gold.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowJsonSpec(!showJsonSpec)}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700/80 transition-colors"
          >
            <FileCode className="w-3.5 h-3.5 text-indigo-400" />
            <span>{showJsonSpec ? 'Ocultar JSON' : 'Ver Spec OpenMetadata'}</span>
          </button>

          <button
            onClick={fetchLineage}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-blue-600/30 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Actualizar Métricas</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-2xl text-xs text-red-300 flex items-center gap-3">
          <Info className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Banner Informativo Docker Desktop & OpenMetadata */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 p-4 rounded-2xl">
          <div className="flex items-center space-x-2 text-blue-400 text-xs font-bold uppercase tracking-wider mb-2">
            <Server className="w-4 h-4" />
            <span>Servidor OpenMetadata</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed mb-3">
            Para observar el linaje formal en OpenMetadata UI con OpenSearch y MySQL:
          </p>
          <div className="bg-slate-950 border border-slate-800 p-2 rounded-lg font-mono text-[11px] text-emerald-400 select-all mb-3">
            docker compose -f docker-compose.openmetadata.yml up -d
          </div>
          <a
            href="http://localhost:8585"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 font-semibold"
          >
            <span>Abrir OpenMetadata (Puerto 8585)</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 p-4 rounded-2xl">
          <div className="flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-wider mb-2">
            <HardDrive className="w-4 h-4" />
            <span>Persistencia en Docker Desktop</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed mb-2">
            Los datos y metadatos se almacenan persistentemente en volúmenes nombrados visibles en Docker Desktop:
          </p>
          <ul className="text-[11px] text-slate-400 space-y-1 font-mono">
            <li>• <span className="text-blue-300">postgres_data</span>: Tablas raw, staging y curated</li>
            <li>• <span className="text-orange-300">minio_data</span>: Data Lake Bronze GeoJSON</li>
            <li>• <span className="text-purple-300">airflow_logs</span>: Auditoría y trazas de DAGs</li>
          </ul>
        </div>

        <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 p-4 rounded-2xl">
          <div className="flex items-center space-x-2 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-2">
            <ShieldCheck className="w-4 h-4" />
            <span>Gobernanza y Calidad Pandera</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed mb-2">
            Compuerta de calidad declarativa bloqueante antes de Silver a Gold:
          </p>
          <ul className="text-[11px] text-slate-400 space-y-1">
            <li>• <span className="text-emerald-300 font-semibold">Tolerancia a Fallos:</span> Descarte inmediato y trazabilidad de excepciones.</li>
            <li>• <span className="text-emerald-300 font-semibold">Geometría:</span> Latitud [-90, 90], Longitud [-180, 180].</li>
            <li>• <span className="text-emerald-300 font-semibold">Frescura:</span> Detección de desfases temporales.</li>
          </ul>
        </div>
      </div>

      {/* Visor de Especificación JSON OpenMetadata */}
      {showJsonSpec && lineage && (
        <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
            <span className="text-xs font-mono text-indigo-400 font-semibold">
              pipeline_metadata.json (OpenMetadata Specification 1.3)
            </span>
            <span className="text-xs text-slate-500">
              Ubicación: docs/openmetadata/pipeline_metadata.json
            </span>
          </div>
          <pre className="text-[11px] font-mono text-slate-300 max-h-72 overflow-y-auto p-3 bg-slate-900/60 rounded-xl border border-slate-800">
            {JSON.stringify(lineage, null, 2)}
          </pre>
        </div>
      )}

      {/* Flujo Visual Medallion Interactivo */}
      {lineage && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Columna Izquierda: Nodos del Pipeline en 2 columnas */}
          <div className="lg:col-span-2 space-y-4">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-400" />
              <span>Activos y Nodos del Pipeline de Datos ({lineage.nodes.length} nodos)</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {lineage.nodes.map((node) => {
                const isSelected = selectedNode?.id === node.id;
                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    className={`cursor-pointer p-3.5 rounded-xl border transition-all bg-gradient-to-br ${getLayerColor(
                      node.layer
                    )} ${
                      isSelected
                        ? 'ring-2 ring-blue-500 shadow-lg shadow-blue-500/20 scale-[1.01]'
                        : 'hover:border-slate-600 opacity-90 hover:opacity-100'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-2">
                        {getNodeIcon(node.type)}
                        <span className="text-xs font-bold text-white">{node.name}</span>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-mono uppercase bg-slate-900/80 border border-slate-700/60">
                        {node.layer}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-300 mt-2 line-clamp-2">
                      {node.description}
                    </p>

                    <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-800/60">
                      <span className="text-[10px] text-slate-400 font-mono">
                        Tipo: {node.type}
                      </span>
                      {node.record_count !== null && node.record_count !== undefined ? (
                        <span className="text-[11px] font-bold text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          {node.record_count.toLocaleString()} registros
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500 font-mono">En tiempo real</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Cadena de Relaciones (Lineage Edges) */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 mt-4">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-3">
                Conexiones de Linaje Activas ({lineage.edges.length} relaciones upstream/downstream)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {lineage.edges.map((edge, idx) => (
                  <div
                    key={idx}
                    className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-300 bg-slate-950/80 px-2.5 py-1.5 rounded-lg border border-slate-800"
                  >
                    <span className="text-blue-400 truncate max-w-[90px]">{edge.from}</span>
                    <ArrowRight className="w-3 h-3 text-slate-500 flex-shrink-0" />
                    <span className="text-emerald-400 truncate max-w-[90px]">{edge.to}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Columna Derecha: Detalle del Nodo Seleccionado */}
          <div className="space-y-4">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Info className="w-4 h-4 text-indigo-400" />
              <span>Metadatos del Activo Seleccionado</span>
            </div>

            {selectedNode ? (
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl space-y-4 sticky top-20">
                <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-800">
                  <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                    {getNodeIcon(selectedNode.type)}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{selectedNode.name}</h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-blue-400 font-mono">{selectedNode.id}</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 uppercase font-mono">
                        {selectedNode.layer}
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                    Descripción Técnica
                  </label>
                  <p className="text-xs text-slate-200 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                    {selectedNode.description}
                  </p>
                </div>

                {selectedNode.record_count !== null && selectedNode.record_count !== undefined && (
                  <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-between">
                    <span className="text-xs text-emerald-300 font-semibold">Registros Almacenados:</span>
                    <span className="text-sm font-bold text-emerald-400 font-mono">
                      {selectedNode.record_count.toLocaleString()}
                    </span>
                  </div>
                )}

                {selectedNode.details && (
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1.5">
                      Propiedades y Configuración
                    </label>
                    <div className="space-y-1.5 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                      {Object.entries(selectedNode.details).map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between text-xs py-0.5">
                          <span className="text-slate-400 font-mono">{key}:</span>
                          <span className="text-slate-200 font-medium truncate max-w-[180px]">
                            {String(val)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-2 border-t border-slate-800 text-center">
                  <span className="text-[10px] text-slate-500 font-mono">
                    Catálogo SismoWatch • OpenMetadata Specification
                  </span>
                </div>
              </div>
            ) : (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center text-slate-500 text-xs">
                Seleccione un activo para ver sus metadatos detallados.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
