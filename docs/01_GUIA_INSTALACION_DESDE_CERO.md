# Guía de Instalación y Despliegue desde Cero (Nueva Máquina)

Esta guía detalla el procedimiento paso a paso para clonar, configurar, desplegar y validar la plataforma **SismoWatch** en un equipo o servidor completamente nuevo (Linux, Windows con WSL2 o macOS).

---

## 1. Requisitos Previos del Sistema

### 1.1 Hardware Recomendado
- **Procesador:** CPU de 4 núcleos o superior (x86_64 o Apple Silicon ARM64).
- **Memoria RAM:** 
  - Mínimo: **8 GB de RAM** (ejecutando el stack base con fallback determinista de IA).
  - Recomendado: **16 GB de RAM** (para ejecutar Ollama localmente con LLMs y OpenMetadata).
- **Almacenamiento:** Mínimo **20 GB de espacio libre en disco** (para imágenes Docker, volúmenes y modelos de IA).

### 1.2 Software Requerido
Antes de comenzar, asegúrate de tener instalado en la máquina destino:
1. **Git:** Para clonar el repositorio (`git --version`).
2. **Docker Engine y Docker Compose:**
   - Docker versión $\ge$ 24.0.
   - Docker Compose versión $\ge$ v2.20 (integrado en `docker compose`).
   - *En Windows / macOS:* Instalar **Docker Desktop** y verificar que esté encendido.
3. **Ollama (Opcional pero recomendado):** Para ejecutar el modelo de lenguaje de forma local. Si no se instala, el sistema utilizará automáticamente el generador determinista sin romperse.

---

## 2. Paso 1: Clonar el Repositorio

Abre una terminal y clona el código fuente en la máquina destino:

```bash
# Clonar el proyecto
git clone <URL_DEL_REPOSITORIO> PBD-sismowatch

# Ingresar a la carpeta raíz del proyecto
cd PBD-sismowatch
```

---

## 3. Paso 2: Configurar las Variables de Entorno (`.env`)

El proyecto incluye una plantilla completa llamada `.env.example`. Copia esta plantilla para crear el archivo `.env`:

```bash
cp .env.example .env
```

### 3.1 Generar la Clave Fernet de Airflow y Clave JWT
Para que Apache Airflow y la API de FastAPI puedan encriptar conexiones y firmar tokens de forma segura, genera claves criptográficas seguras:

```bash
# Generar clave Fernet para Airflow con Python
python3 -c "from cryptography.fernet import Fernet; print('AIRFLOW__CORE__FERNET_KEY=' + Fernet.generate_key().decode())"

# Generar clave secreta para JWT
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```
Copia los valores resultantes en tu archivo `.env`.

*(Nota: Si usas las credenciales por defecto incluidas en `.env.example`, el sistema funcionará de inmediato para desarrollo local).*

---

## 4. Paso 3: Desplegar la Plataforma con Docker Compose

El despliegue completo de la infraestructura se ejecuta con un único comando:

```bash
docker compose up -d --build
```

