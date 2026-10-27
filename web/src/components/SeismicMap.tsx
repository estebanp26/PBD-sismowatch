import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { EarthquakeEvent } from '../types';

interface SeismicMapProps {
  events: EarthquakeEvent[];
  selectedEvent: EarthquakeEvent | null;
  onSelectEvent: (event: EarthquakeEvent) => void;
}

export const SeismicMap: React.FC<SeismicMapProps> = ({
  events,
  selectedEvent,
  onSelectEvent
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      // Inicializar mapa centrado en vista global
      const map = L.map(mapContainerRef.current, {
        center: [20.0, 0.0],
        zoom: 2,
        minZoom: 2,
        maxZoom: 10,
        zoomControl: true,
      });

      // Capa base oscura Esri Dark Gray (libre de API keys y marcas de agua)
      const esriDark = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        {
          attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ | SismoWatch',
          maxZoom: 16
        }
      );

      // Capa alternativa OpenStreetMap estándar
      const osmStandard = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | SismoWatch',
        maxZoom: 19
      });

      esriDark.addTo(map);

      // Selector de capas base en la esquina superior derecha
      L.control.layers({
        'Oscuro (Esri)': esriDark,
        'Estándar (OSM)': osmStandard
      }, undefined, { position: 'topright' }).addTo(map);

      const markersGroup = L.layerGroup().addTo(map);
      markersLayerRef.current = markersGroup;
      mapInstanceRef.current = map;
    }

    return () => {
      // Cleanup al desmontar
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Actualizar marcadores cuando cambian los eventos
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    events.forEach(event => {
      const { latitude, longitude, mag, place, depth_km, time, tsunami, url } = event;

      // Color según severidad de magnitud
      let color = '#3B82F6'; // Azul < 4.0
      let fillColor = '#60A5FA';
      if (mag >= 6.0) {
        color = '#EF4444'; // Rojo fuerte
        fillColor = '#F87171';
      } else if (mag >= 4.5) {
        color = '#F59E0B'; // Ámbar
        fillColor = '#FBBF24';
      } else if (mag >= 3.0) {
        color = '#10B981'; // Verde esmeralda
        fillColor = '#34D399';
      }

      // Tamaño proporcional a magnitud (mínimo 5, máximo 20)
      const radius = Math.max(5, Math.min(22, (mag || 1) * 2.8));

      const circle = L.circleMarker([latitude, longitude], {
        radius,
        color: tsunami === 1 ? '#DC2626' : color,
        weight: tsunami === 1 ? 3 : 1.5,
        fillColor,
        fillOpacity: 0.65,
      });

      // Contenido del Popup informativo
      const popupHtml = `
        <div style="font-family: inherit; font-size: 12px; line-height: 1.4;">
          <div style="font-weight: bold; font-size: 13px; color: ${color}; margin-bottom: 4px;">
            M ${mag.toFixed(1)} - ${place}
          </div>
          <div style="color: #94A3B8; margin-bottom: 2px;">
            <b>Profundidad:</b> ${depth_km.toFixed(1)} km
          </div>
          <div style="color: #94A3B8; margin-bottom: 2px;">
            <b>Fecha UTC:</b> ${new Date(time).toUTCString()}
          </div>
          ${
            tsunami === 1
              ? '<div style="color: #EF4444; font-weight: bold; margin: 4px 0;">⚠️ ALERTA DE TSUNAMI REGISTRADA</div>'
              : ''
          }
          ${
            url
              ? `<div style="margin-top: 6px;"><a href="${url}" target="_blank" rel="noopener noreferrer" style="color: #3B82F6; text-decoration: underline;">Ver ficha oficial USGS &rarr;</a></div>`
              : ''
          }
        </div>
      `;

      circle.bindPopup(popupHtml);
      circle.on('click', () => onSelectEvent(event));

      markersLayerRef.current?.addLayer(circle);
    });
  }, [events, onSelectEvent]);

  // Centrar mapa si se selecciona un evento en la lista
  useEffect(() => {
    if (selectedEvent && mapInstanceRef.current) {
      mapInstanceRef.current.flyTo(
        [selectedEvent.latitude, selectedEvent.longitude],
        5,
        { duration: 1.5 }
      );
    }
  }, [selectedEvent]);

  return (
    <div className="relative rounded-2xl overflow-hidden border border-slate-800 shadow-2xl h-[420px] bg-slate-900">
      <div ref={mapContainerRef} className="w-full h-full" />
      {/* Leyenda de Magnitud en esquina inferior derecha */}
      <div className="absolute bottom-3 right-3 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-lg p-2.5 text-[11px] text-slate-300 shadow-lg">
        <div className="font-semibold text-slate-200 mb-1.5">Escala de Magnitud</div>
        <div className="flex items-center gap-1.5 mb-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
          <span>M &ge; 6.0 (Severo / Mayor)</span>
        </div>
        <div className="flex items-center gap-1.5 mb-1">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
          <span>M 4.5 - 5.9 (Moderado)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
          <span>M &lt; 4.5 (Menor)</span>
        </div>
      </div>
    </div>
  );
};
