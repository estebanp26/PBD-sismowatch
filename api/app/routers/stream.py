"""
SismoWatch - Router de Streaming en Vivo (/api/stream)
Transmisión en tiempo real mediante Server-Sent Events (SSE).
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.security import require_viewer_or_admin
from app.services.stream_service import event_stream_generator

router = APIRouter(prefix="/api", tags=["Tiempo Real"])

@router.get("/stream", summary="Feed de sismos en tiempo real mediante SSE")
async def stream_earthquakes(current_user: dict = Depends(require_viewer_or_admin)):
    """
    Canal de transmisión continua Server-Sent Events (SSE).
    Emite actualizaciones de nuevos eventos sísmicos y heartbeats para reconexión automática sin recarga de página.
    """
    return StreamingResponse(
        event_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
