# Plataforma Web React — Documentación de la Interfaz de Usuario y Experiencia Analítica

## 1. ¿Qué es el Frontend de SismoWatch y qué rol cumple?
La **Plataforma Web de SismoWatch** es una aplicación de página única (*Single Page Application - SPA*) moderna construida con **React 18**, **TypeScript**, **Vite** y **Tailwind CSS**.

Cumple el rol de **interfaz de comando, visualización analítica y observabilidad en tiempo real** para operadores sismológicos, tomadores de decisiones de emergencia y administradores del pipeline de datos.

Se ejecuta en el puerto **`3000`** servida a través de un contenedor ligero de producción basado en **Nginx**.

---

## 2. Parámetros de Conexión y Accesos

| Parámetro | Valor Local por Defecto | Variable de Entorno | Descripción |
|---|---|---|---|
| **URL de la Aplicación** | [http://localhost:3000](http://localhost:3000) | `WEB_PORT=3000` | Acceso web para usuarios y analistas |
| **URL del Backend API** | `http://localhost:8000` | `VITE_API_URL` | Endpoint al que se conectan las llamadas AJAX y SSE |
| **Servidor Web** | Nginx Alpine | N/A | Servidor web HTTP inverso para archivos estáticos |
| **Cuentas Preconfiguradas** | - **Admin:** `admin` / `AdminSecurePass2026!`<br/>- **Viewer:** `viewer` / `ViewerSecurePass2026!` | N/A | Acceso rápido en el modal de autenticación |

---

## 3. Módulos y Pestañas de la Aplicación

La navegación principal se organiza en 6 pestañas especializadas:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SismoWatch Global | Dashboard | Eventos | Reportes IA | Salud Pipeline | Asistente IA | Linaje │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Pestaña 1: Dashboard Principal
- **Tarjetas de KPIs (24 horas):** Muestran el número total de eventos registrados, magnitud máxima, promedio global, alertas de tsunami activas y el porcentaje de calidad del pipeline (*Quality Score*).
- **Mapa Sísmico Interactivo (Leaflet):**
  - Mapeo geográfico de cada sismo mediante marcadores proporcionales a su magnitud.
  - Código cromático: verde (sismos menores $< 4.0$), amarillo (moderados $4.0 - 5.5$), naranja (fuertes $5.5 - 6.9$) y rojo con pulsación (severos $\ge 7.0$ o alerta de tsunami).
  - Ventana modal (*popup*) con detalles inmediatos al hacer clic en cualquier epicentro.
- **Gráficos Estadísticos:** Distribución de sismos por escala de magnitud, profundidad hipocentral y ranking de regiones con mayor actividad.

### 3.2 Pestaña 2: Feed de Eventos
- Listado tabular reactivo de todos los sismos consolidados en la capa Gold.
- **Filtros Dinámicos en Tiempo Real:** Búsqueda textual por región/país, deslizador de magnitud mínima ($0.0$ a $8.0+$) y filtro exclusivo para sismos con alerta de tsunami.
- **Paginación y Drawer de Detalle:** Permite seleccionar cualquier evento para inspeccionar sus parámetros sismológicos avanzados (`felt`, `cdi`, `mmi`, `gap`, `rms`, fuentes y coordenadas con alta precisión).

### 3.3 Pestaña 3: Reportes Ejecutivos IA
- Visualización de los informes analíticos diarios generados automáticamente por el modelo de lenguaje local (Ollama).
- Presentación en formato Markdown con tipografía estructurada: resumen ejecutivo, zonas críticas, evaluación de anomalías y recomendaciones operativas.
- **Exportación a PDF con Un Clic:** Botón directo para descargar el informe en un archivo PDF formal con membrete institucional.

### 3.4 Pestaña 4: Salud del Pipeline y Calidad
- Monitor en tiempo real de los 3 DAGs de Apache Airflow (`dag_usgs_ingest_raw`, `dag_transform_and_quality`, `dag_daily_ai_report`).
- Métricas de la compuerta de calidad Pandera (registros evaluados, aprobados y tasa de descarte).
- **Modal de Backfill (Exclusivo Admin):** Formulario para lanzar reprocesamiento histórico indicando días hacia atrás y umbral de magnitud.

### 3.5 Pestaña 5: Asistente IA (Chatbot sobre Silver y Gold)
- Asistente conversacional especializado en sismología y en los datos del lago.
- **Enrutador de Respuestas Ultrarrápido (< 10 ms):** Responde instantáneamente saludos, definiciones técnicas, estructura de la base de datos y preguntas frecuentes.
- **Consultas Analíticas en Vivo:** Consulta a Ollama sobre eventos sísmicos específicos, resúmenes regionales y estadísticas.
- **Historial Multi-Turno y Etiquetas de Trazabilidad:** Muestra si la respuesta provino de la capa Silver o Gold, el tiempo exacto de cómputo en milisegundos y sugerencias automáticas de preguntas.

### 3.6 Pestaña 6: Linaje y Flujo (OpenMetadata Spec)
- Diagrama interactivo del flujo de datos Medallón (USGS $\rightarrow$ Airflow $\rightarrow$ MinIO $\rightarrow$ Staging $\rightarrow$ Pandera $\rightarrow$ Curated $\rightarrow$ FastAPI $\rightarrow$ Web).
- Conteos dinámicos en tiempo real de registros almacenados en cada capa.
- Inspector lateral de propiedades de cada nodo (esquema, columnas, claves de idempotencia, periodicidad).
- Visor embebido de la especificación técnica en formato JSON de OpenMetadata.

---

## 4. Conexión en Tiempo Real con Server-Sent Events (SSE)

La aplicación implementa una conexión SSE unidireccional con el backend (`/api/stream`):
- En la barra de navegación superior, un indicador **"EN VIVO (SSE)"** con pulso verde confirma que el canal está abierto.
- Cuando el pipeline detecta un sismo de alta magnitud en el USGS, el evento se transmite de inmediato por la conexión SSE sin necesidad de recargar la página.
- En caso de desconexión de red, el frontend implementa reconexión automática transparente con retroceso exponencial (*exponential backoff*).

---

## 5. Compilación y Construcción del Proyecto

Para recompilar el frontend tras realizar modificaciones en el código fuente:

```bash
# 1. Ingresar al directorio de la aplicación web
cd web

# 2. Instalar dependencias (si es una nueva máquina)
npm install

# 3. Compilar TypeScript y empaquetar con Vite
npm run build

# 4. Copiar los archivos optimizados al contenedor de Nginx
docker cp dist/. sismowatch_web:/usr/share/nginx/html/
```