### ¿Qué hace este comando automáticamente?
1. **Red Virtual:** Crea la red aislada `pbd-sismowatch_sismowatch_net`.
2. **PostgreSQL 16:** Levanta la base de datos y ejecuta los scripts de [`db/init/`](file:///home/cohorte5/Escritorio/PBD-sismowatch/db/init/):
   - Crea los esquemas `raw`, `staging` y `curated`.
   - Crea los 4 roles con mínimo privilegio (`postgres`, `sismo_ingest`, `sismo_etl`, `sismo_app`).
   - Crea las tablas con sus índices y carga los usuarios iniciales (`admin` y `viewer`).
3. **MinIO S3:** Inicia el lago de datos en los puertos 9000 (API) y 9001 (Consola) y crea el bucket `sismowatch-lake`.
4. **Airflow Init:** Ejecuta las migraciones de base de datos de Airflow y crea el usuario `sismo_admin`.
5. **Airflow Scheduler y Webserver:** Inician el motor de orquestación de DAGs en el puerto 8080.
6. **FastAPI Backend:** Compila y levanta la API REST en el puerto 8000 con conexión de solo lectura vía `sismo_app`.
7. **React Frontend:** Construye y sirve la aplicación web mediante Nginx en el puerto 3000.

---

## 5. Paso 4: Verificación de Salud del Sistema (Sanity Checks)

Una vez finalizada la construcción, verifica que todos los contenedores se encuentren en estado `Up` y `healthy`:

```bash
# 1. Comprobar estado de los contenedores
docker compose ps

# Debe mostrar 6 contenedores activos:
# - sismowatch_postgres (healthy)
# - sismowatch_minio (Up)
# - sismowatch_airflow_scheduler (Up)
# - sismowatch_airflow_webserver (Up)
# - sismowatch_api (Up)
# - sismowatch_web (Up)

# 2. Verificar salud de la API
curl -s http://localhost:8000/health
# Respuesta esperada: {"status":"HEALTHY","service":"SismoWatch API","version":"1.0.0"}

# 3. Verificar que el frontend responda
curl -I http://localhost:3000
# Respuesta esperada: HTTP/1.1 200 OK
```

---

## 6. Paso 5: Accesos y Credenciales del Sistema

Ya puedes abrir tu navegador web y acceder a cada uno de los servicios:

| Servicio | URL de Acceso | Usuario | Contraseña |
|---|---|---|---|
| **Plataforma Web (SismoWatch)** | [http://localhost:3000](http://localhost:3000) | `admin`<br/>`viewer` | `AdminSecurePass2026!`<br/>`ViewerSecurePass2026!` |
| **API REST (Documentación Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | N/A | Autenticación JWT mediante botón *Authorize* |
| **Apache Airflow (DAGs)** | [http://localhost:8080](http://localhost:8080) | `sismo_admin` | `airflow_secure_admin_2026` |
| **MinIO Console (S3 Lake)** | [http://localhost:9001](http://localhost:9001) | `minio_admin` | `minio_secret_pass_2026` |
| **PostgreSQL (Conexión Directa)** | `localhost:5432` (BD: `sismowatch`) | `postgres` | `postgres_secure_pass_2026` |

---

## 7. Paso 6: Configurar Ollama para Inteligencia Artificial (Opcional)

Si deseas contar con el asistente conversacional interactivo y la redacción de informes con IA local:

### 7.1 Instalar Ollama en la máquina anfitriona
- **Linux:**
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```
- **macOS / Windows:** Descargar el instalador oficial desde [https://ollama.com/download](https://ollama.com/download).

### 7.2 Descargar los Modelos
En una terminal de tu máquina física, descarga los modelos:
```bash
# Modelo recomendado de razonamiento
ollama pull llama3:latest

# Modelo liviano alternativo
ollama pull qwen2.5:latest
```

### 7.3 Habilitar Conectividad Host $\leftrightarrow$ Docker (Solo Linux)
En Linux, Ollama se enlaza por defecto a `127.0.0.1:11434`, bloqueando peticiones de Docker. Para permitir que los contenedores se comuniquen con Ollama, ejecuta este reenviador ligero:
```bash
socat TCP-LISTEN:11435,fork,reuseaddr TCP:127.0.0.1:11434 &
```
*(En Windows y macOS con Docker Desktop, `host.docker.internal` se conecta directamente sin necesidad de socat).*

---

## 8. Paso 7 (Opcional): Desplegar OpenMetadata

Si deseas observar el catálogo oficial corporativo de metadatos y linaje en el puerto `8585`:

```bash
# Levantar el stack de OpenMetadata (MySQL + OpenSearch + Server)
docker compose -f docker-compose.openmetadata.yml up -d

# Abrir en el navegador cuando los servicios inicien (tarda aprox. 2 minutos)
# http://localhost:8585 (Credenciales: admin / admin)
```

---

## 9. Paso 8: Ejecución de Pruebas Automatizadas (Pytest)

Si deseas verificar la integridad del código fuente, las reglas de calidad de Pandera, la seguridad RBAC y los DAGs:

```bash
# 1. Crear entorno virtual de Python
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias de desarrollo y testing
pip install -r requirements-dev.txt

# 3. Ejecutar la suite completa de pruebas
pytest -v
```
**Resultado esperado:** `23 passed in ~1s`.

---

## 10. Resolución de Problemas Frecuentes (Troubleshooting)

### Error 1: "Address already in use" (Puerto ocupado)
- **Causa:** Tienes otro servicio local (ej. PostgreSQL local en el puerto 5432 o Nginx en el 80/3000) ocupando el puerto.
- **Solución:** Cambia el puerto en conflicto dentro del archivo `.env` (ej. `POSTGRES_PORT=5433` o `API_PORT=8001`) o detén el servicio nativo previo (`sudo systemctl stop postgresql`).

### Error 2: "Docker Desktop out of memory"
- **Causa:** Docker Desktop tiene asignado menos de 4 GB de RAM en sus ajustes.
- **Solución:** Abre Docker Desktop $\rightarrow$ *Settings* $\rightarrow$ *Resources* $\rightarrow$ Aumenta la memoria a mínimo 6 GB y aplica los cambios.

### Error 3: "Permission denied for docker.sock" en Linux
- **Causa:** El usuario de Linux no pertenece al grupo `docker`.
- **Solución:**
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

### Error 4: Los DAGs de Airflow tardan en aparecer en la interfaz web
- **Causa:** En el primer encendido, `airflow-scheduler` tarda entre 30 y 60 segundos en parsear la carpeta `airflow/dags/`.
- **Solución:** Espera un minuto o fuerza el refresco:
  ```bash
  docker exec -it sismowatch_airflow_scheduler airflow dags reserialize
  ```

---

## 11. Detener o Reiniciar la Plataforma

```bash
# Detener los contenedores preservando todos los datos en disco
docker compose stop

# Volver a encender los contenedores
docker compose start

# Apagar y eliminar los contenedores (los volúmenes nombrados se conservan)
docker compose down

# Apagar eliminando absolutamente todo (CUIDADO: borra los datos de la base de datos)
docker compose down -v
```
