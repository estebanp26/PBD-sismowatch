# MinIO Object Storage — Documentación Técnica y Operativa

## 1. ¿Qué es MinIO y qué rol cumple en SismoWatch?
**MinIO** es un servidor de almacenamiento de objetos de alto rendimiento 100% compatible con la API de **Amazon S3**. 

En la arquitectura de **SismoWatch**, MinIO actúa como el **Data Lakehouse en la Capa Bronze (Lago de Datos)**. Cumple el principio fundamental de ingeniería de datos: **preservar la verdad cruda e inmutable de los datos de origen**.

Cuando el orquestador (Airflow) extrae la información sísmica del servicio geológico de los Estados Unidos (USGS), almacena el archivo GeoJSON original en MinIO antes de realizar cualquier tipo de transformación, limpieza o filtrado. Si en el futuro cambian las reglas de negocio, se detecta un error de lógica o se requiere reentrenar modelos de Machine Learning, los datos originales siempre están disponibles en el lago sin alteraciones.

---

## 2. Credenciales y Parámetros de Conexión

| Parámetro | Valor Local por Defecto | Variable de Entorno | Descripción |
|---|---|---|---|
| **Consola Web (UI)** | `http://localhost:9001` | `MINIO_CONSOLE_PORT=9001` | Interfaz gráfica para navegación de buckets y objetos |
| **API S3 Endpoint** | `http://localhost:9000` | `MINIO_PORT=9000` | Endpoint S3 para clientes Python (`boto3`, `s3fs`) y Airflow |
| **Endpoint Interno Docker** | `http://minio:9000` | `AWS_ENDPOINT_URL_S3` | Comunicación interna entre contenedores |
| **Usuario Root (Access Key)** | `minio_admin` | `MINIO_ROOT_USER` | Usuario administrador |
| **Contraseña Root (Secret Key)** | `minio_secret_pass_2026` | `MINIO_ROOT_PASSWORD` | Clave secreta de acceso |
| **Bucket Principal** | `sismowatch-lake` | `S3_BUCKET_NAME` | Bucket donde reside la capa Bronze |
| **Región** | `us-east-1` | `AWS_DEFAULT_REGION` | Región estándar de compatibilidad S3 |

---

## 3. Estructura de Almacenamiento y Particionamiento

Los datos crudos se almacenan en el bucket `sismowatch-lake` siguiendo una estrategia de particionamiento por fecha jerárquica:

```text
sismowatch-lake/
└── raw/
    └── usgs/
        └── year=YYYY/
            └── month=MM/
                └── day=DD/
                    ├── usgs_all_hour_YYYYMMDD_HHMMSS.geojson
                    └── usgs_all_hour_YYYYMMDD_HHMMSS.metadata.json
```

### Ventajas de esta estructura:
1. **Evita cuellos de botella en listados S3:** Particionar por año, mes y día previene que una sola carpeta acumule cientos de miles de archivos, lo cual ralentizaría las consultas.
2. **Consultas eficientes y reprocesamiento:** Permite ejecutar tareas de backfill o reprocesamiento histórico apuntando únicamente a una fecha o rango temporal concreto (ej. `raw/usgs/year=2026/month=10/day=27/`).
3. **Inmutabilidad:** Cada archivo GeoJSON se nombra con su timestamp de ingesta y se almacena con permisos de solo lectura para los procesos downstream.

---

## 4. Persistencia en Docker Desktop

En Docker Desktop, MinIO almacena todos sus objetos de forma persistente a través del volumen nombrado:

```yaml
volumes:
  - minio_data:/data
```

- **Volumen:** `minio_data`
- **Ubicación interna:** `/data`
- **Garantía:** Aunque se apaguen, reconstruyan o reinicien los contenedores (`docker compose down && docker compose up -d`), **los datos del lago se conservan intactos en tu disco local**.

---

## 5. Operaciones Frecuentes y Comandos CLI

### 5.1 Acceso mediante Interfaz Gráfica (Navegador)
1. Abrir en el navegador: [http://localhost:9001](http://localhost:9001).
2. Ingresar usuario: `minio_admin`
3. Ingresar contraseña: `minio_secret_pass_2026`
4. Desde la consola podrás crear buckets, explorar carpetas, descargar GeoJSONs crudos y monitorear el uso de almacenamiento.

### 5.2 Uso del Cliente MinIO CLI (`mc`)
MinIO incluye la herramienta de terminal `mc` para interactuar rápidamente:

```bash
# 1. Configurar el alias local de conexión
docker run --rm -it --network pbd-sismowatch_sismowatch_net minio/mc \
  alias set sismowatch http://minio:9000 minio_admin minio_secret_pass_2026

# 2. Listar los buckets existentes
docker run --rm -it --network pbd-sismowatch_sismowatch_net minio/mc \
  ls sismowatch/

# 3. Listar archivos dentro de la capa cruda
docker run --rm -it --network pbd-sismowatch_sismowatch_net minio/mc \
  ls sismowatch/sismowatch-lake/raw/
```

### 5.3 Ejemplo de Lectura desde Python (`boto3`)
```python
import boto3
import json

s3_client = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minio_admin",
    aws_secret_access_key="minio_secret_pass_2026",
    region_name="us-east-1"
)

# Descargar y leer el último GeoJSON ingerido
response = s3_client.get_object(
    Bucket="sismowatch-lake",
    Key="raw/usgs/year=2026/month=10/day=27/usgs_latest.geojson"
)
geojson_data = json.loads(response["Body"].read().decode("utf-8"))
print(f"Total de sismos registrados en el lote: {len(geojson_data['features'])}")
```

---

## 6. Monitoreo y Resolución de Problemas

- **Verificar que el servicio está activo:**
  ```bash
  curl -I http://localhost:9000/minio/health/live
  # Debe responder: HTTP/1.1 200 OK
  ```
- **Ver logs del contenedor:**
  ```bash
  docker logs -f sismowatch_minio
  ```
- **Error habitual: Puerto 9000 o 9001 ocupado:**
  Si otro servicio local usa el puerto 9000 o 9001, puedes modificar `MINIO_PORT` o `MINIO_CONSOLE_PORT` en el archivo `.env`.
