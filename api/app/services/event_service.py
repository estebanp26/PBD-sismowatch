"""
SismoWatch - Servicio de Consulta de Eventos Sísmicos
Consultas optimizadas sobre la capa Curated con filtros y paginación.
"""

from datetime import datetime
import math
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.earthquake import EarthquakeEventSchema, PaginatedEventsResponse

class EventService:
    @staticmethod
    def get_events(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        min_mag: Optional[float] = None,
        max_mag: Optional[float] = None,
        region: Optional[str] = None,
        tsunami_only: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> PaginatedEventsResponse:
        """Consulta eventos sísmicos en curated con filtros dinámicos y paginación."""
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        if min_mag is not None:
            where_clauses.append("mag >= :min_mag")
            params["min_mag"] = min_mag

        if max_mag is not None:
            where_clauses.append("mag <= :max_mag")
            params["max_mag"] = max_mag

        if region and region.strip():
            where_clauses.append("LOWER(place) LIKE LOWER(:region)")
            params["region"] = f"%{region.strip()}%"

        if tsunami_only:
            where_clauses.append("tsunami = 1")

        if start_date is not None:
            where_clauses.append("time >= :start_date")
            params["start_date"] = start_date

        if end_date is not None:
            where_clauses.append("time <= :end_date")
            params["end_date"] = end_date

        where_sql = " AND ".join(where_clauses)

        # Conteo total con parámetros seguros
        count_query = text(f"SELECT COUNT(*) FROM curated.earthquake_events WHERE {where_sql};")  # nosec B608
        total = db.execute(count_query, params).scalar() or 0

        # Paginación
        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        data_query = text(f"""
            SELECT 
                id, mag, place, time, updated, url, status, tsunami, sig,
                mag_type, type, title, longitude, latitude, depth_km, is_updated
            FROM curated.earthquake_events
            WHERE {where_sql}
            ORDER BY time DESC
            LIMIT :limit OFFSET :offset;
        """)  # nosec B608

        rows = db.execute(data_query, params).fetchall()
        items = [
            EarthquakeEventSchema(
                id=r[0],
                mag=float(r[1]),
                place=r[2],
                time=r[3],
                updated=r[4],
                url=r[5],
                status=r[6],
                tsunami=int(r[7]),
                sig=r[8],
                mag_type=r[9],
                type=r[10],
                title=r[11],
                longitude=float(r[12]),
                latitude=float(r[13]),
                depth_km=float(r[14]),
                is_updated=bool(r[15])
            )
            for r in rows
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedEventsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
