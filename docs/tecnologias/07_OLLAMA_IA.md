# Ollama & Inteligencia Artificial — Asistente Conversacional y Reportes Ejecutivos

## 1. ¿Qué es Ollama y qué rol cumple en SismoWatch?
**Ollama** es una plataforma para ejecutar modelos de lenguaje de gran escala (*Large Language Models - LLMs*) de código abierto localmente en tu propio hardware, sin enviar datos a la nube, sin costos recurrentes y con total soberanía y privacidad de la información.

En **SismoWatch**, Ollama cumple dos funciones esenciales de inteligencia artificial:
1. **Redacción Automatizada de Informes Ejecutivos Diarios (DAG `dag_daily_ai_report`):** Sintetiza la actividad sísmica global de las últimas 24 horas y evalúa la presencia de enjambres sísmicos.
2. **Asistente Conversacional Inteligente (Chatbot sobre Silver y Gold):** Permite a los usuarios consultar datos sismológicos, realizar preguntas complejas en lenguaje natural y obtener respuestas inmediatas y contextualizadas.

---

## 2. Parámetros de Conexión y Modelos Soportados

| Parámetro | Valor Local por Defecto | Variable de Entorno | Descripción |
|---|---|---|---|
| **URL del Servicio Ollama** | `http://host.docker.internal:11435` | `OLLAMA_BASE_URL` | Endpoint accesible desde los contenedores Docker |
| **Puerto Nativo en Host** | `http://127.0.0.1:11434` | N/A | Puerto en el que escucha el daemon de Ollama en la máquina |
| **Modelo Recomendado** | `llama3:latest` o `qwen2.5` | `OLLAMA_MODEL` | Modelos de alto rendimiento y razonamiento sismológico |
| **Tiempo Límite (Timeout)** | 45 segundos | `OLLAMA_TIMEOUT` | Tiempo máximo de espera por generación |

---

## 3. Las Dos Funciones de Inteligencia Artificial

### 3.1 Función 1: Generación de Reportes Diarios con Guardrails
El DAG de Airflow [`dag_daily_ai_report`](file:///home/cohorte5/Escritorio/PBD-sismowatch/airflow/dags/dag_daily_ai_report.py) se ejecuta cada día a las 06:00 UTC siguiendo este patrón estricto para evitar alucinaciones:

```
[ Capa Gold: SQL ] ──► [ Detección Z-Score ] ──► [ Contexto Estructurado ] ──► [ Ollama LLM ] ──► [ Guardrails ] ──► [ Reporte Persistido ]
(Verdad Matemática)     (Análisis de Enjambres)    (Prompt Determinista)         (Redacción)        (Validación)       (curated.ai_executive_reports)
```

1. **Verdad Matemática Fundamental:** Se calculan en SQL los números exactos (total de sismos, sismo máximo, alertas de tsunami). El LLM **nunca inventa números**, solo redacta el texto explicativo.
2. **Detección Estadística de Anomalías:** Se calcula el Z-score comparando la actividad de las últimas 24 horas con la media móvil y desviación estándar de los últimos 30 días:
   $$Z = \frac{X_{24h} - \mu_{30d}}{\sigma_{30d}}$$
   Si $Z > 2.0$, se activa una alerta formal de enjambre sísmico en el reporte.
3. **Mecanismo de Resiliencia (*Fallback*):** Si Ollama no está encendido o el sistema se encuentra en un entorno sin GPU, el sistema activa automáticamente un generador determinista que produce el informe en Markdown con los datos exactos sin interrumpir el flujo.

### 3.2 Función 2: Asistente Conversacional (Chatbot Silver & Gold)
Disponible en la pestaña **Asistente IA** de la plataforma web y a través del endpoint `POST /api/chat/query`:

- **Enrutador de Respuestas Ultrarrápido (< 10 ms):**
  - Para preguntas comunes (saludos, explicación de la arquitectura Medallón, definición de Richter vs Mercalli, o conteos directos), un clasificador semántico basado en expresiones regulares y palabras clave genera la respuesta inmediatamente sin esperar el ciclo de inferencia de la CPU.
- **Inferencia Acotada en CPU:**
  - Cuando se requiere inferencia abierta de LLM, el servicio inyecta en el prompt los datos consolidados en memoria de las capas Silver y Gold, restringiendo el parámetro `num_predict` entre 50 y 80 tokens. Esto garantiza respuestas concisas en menos de 3 a 5 segundos, evitando cuellos de botella en CPUs locales.
- **Trazabilidad de Respuestas:**
  - Cada respuesta indica si la información provino de la capa **Gold** (curada) o **Silver** (staging), y reporta el tiempo exacto de procesamiento en milisegundos.

---

## 4. Configuración de Red en Linux (Host $\leftrightarrow$ Contenedor)

En sistemas operativos Linux, el daemon de Ollama por defecto suele escuchar únicamente en `127.0.0.1:11434`, bloqueando el tráfico proveniente del puente virtual de Docker (`172.20.0.1`).

### Solución Definitiva (Opciones A y B):

#### Opción A: Configurar Ollama para escuchar en todas las interfaces (Recomendada)
Si Ollama corre como servicio de `systemd`:
1. Editar la configuración del servicio:
   ```bash
   sudo systemctl edit ollama.service
   ```
2. Agregar:
   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```
3. Reiniciar el servicio:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```

#### Opción B: Reenviador de puertos con `socat` (Sin modificar systemd)
Puedes levantar un puente ligero con `socat` que redirija las peticiones del puerto 11435 a 11434:
```bash
socat TCP-LISTEN:11435,fork,reuseaddr TCP:127.0.0.1:11434 &
```
En el archivo `docker-compose.yml`, el servicio `api` cuenta con la directiva:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```
lo cual permite que tanto la API como Airflow se comuniquen con el host local sin complicaciones.

---

## 5. Comandos Útiles para Gestionar Modelos en Ollama

```bash
# 1. Verificar si Ollama está corriendo en la máquina
curl http://localhost:11434/api/tags

# 2. Descargar el modelo recomendado Llama 3
ollama pull llama3:latest

# 3. Descargar el modelo liviano Qwen 2.5 (ideal para laptops con poca RAM)
ollama pull qwen2.5:latest

# 4. Probar una consulta rápida desde la terminal
ollama run llama3:latest "¿Qué significa la escala sismológica de Richter?"
```
