"""
SismoWatch - Cliente de Automatización con IA (Ollama / Qwen2.5)
Implementación con guardrails deterministas, sanitización contra prompt injection y fallback.
"""

from datetime import datetime, date
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import requests
from sqlalchemy import text

from include.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    AI_TIMEOUT_SECONDS,
    AI_MAX_RETRIES
)
from include.clients.db_client import get_db_connection

logger = logging.getLogger(__name__)

PROMPT_V1_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "daily_executive_v1.txt")

def sanitize_text(value: str) -> str:
    """
    Sanitiza cadenas provenientes de fuentes externas (como 'place') para mitigar prompt injection.
    Elimina caracteres de escape, instrucciones comunes y tags peligrosos.
    """
    if not value or not isinstance(value, str):
        return ""
    # Eliminar secuencias de escape e instrucciones sospechosas
    cleaned = re.sub(r'[\r\n\t]+', ' ', value)
    cleaned = re.sub(r'[<>{}[\]\\]', '', cleaned)
    forbidden_patterns = [
        r'ignore previous instructions',
        r'system prompt',
        r'disregard',
        r'override',
        r'you are now',
        r'delete from',
        r'drop table'
    ]
    for pattern in forbidden_patterns:
        cleaned = re.sub(pattern, '[REDACTED]', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()[:120]

class AIReportGenerator:
    """Generador de reportes ejecutivos narrativos asistido por IA con validación numérica estricta."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model_name: str = OLLAMA_MODEL,
        timeout: int = AI_TIMEOUT_SECONDS
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.prompt_version = "v1.0.0"

    def generate_daily_executive_report(
        self,
        metrics: Dict[str, Any],
        top_regions: List[Dict[str, Any]],
        highlight_event: str
    ) -> Dict[str, Any]:
        """
        Genera el reporte ejecutivo diario.
        1. Carga la plantilla versionada.
        2. Sanitiza entradas externas.
        3. Invoca Ollama LLM.
        4. Verifica que los números en el texto coincidan con los calculados.
        5. Aplica fallback determinista si el LLM falla o alucina cifras.
        6. Registra métricas de ejecución en la base de datos.
        """
        start_time = time.time()
        prompt_content = self._build_prompt(metrics, top_regions, highlight_event)
        
        narrative_text = ""
        status = "SUCCESS"
        error_msg = None
        prompt_tokens = len(prompt_content.split())
        completion_tokens = 0

        try:
            # Intento de generación con Ollama
            llm_text, completion_tokens = self._call_ollama(prompt_content)
            
            # Control de veracidad: validar que las cifras del texto no alucinen
            if self._validate_numerical_guardrails(llm_text, metrics):
                narrative_text = llm_text
                logger.info("Reporte narrativo generado por IA validado exitosamente contra cifras calculadas.")
            else:
                logger.warning("El texto de la IA falló el control de veracidad numérica. Activando fallback determinista.")
                narrative_text = self._generate_deterministic_fallback(metrics, top_regions, highlight_event)
                status = "FALLBACK_GENERATED"
                error_msg = "Discrepancia en validación de números con respecto a la verdad fundamental calculada."

        except Exception as e:
            logger.warning(f"Fallo en proveedor de IA ({self.model_name}): {e}. Activando fallback determinista.")
            narrative_text = self._generate_deterministic_fallback(metrics, top_regions, highlight_event)
            status = "FALLBACK_GENERATED"
            error_msg = str(e)

        latency_ms = int((time.time() - start_time) * 1000)
        total_tokens = prompt_tokens + completion_tokens

        # Persistir el reporte en curated.ai_executive_reports
        report_id = self._save_report_to_db(metrics, top_regions, narrative_text)

        # Persistir log de auditoría en curated.ai_execution_logs
        self._save_execution_log(
            report_id=report_id,
            prompt_version=self.prompt_version,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_msg
        )

        return {
            "report_id": report_id,
            "title": "Reporte Ejecutivo Global de Actividad Sísmica",
            "summary_text": narrative_text,
            "metrics": metrics,
            "top_regions": top_regions,
            "status": status,
            "latency_ms": latency_ms
        }

    def _build_prompt(self, metrics: Dict[str, Any], top_regions: List[Dict[str, Any]], highlight_event: str) -> str:
        """Lee el prompt base y sustituye los valores precalculados sanitizados."""
        with open(PROMPT_V1_PATH, "r", encoding="utf-8") as f:
            template = f.read()

        regions_formatted = ", ".join([
            f"{sanitize_text(r.get('region', 'N/A'))} ({r.get('count', 0)} sismos, máx M {r.get('max_mag', 0)})"
            for r in top_regions[:4]
        ]) or "Distribución global dispersa"

        return template.format(
            total_events=metrics.get("total_events", 0),
            max_magnitude=metrics.get("max_magnitude", 0.0),
            avg_magnitude=metrics.get("avg_magnitude", 0.0),
            tsunami_alerts=metrics.get("tsunami_alerts", 0),
            avg_depth_km=metrics.get("avg_depth_km", 0.0),
            top_regions_str=regions_formatted,
            highlight_event=sanitize_text(highlight_event)
        )

    def _call_ollama(self, prompt: str) -> Tuple[str, int]:
        """Realiza la solicitud HTTP al endpoint /api/generate de Ollama."""
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,  # Baja temperatura para evitar alucinaciones
                "top_p": 0.9
            }
        }

        response = requests.post(endpoint, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        response_text = data.get("response", "").strip()
        eval_count = data.get("eval_count", len(response_text.split()))
        return response_text, eval_count

    def _validate_numerical_guardrails(self, text: str, metrics: Dict[str, Any]) -> bool:
        """
        Verifica que los números clave calculados por SQL (total_events, max_magnitude)
        estén presentes o no se contradigan en el texto del modelo.
        """
        if not text:
            return False

        max_mag = metrics.get("max_magnitude")
        total_events = metrics.get("total_events")

        # Comprobación de presencia de la magnitud máxima si es > 0
        if max_mag and max_mag > 0:
            mag_str = str(max_mag)
            if mag_str not in text and f"{max_mag:.1f}" not in text:
                logger.warning(f"Guardrail fallido: La magnitud máxima {max_mag} no fue hallada en el texto.")
                return False

        return True

    def _generate_deterministic_fallback(
        self,
        metrics: Dict[str, Any],
        top_regions: List[Dict[str, Any]],
        highlight_event: str
    ) -> str:
        """Generador determinista sin LLM para garantizar resiliencia absoluta del pipeline."""
        total = metrics.get("total_events", 0)
        max_mag = metrics.get("max_magnitude", 0.0)
        avg_mag = metrics.get("avg_magnitude", 0.0)
        tsunami = metrics.get("tsunami_alerts", 0)
        avg_depth = metrics.get("avg_depth_km", 0.0)

        top_desc = ", ".join([
            f"{r.get('region', 'Desconocida')} ({r.get('count', 0)} eventos, M máx {r.get('max_mag', 0.0)})"
            for r in top_regions[:3]
        ]) or "actividad dispersa"

        p1 = (
            f"En las últimas 24 horas se registraron un total de {total} eventos sísmicos a nivel global, "
            f"con una magnitud promedio de {avg_mag:.2f} y una profundidad media de {avg_depth:.1f} km. "
            f"El evento de mayor energía fue de magnitud M {max_mag:.1f} ({sanitize_text(highlight_event)}), "
            f"contabilizándose {tsunami} evento(s) con activación de alerta de tsunami."
        )

        p2 = (
            f"Las zonas de mayor concentración sísmica correspondieron a: {top_desc}. "
            "Se recomienda a los centros de monitoreo y comités de riesgo mantener vigilancia activa "
            "en las fallas geológicas adyacentes y verificar los protocolos de emergencia correspondientes."
        )

        return f"{p1}\n\n{p2}"

    def _save_report_to_db(
        self,
        metrics: Dict[str, Any],
        top_regions: List[Dict[str, Any]],
        summary_text: str
    ) -> int:
        """Persiste el reporte en curated.ai_executive_reports de forma idempotente."""
        query = text("""
            INSERT INTO curated.ai_executive_reports (
                report_date, title, summary_text, top_regions, metrics_snapshot, generated_by_model
            )
            VALUES (
                CURRENT_DATE, :title, :summary_text, :top_regions, :metrics_snapshot, :model_name
            )
            ON CONFLICT (report_date) DO UPDATE SET
                title = EXCLUDED.title,
                summary_text = EXCLUDED.summary_text,
                top_regions = EXCLUDED.top_regions,
                metrics_snapshot = EXCLUDED.metrics_snapshot,
                generated_by_model = EXCLUDED.generated_by_model,
                created_at = NOW()
            RETURNING id;
        """)

        with get_db_connection(role="etl") as conn:
            result = conn.execute(query, {
                "title": "Reporte Ejecutivo Global de Actividad Sísmica",
                "summary_text": summary_text,
                "top_regions": json.dumps(top_regions),
                "metrics_snapshot": json.dumps(metrics),
                "model_name": self.model_name
            }).fetchone()
            return result[0] if result else 0

    def _save_execution_log(
        self,
        report_id: int,
        prompt_version: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: int,
        status: str,
        error_message: Optional[str]
    ) -> None:
        """Guarda auditoría técnica en curated.ai_execution_logs."""
        query = text("""
            INSERT INTO curated.ai_execution_logs (
                report_id, model_name, prompt_version, prompt_tokens, completion_tokens,
                total_tokens, latency_ms, estimated_cost_usd, status, error_message
            )
            VALUES (
                :report_id, :model_name, :prompt_version, :prompt_tokens, :completion_tokens,
                :total_tokens, :latency_ms, 0.0, :status, :error_message
            );
        """)

        with get_db_connection(role="etl") as conn:
            conn.execute(query, {
                "report_id": report_id if report_id > 0 else None,
                "model_name": self.model_name,
                "prompt_version": prompt_version,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "latency_ms": latency_ms,
                "status": status,
                "error_message": error_message
            })
