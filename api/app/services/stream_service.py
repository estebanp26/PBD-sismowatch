"""
SismoWatch - Servicio de Streaming en Tiempo Real (Server-Sent Events)
Transmisión continua de eventos sísmicos recientes y latidos de corazón (heartbeat).
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import AsyncGenerator
from sqlalchemy import text

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

async def event_stream_generator() -> AsyncGenerator[str, None]:
    """
    Generador asíncrono para Server-Sent Events (SSE).
    Envía eventos sísmicos recientes y pulsos de sincronización para mantener la conexión activa.
    """
    last_checked_time = datetime.now(timezone.utc)

    # Envío inicial del saludo y estado en vivo
    initial_event = {
        "type": "connection_established",
        "timestamp": last_checked_time.isoformat(),
        "status": "LIVE"
    }
    yield f"data: {json.dumps(initial_event)}\n\n"

    while True:
        try:
            db = SessionLocal()
            try:
                # Buscar eventos creados o actualizados recientemente
                query = text("""
                    SELECT id, mag, place, time, status, tsunami, longitude, latitude, depth_km, title
                    FROM curated.earthquake_events
                    WHERE processed_at >= :last_time OR time >= NOW() - INTERVAL '15 minutes'
                    ORDER BY time DESC
                    LIMIT 10;
                """)
                rows = db.execute(query, {"last_time": last_checked_time}).fetchall()

                if rows:
                    events_data = [
                        {
                            "id": r[0],
                            "mag": float(r[1]),
                            "place": r[2],
                            "time": r[3].isoformat() if r[3] else None,
                            "status": r[4],
                            "tsunami": int(r[5]),
                            "longitude": float(r[6]),
                            "latitude": float(r[7]),
                            "depth_km": float(r[8]),
                            "title": r[9]
                        }
                        for r in rows
                    ]
                    payload = {
                        "type": "seismic_update",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "events": events_data
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                else:
                    # Enviar heartbeat periódico para mantener vivo el canal SSE
                    heartbeat = {
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "LIVE"
                    }
                    yield f"data: {json.dumps(heartbeat)}\n\n"

                last_checked_time = datetime.now(timezone.utc)
            finally:
                db.close()

            # Espera no bloqueante de 5 segundos antes del siguiente ciclo
            await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("Cliente desconectado del stream SSE.")
            break
        except Exception as e:
            logger.error(f"Error en el generador SSE: {e}")
            await asyncio.sleep(5)
