"""
SismoWatch - Configuración Centralizada
Manejo seguro de variables de entorno para Airflow, Base de Datos, MinIO y Ollama.
"""

import os
from typing import Optional

# Base de Datos PostgreSQL
DB_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME: str = os.getenv("POSTGRES_DB", "sismowatch")
DB_SUPER_USER: str = os.getenv("POSTGRES_USER", "postgres")
DB_SUPER_PASS: str = os.getenv("POSTGRES_PASSWORD", "postgres_secure_pass_2026")

# Roles con principio de mínimo privilegio
SISMO_INGEST_USER: str = "sismo_ingest"
SISMO_INGEST_PASS: str = os.getenv("SISMO_INGEST_PASSWORD", "ingest_secret_pass_2026")

SISMO_ETL_USER: str = "sismo_etl"
SISMO_ETL_PASS: str = os.getenv("SISMO_ETL_PASSWORD", "etl_secret_pass_2026")

SISMO_APP_USER: str = "sismo_app"
SISMO_APP_PASS: str = os.getenv("SISMO_APP_PASSWORD", "app_readonly_pass_2026")

def get_connection_url(role: str = "etl") -> str:
    """Retorna la cadena de conexión de SQLAlchemy según el rol requerido."""
    if role == "ingest":
        user, pwd = SISMO_INGEST_USER, SISMO_INGEST_PASS
    elif role == "app":
        user, pwd = SISMO_APP_USER, SISMO_APP_PASS
    elif role == "admin":
        user, pwd = DB_SUPER_USER, DB_SUPER_PASS
    else:  # default 'etl'
        user, pwd = SISMO_ETL_USER, SISMO_ETL_PASS
    
    return f"postgresql+psycopg2://{user}:{pwd}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Almacenamiento MinIO / S3 Lakehouse
S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "http://minio:9000")
S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "sismowatch-lake")
AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "minio_admin")
AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "minio_secret_pass_2026")
AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# USGS Feeds y Endpoints
USGS_REALTIME_URL: str = os.getenv(
    "USGS_REALTIME_URL", 
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
)
USGS_QUERY_BASE_URL: str = os.getenv(
    "USGS_QUERY_BASE_URL",
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
)

# Inteligencia Artificial (Ollama / Qwen2.5)
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5")
AI_TIMEOUT_SECONDS: int = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "2"))
