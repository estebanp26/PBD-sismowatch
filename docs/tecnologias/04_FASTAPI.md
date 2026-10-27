# FastAPI Backend — Documentación de la API REST y Servicios en Tiempo Real

## 1. ¿Qué es FastAPI y qué rol cumple en SismoWatch?
**FastAPI** es un framework web moderno, asíncrono y de alto rendimiento para Python 3.11+, basado en tipos estándar de Python y especificaciones abiertas como OpenAPI y JSON Schema.

En **SismoWatch**, FastAPI actúa como la **capa de servicio y consumo gobernado (Consumption Layer)**. Es la pasarela segura entre los datos consolidados en la base de datos (capas Silver y Gold) y los clientes finales (la plataforma web React, herramientas de inteligencia de negocios o sistemas externos de alerta).

---

## 2. Parámetros de Conexión y Accesos

| Parámetro | Valor Local por Defecto | Variable de Entorno | Descripción |
|---|---|---|---|
| **URL Base de la API** | `http://localhost:8000` | `API_PORT=8000` | Host y puerto de escucha de Uvicorn |
| **Documentación Interactiva (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | N/A | Interfaz visual interactiva para probar endpoints |
| **Documentación Alternativa (ReDoc)** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | N/A | Especificación formal de contratos de API |
| **Rol de Base de Datos** | `sismo_app` | `APP_DB_USER` | Usuario de PostgreSQL con permisos estrictos de solo lectura |
| **Secreto Criptográfico JWT** | Definido en `.env` | `JWT_SECRET_KEY` | Firma y validación de tokens de sesión |
| **Algoritmo de Firma** | `HS256` | `JWT_ALGORITHM` | Estándar HMAC con SHA-256 |
| **Tiempo de Expiración Token** | 1440 minutos (24 horas) | `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración de la sesión activa |

---

## 3. Modelo de Autenticación y Control de Acceso por Roles (RBAC)

La API implementa seguridad basada en **Tokens JWT (Bearer Token)** y dos roles con permisos diferenciados:

| Rol | Usuarios Preconfigurados | Contraseña | Capacidades en la API |
|---|---|---|---|
| **`viewer`** | `viewer` | `ViewerSecurePass2026!` | Consulta de KPIs, listado de eventos, visualización de reportes, asistente de chat IA, linaje de datos y recepción de streaming SSE. |
| **`admin`** | `admin` | `AdminSecurePass2026!` | Todas las capacidades de `viewer` **MÁS** la ejecución de operaciones de administración (lanzamiento de backfill histórico y regeneración forzada de reportes). |

Cualquier solicitud a un endpoint protegido sin token devuelve `HTTP 401 Unauthorized`. Si un usuario con rol `viewer` intenta lanzar un backfill, recibe inmediatamente `HTTP 403 Forbidden`.

---

## 4. Catálogo Completo de Endpoints

### 4.1 Autenticación (`/auth`)
- **`POST /auth/login`**: Valida credenciales contra la tabla `curated.users` (usando verificación bcrypt) y retorna el token JWT con los datos del usuario (`username`, `full_name`, `role`).

### 4.2 Métricas y Eventos Sísmicos (`/api`)
- **`GET /api/kpis`**: Retorna el resumen ejecutivo de las últimas 24 horas (total de sismos, sismo de mayor magnitud, promedio de magnitud, alertas de tsunami activas y score de calidad del pipeline).
- **`GET /api/events`**: Consulta paginada y filtrable de eventos sísmicos en la capa Gold (`curated.earthquake_events`). Admite filtros por `page`, `page_size`, `min_magnitude`, `region`, `tsunami_only`, `start_date` y `end_date`.
- **`GET /api/events/{event_id}`**: Detalle técnico completo de un sismo individual.
- **`GET /api/stats`**: Agregaciones para gráficos (distribución por magnitud, profundidad, regiones más activas).

### 4.3 Reportes de Inteligencia y Descarga PDF (`/api/reports`)
- **`GET /api/reports`**: Listado de reportes ejecutivos diarios generados por el pipeline de IA.
- **`GET /api/reports/latest`**: Último reporte ejecutivo consolidado.
- **`GET /api/reports/{report_id}/pdf`**: Generación dinámica y descarga en streaming de un informe ejecutivo en formato **PDF formal** listo para imprimir o compartir.

### 4.4 Streaming en Tiempo Real (`/api/stream`)
- **`GET /api/stream`**: Endpoint **Server-Sent Events (SSE)**. Mantiene una conexión HTTP persistente y empuja notificaciones automáticas al frontend cuando ocurren nuevos sismos de magnitud relevante o alertas de tsunami sin necesidad de sondeos continuos (*polling*).

### 4.5 Asistente de IA Chatbot (`/api/chat`)
- **`POST /api/chat/query`**: Consulta conversacional al asistente sobre las capas Silver y Gold. Cuenta con un **enrutador de intenciones ultrarrápido (< 10 ms)** para saludos, preguntas frecuentes y conceptos sismológicos, y conexión contextual con Ollama para consultas analíticas complejas.
- **`GET /api/chat/suggestions`**: Sugerencias dinámicas de preguntas para el usuario.

### 4.6 Linaje de Datos y Metadatos (`/api/metadata`)
- **`GET /api/metadata/lineage`**: Retorna el gráfico de linaje de datos de punta a punta (nodos, relaciones, herramientas) y los **conteos de registros en tiempo real** de cada capa Medallón, compatible con la especificación de OpenMetadata.

### 4.7 Acciones de Administración (`/api/admin`) *(Protegidas: Solo Admin)*
- **`POST /api/admin/backfill`**: Activa el DAG de Airflow de ingesta histórica especificando días hacia atrás y magnitud mínima.
- **`POST /api/admin/reports/regenerate`**: Fuerza la regeneración inmediata del informe ejecutivo del día actual mediante Airflow y Ollama.

### 4.8 Chequeo de Salud (`/health`) *(Público)*
- **`GET /health`**: Endpoint ligero sin autenticación para monitoreo de contenedores, balanceadores de carga y health checks de Docker. Responde `{"status": "HEALTHY", "service": "SismoWatch API", "version": "1.0.0"}`.

---

## 5. Arquitectura de Seguridad y Buenas Prácticas

1. **Principio de Mínimo Privilegio en Base de Datos**: La API se conecta a PostgreSQL utilizando el usuario `sismo_app`, el cual tiene revocado cualquier permiso de escritura (`INSERT`, `UPDATE`, `DELETE`, `DROP`). Si la API sufriese una vulnerabilidad, la base de datos es inmune a alteraciones directas.
2. **CORS Restringido**: Configurado mediante `CORSMiddleware` para permitir solicitudes únicamente desde los orígenes autorizados (por defecto `http://localhost:3000`).
3. **Manejador Global de Excepciones**: Captura cualquier error no controlado y devuelve una respuesta JSON estructurada con código HTTP 500, impidiendo que se filtren trazas de código o credenciales internas al cliente.

---

## 6. Comandos Operativos y Pruebas con `curl`

```bash
# 1. Obtener Token JWT con el usuario viewer
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"viewer","password":"ViewerSecurePass2026!"}' | jq -r .access_token)

# 2. Consultar los KPIs usando el token obtenido
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/kpis | jq .

# 3. Consultar el linaje de datos en tiempo real
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/metadata/lineage | jq .

# 4. Hacer una consulta al Chatbot de IA
curl -s -X POST http://localhost:8000/api/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Cuántos sismos han ocurrido en las últimas 24 horas?"}' | jq .
```
