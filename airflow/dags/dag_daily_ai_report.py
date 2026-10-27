"""
### DAG: Reporte Ejecutivo Diario con IA y Detección de Anomalías Sísmicas
Calcula de manera 100% determinista los KPIs en SQL/Python sobre la capa Curated,
ejecuta algoritmos estadísticos (Z-score) para detectar enjambres y anomalías,
y genera el reporte narrativo ejecutivo mediante Ollama (Qwen2.5) con guardrails numéricos y fallback.
"""

from datetime import datetime, timedelta
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from airflow import DAG
from airflow.operators.python import PythonOperator

from include.analytics.anomaly_detection import SeismicAnalyticsService
from include.clients.ai_client import AIReportGenerator
from include.alerts import failure_alert_callback

logger = logging.getLogger(__name__)

default_args = {
    "owner": "sismowatch_data_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
    "execution_timeout": timedelta(minutes=6),
    "on_failure_callback": failure_alert_callback
}

def compute_deterministic_kpis_task(**context) -> None:
    """Calcula indicadores estadísticos exactos de las últimas 24 horas en SQL con try-catch."""
    ti = context.get("ti")
    try:
        metrics, top_regions, highlight = SeismicAnalyticsService.calculate_deterministic_kpis(hours_back=24)
        if ti:
            ti.xcom_push(key="kpis", value=metrics)
            ti.xcom_push(key="top_regions", value=top_regions)
            ti.xcom_push(key="highlight", value=highlight)
        logger.info(f"[AIRFLOW ÉXITO]: KPIs calculados exitosamente: {metrics}")
    except Exception as kpi_err:
        logger.error(f"[AIRFLOW ERROR KPIS]: Error calculando KPIs deterministas: {kpi_err}", exc_info=True)
        if ti:
            fallback_metrics = {"total_events": 0, "max_magnitude": 0.0, "avg_magnitude": 0.0, "tsunami_alerts": 0}
            ti.xcom_push(key="kpis", value=fallback_metrics)
            ti.xcom_push(key="top_regions", value=[])
            ti.xcom_push(key="highlight", value=None)
            ti.xcom_push(key="kpi_error", value=str(kpi_err))

def detect_anomalies_task(**context) -> int:
    """Ejecuta algoritmo Z-score para identificar enjambres sísmicos y eventos extremos con try-catch."""
    ti = context.get("ti")
    try:
        anomalies = SeismicAnalyticsService.detect_and_record_anomalies(hours_back=24, z_score_threshold=2.0)
        logger.info(f"[AIRFLOW ÉXITO ANOMALÍAS]: Análisis de anomalías finalizado: {len(anomalies)} alertas generadas.")
        if ti:
            ti.xcom_push(key="anomalies_count", value=len(anomalies))
        return len(anomalies)
    except Exception as anom_err:
        logger.error(f"[AIRFLOW ERROR ANOMALÍAS]: Error durante el cálculo de Z-score: {anom_err}", exc_info=True)
        if ti:
            ti.xcom_push(key="anomalies_error", value=str(anom_err))
        return 0

def generate_ai_report_task(**context) -> None:
    """
    Invoca al generador de IA con guardrails numéricos y try-catch resiliente:
    - Las cifras provienen estrictamente del cálculo previo.
    - Se verifica coincidencia de números.
    - Se activa fallback si el LLM no responde o alucina, sin romper el DAG.
    """
    ti = context.get("ti")
    try:
        metrics = ti.xcom_pull(key="kpis", task_ids="compute_deterministic_kpis") if ti else None
        top_regions = ti.xcom_pull(key="top_regions", task_ids="compute_deterministic_kpis") if ti else None
        highlight = ti.xcom_pull(key="highlight", task_ids="compute_deterministic_kpis") if ti else None

        if not metrics:
            try:
                metrics, top_regions, highlight = SeismicAnalyticsService.calculate_deterministic_kpis(hours_back=24)
            except Exception as kpi_retry_err:
                logger.warning(f"[AVISO AIRFLOW]: Recálculo de KPIs falló: {kpi_retry_err}. Usando valores seguros.")
                metrics = {"total_events": 0, "max_magnitude": 0.0, "avg_magnitude": 0.0, "tsunami_alerts": 0}
                top_regions = []
                highlight = None

        generator = AIReportGenerator()
        result = generator.generate_daily_executive_report(
            metrics=metrics,
            top_regions=top_regions or [],
            highlight_event=highlight
        )
        logger.info(f"[AIRFLOW ÉXITO REPORTE]: Reporte diario generado. Estado: {result.get('status')}, ID: {result.get('report_id')}")

        # Persistencia en MinIO S3 Lakehouse - Capa Curated (Oro: Reportes Ejecutivos)
        try:
            from include.clients.s3_client import S3LakeClient
            s3_client = S3LakeClient()
            report_id = result.get("report_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_client.upload_curated_report(result, report_id=str(report_id))
        except Exception as s3_err:
            logger.warning(f"[AVISO S3 CURATED]: Aviso al guardar reporte en S3 Curated: {s3_err}")

    except Exception as report_err:
        logger.error(f"[AIRFLOW ERROR REPORTE IA]: Error al generar reporte ejecutivo con IA: {report_err}", exc_info=True)
        if ti:
            ti.xcom_push(key="report_generation_error", value=str(report_err))

with DAG(
    dag_id="dag_daily_ai_report",
    default_args=default_args,
    description="Generación diaria de reporte ejecutivo con IA y detección de anomalías",
    schedule_interval="0 6 * * *",  # Todos los días a las 06:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ai", "ollama", "qwen2.5", "analytics", "anomalies", "reports"],
    doc_md=__doc__
) as dag:

    kpi_task = PythonOperator(
        task_id="compute_deterministic_kpis",
        python_callable=compute_deterministic_kpis_task
    )

    anomaly_task = PythonOperator(
        task_id="detect_seismic_anomalies",
        python_callable=detect_anomalies_task
    )

    report_task = PythonOperator(
        task_id="generate_ai_narrative_report",
        python_callable=generate_ai_report_task
    )

    kpi_task >> [anomaly_task, report_task]
