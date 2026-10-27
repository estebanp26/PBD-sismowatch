"""
### DAG: Ingesta Periódica USGS Raw (Capa Bronce)
Extrae el feed GeoJSON de última hora de la USGS cada 5 minutos,
almacena el payload inmutable en MinIO S3 y en PostgreSQL (raw.usgs_earthquakes_raw)
de forma idempotente y dispara el pipeline de transformación y calidad.
"""

from datetime import datetime, timedelta
import logging
import sys
import os

# Asegurar que airflow/include esté en el sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from include.config import USGS_REALTIME_URL
from include.clients.usgs_client import USGSClient
from include.clients.s3_client import S3LakeClient
from include.clients.db_client import DatabaseManager
from include.alerts import failure_alert_callback

logger = logging.getLogger(__name__)

default_args = {
    "owner": "sismowatch_data_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=20),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=4),
    "on_failure_callback": failure_alert_callback
}

def extract_and_load_raw_task(**context) -> str:
    """Extrae el feed de USGS y lo persiste en S3 y base de datos raw con try-catch resiliente."""
    ti = context.get("ti")
    try:
        client_usgs = USGSClient(timeout=15, max_retries=3)
        data, payload_hash, event_count = client_usgs.fetch_realtime_feed(USGS_REALTIME_URL)

        # 1. Almacenamiento en Data Lake (MinIO S3) con try-catch
        s3_uri = None
        try:
            s3_client = S3LakeClient()
            s3_uri = s3_client.upload_raw_payload(data, payload_hash)
        except Exception as s3_err:
            logger.warning(f"[AVISO S3 INGESTA]: Error al persistir payload crudo en S3: {s3_err}")

        # 2. Almacenamiento en tabla raw.usgs_earthquakes_raw con try-catch
        raw_id, is_new = None, False
        try:
            raw_id, is_new = DatabaseManager.save_raw_feed(
                source_url=USGS_REALTIME_URL,
                payload_hash=payload_hash,
                raw_payload=data,
                event_count=event_count
            )
        except Exception as db_err:
            logger.error(f"[AIRFLOW ERROR DB RAW]: Error al guardar feed en raw.usgs_earthquakes_raw: {db_err}", exc_info=True)
            if ti:
                ti.xcom_push(key="raw_db_error", value=str(db_err))

        logger.info(f"[AIRFLOW ÉXITO INGESTA]: Ingesta Raw finalizada. S3 URI: {s3_uri}, Raw ID: {raw_id}, Nuevo: {is_new}")
        return payload_hash

    except Exception as fatal_ingest_err:
        err_msg = f"[AIRFLOW ERROR INGESTA USGS]: Fallo crítico al extraer feed del USGS: {fatal_ingest_err}"
        logger.error(err_msg, exc_info=True)
        if ti:
            ti.xcom_push(key="ingest_fatal_error", value=str(fatal_ingest_err))
        return ""

with DAG(
    dag_id="dag_usgs_ingest_raw",
    default_args=default_args,
    description="Ingesta continua del feed GeoJSON de USGS cada 5 minutos",
    schedule_interval="*/5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ingestion", "usgs", "raw", "s3", "medallion"],
    doc_md=__doc__
) as dag:

    ingest_raw_task = PythonOperator(
        task_id="extract_and_load_raw",
        python_callable=extract_and_load_raw_task
    )

    trigger_transform_task = TriggerDagRunOperator(
        task_id="trigger_transform_and_quality",
        trigger_dag_id="dag_transform_and_quality",
        wait_for_completion=False,
        reset_dag_run=True
    )

    ingest_raw_task >> trigger_transform_task
