"""
SismoWatch - API Principal FastAPI
Plataforma de backend para consumo gobernado, analítica en tiempo real y seguridad RBAC.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.routers import auth, events, reports, pipeline, stream, admin, chat, metadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sismowatch_api")

app = FastAPI(
    title="SismoWatch API",
    description="Plataforma de Monitoreo Sísmico Global en Tiempo Casi Real con Inteligencia Artificial y Calidad de Datos.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS restringido
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Manejador global de excepciones para evitar caídas o pantallas en blanco
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error no controlado en la ruta {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor",
            "message": "Ha ocurrido un problema al procesar la solicitud. Nuestro equipo técnico ha sido notificado.",
            "path": request.url.path
        }
    )

# Inclusión de routers
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(reports.router)
app.include_router(pipeline.router)
app.include_router(stream.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(metadata.router)

@app.get("/health", tags=["Salud"], summary="Verificación de estado de la API")
def health_check():
    """Endpoint ligero para chequeo de salud y balanceadores de carga."""
    return {"status": "HEALTHY", "service": "SismoWatch API", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
