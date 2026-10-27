"""
SismoWatch - Router del Chatbot Analítico de IA (/api/chat)
Endpoints para interactuar con el asistente con dominio sobre capas Silver y Gold.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_viewer_or_admin
from app.db.session import get_db
from app.schemas.earthquake import ChatQueryRequest, ChatQueryResponse
from app.services.chatbot_service import ChatbotService

router = APIRouter(prefix="/api/chat", tags=["Asistente IA Chatbot"])

@router.post("/query", response_model=ChatQueryResponse, summary="Consultar al asistente analítico sobre Silver y Gold")
def chat_query(
    payload: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_viewer_or_admin)
):
    """
    Recibe la pregunta en lenguaje natural, consulta de forma segura las capas Silver y Gold,
    y devuelve la respuesta analítica optimizada con tiempos de ejecución en milisegundos.
    """
    try:
        result = ChatbotService.process_query(payload.message, db, history=payload.history)
        return ChatQueryResponse(
            reply=result.get("reply", ""),
            data=result.get("data"),
            source_layer=result.get("source_layer", "Gold (curated)"),
            query_sql=result.get("query_sql"),
            execution_time_ms=result.get("execution_time_ms", 0.0),
            cached=result.get("cached", False),
            suggested_questions=result.get("suggested_questions", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la consulta del asistente: {str(e)}"
        )

@router.get("/suggestions", response_model=List[str], summary="Obtener preguntas sugeridas para el usuario")
def get_chat_suggestions(
    current_user: dict = Depends(require_viewer_or_admin)
):
    """Devuelve preguntas de ejemplo para acelerar la interacción del operador."""
    return ChatbotService.get_suggestions()
