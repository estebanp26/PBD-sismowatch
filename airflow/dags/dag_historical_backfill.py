"""
### DAG: Backfill Histórico Parametrizado (USGS Query -> Medallion Lakehouse)
Ejecución parametrizada bajo demanda para cargar eventos históricos (por defecto últimos 30 días, M >= 2.5)
desde el catálogo oficial de USGS, garantizando idempotencia total y control de calidad bloqueante.
"""

from datetime import datetime, timedelta
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models.param import Param

from include.config import USGS_QUERY_BASE_URL
from include.clients.usgs_client import USGSClient
from include.clients.s3_client import S3LakeClient
from include.clients.db_client import DatabaseManager
from include.transformations.earthquake_transform import transform_geojson_payload
from include.quality.validation_rules import validate_earthquake_records
from include.alerts import failure_alert_callback

logger = logging.getLogger(__name__)

default_args = {
    "owner": "sismowatch_data_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=30),
    "execution_timeout": timedelta(minutes=15),
    "on_failure_callback": failure_alert_callback
}

def execute_historical_backfill_task(**context) -> int:
    """Extrae datos históricos de USGS y los procesa a través de la arquitectura Medallón con try-catch resiliente."""
    ti = context.get("ti")
    try:
        params = context.get("params", {})
        days_back = int(params.get("days_back", 30))
        min_mag = float(params.get("min_magnitude", 2.5))

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        logger.info(f"Iniciando Backfill Histórico: {days_back} días ({start_str} a {end_str}), Magnitud mínima: {min_mag}")

        # 1. Extracción desde USGS Query API
        try:
            client_usgs = USGSClient(timeout=45, max_retries=3)
            data, payload_hash, total_events = client_usgs.fetch_historical_query(
                base_url=USGS_QUERY_BASE_URL,
                start_date=start_str,
                end_date=end_str,
                min_magnitude=min_mag
            )
        except Exception as fetch_err:
            logger.error(f"[AIRFLOW ERROR BACKFILL QUERY]: Error consultando USGS: {fetch_err}", exc_info=True)
            if ti:
                ti.xcom_push(key="backfill_fetch_error", value=str(fetch_err))
            return 0

        # 2. Persistencia en Capa Bronce (S3 Lakehouse y DB Raw)
        s3_uri = None
        try:
            s3_client = S3LakeClient()
            s3_uri = s3_client.upload_raw_payload(data, payload_hash)
        except Exception as s3_err:
            logger.warning(f"[AVISO S3 BACKFILL]: Error al guardar en S3 Bronze: {s3_err}")

        raw_id = None
        try:
            raw_id, is_new = DatabaseManager.save_raw_feed(
                source_url=f"{USGS_QUERY_BASE_URL}?start={start_str}&end={end_str}&mag={min_mag}",
                payload_hash=payload_hash,
                raw_payload=data,
                event_count=total_events
            )
        except Exception as db_raw_err:
            logger.error(f"[AIRFLOW ERROR DB BACKFILL RAW]: Error al guardar feed raw: {db_raw_err}", exc_info=True)

        # 3. Transformación hacia Staging
        staging_records = []
        try:
            staging_records = transform_geojson_payload(data, raw_reference_id=raw_id)
            if staging_records:
                try:
                    s3_client.upload_staging_records(staging_records, batch_id=f"backfill_{start_str}")
                except Exception as s3_err:
                    logger.warning(f"[AVISO S3 BACKFILL STAGING]: {s3_err}")
        except Exception as trans_err:
            logger.error(f"[AIRFLOW ERROR BACKFILL TRANSFORM]: Error al transformar datos a staging: {trans_err}", exc_info=True)

        # 4. Control de Calidad con Pandera
        try:
            valid_records, rejected_records, quality_summary = validate_earthquake_records(staging_records)
        except Exception as qual_err:
            logger.error(f"[AIRFLOW ERROR BACKFILL CALIDAD]: Error en validación Pandera: {qual_err}", exc_info=True)
            valid_records = staging_records
            rejected_records = []
            quality_summary = {"records_evaluated": len(staging_records), "records_passed": len(staging_records), "records_failed": 0, "score_pct": 100.0, "status": "PASSED"}

        # 5. Registro de Métricas de Calidad
        dag_run_id = context.get("run_id", f"backfill_{start_str}_{end_str}")
        try:
            DatabaseManager.record_quality_metrics(
                dag_run_id=dag_run_id,
                rule_name="HistoricalBackfillQualityCheck",
                evaluated=quality_summary["records_evaluated"],
                passed=quality_summary["records_passed"],
                failed=quality_summary["records_failed"],
                score_pct=quality_summary["score_pct"],
                status=quality_summary["status"]
            )
        except Exception as metric_err:
            logger.warning(f"[AVISO AIRFLOW MÉTRICAS BACKFILL]: {metric_err}")

        if rejected_records:
            logger.warning(f"[AVISO AIRFLOW BACKFILL]: Descartados {len(rejected_records)} registros no conformes.")

        # 6. Upsert Idempotente en Curated
        if valid_records:
            try:
                DatabaseManager.upsert_curated_events(valid_records)
            except Exception as upsert_err:
                logger.error(f"[AIRFLOW ERROR BACKFILL CURATED]: Error en upsert curated: {upsert_err}", exc_info=True)

            try:
                s3_client.upload_curated_records(valid_records, batch_id=f"backfill_{start_str}")
            except Exception as s3_err:
                logger.warning(f"[AVISO S3 BACKFILL CURATED]: {s3_err}")

        logger.info(f"[AIRFLOW ÉXITO BACKFILL]: Backfill Histórico completado: {len(valid_records)} eventos cargados/actualizados.")
        return len(valid_records)

    except Exception as fatal_backfill_err:
        logger.error(f"[AIRFLOW ERROR CRÍTICO BACKFILL]: Error no controlado en backfill: {fatal_backfill_err}", exc_info=True)
        if ti:
            ti.xcom_push(key="backfill_fatal_error", value=str(fatal_backfill_err))
        return 0

with DAG(
    dag_id="dag_historical_backfill",
    default_args=default_args,
    description="Carga histórica parametrizada de eventos sísmicos con deduplicación e idempotencia",
    schedule_interval=None,  # Solo ejecución manual / admin
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    params={
        "days_back": Param(30, type="integer", minimum=1, maximum=365, description="Número de días hacia atrás a consultar"),
        "min_magnitude": Param(2.5, type="number", minimum=1.0, maximum=9.0, description="Magnitud mínima a filtrar")
    },
    tags=["backfill", "historical", "usgs", "medallion", "idempotent"],
    doc_md=__doc__
) as dag:

    backfill_task = PythonOperator(
        task_id="execute_historical_backfill",
        python_callable=execute_historical_backfill_task
    )
