"""
SismoWatch - Configuración del Backend API
Carga de variables de entorno mediante Pydantic Settings.
"""

from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SismoWatch API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    # Base de Datos PostgreSQL (conexión con rol de aplicación sismo_app de solo lectura)
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "sismowatch"
    POSTGRES_USER: str = "sismo_app"
    POSTGRES_PASSWORD: str = "app_readonly_pass_2026"

    # Airflow API para disparar DAGs desde Admin
    AIRFLOW_API_URL: str = "http://airflow-webserver:8080/api/v1"
    AIRFLOW_ADMIN_USER: str = "sismo_admin"
    AIRFLOW_ADMIN_PASSWORD: str = "airflow_secure_admin_2026"

    # Seguridad JWT
    JWT_SECRET_KEY: str = "sismowatch_jwt_super_secret_key_2026_change_in_prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Inteligencia Artificial (Ollama)
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11435"
    OLLAMA_MODEL: str = "llama3:latest"
    AI_TIMEOUT_SECONDS: int = 25

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000"
    ]

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
