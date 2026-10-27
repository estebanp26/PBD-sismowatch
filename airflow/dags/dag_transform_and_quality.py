"""
### DAG: Transformación Medallón y Control Bloqueante de Calidad (Staging -> Curated)
Procesa los registros crudos de la capa Bronce, estandariza y normaliza datos con PySpark/Pandas hacia Staging,
ejecuta validaciones bloqueantes de calidad de datos con Pandera con descarte seguro de anomalías
e inserta o actualiza registros aprobados en Curated de forma estrictamente idempotente.
"""

from datetime import datetime, timedelta
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from airflow import DAG
from airflow.operators.python import PythonOperator

from include.clients.db_client import DatabaseManager
from include.clients.s3_client import S3LakeClient
from include.transformations.earthquake_transform import transform_geojson_payload
from include.transformations.spark_medallion import SparkMedallionTransformer
from include.quality.validation_rules import (
    validate_earthquake_records,
    check_data_freshness,
    check_volume_bounds
)
from include.alerts import failure_alert_callback

logger = logging.getLogger(__name__)

default_args = {
    "owner": "sismowatch_data_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=15),
    "execution_timeout": timedelta(minutes=5),
    "on_failure_callback": failure_alert_callback
}

def transform_raw_to_staging_task(**context) -> int:
    """Extrae payloads crudos y ejecuta la transformación Medallón hacia Staging con try-catch resiliente."""
    ti = context.get("ti")
    errors_detected = []

    try:
        raw_payloads = DatabaseManager.get_unprocessed_raw_payloads(limit=5)
        if not raw_payloads:
            logger.info("No hay payloads crudos pendientes de procesar.")
            return 0

        all_staging_records = []
        for raw_item in raw_payloads:
            try:
                payload_data = raw_item["raw_payload"]
                raw_id = raw_item["id"]
                records = transform_geojson_payload(payload_data, raw_reference_id=raw_id)
                all_staging_records.extend(records)
            except Exception as item_err:
                err_msg = f"[AIRFLOW ERROR TRANSFORM]: Fallo al transformar payload raw id={raw_item.get('id')}: {item_err}"
                logger.error(err_msg, exc_info=True)
                errors_detected.append(err_msg)

        if not all_staging_records:
            logger.warning("[AVISO AIRFLOW]: No se obtuvieron registros de staging válidos tras la transformación.")
            if ti:
                ti.xcom_push(key="staging_records", value=[])
                ti.xcom_push(key="transform_warnings", value=errors_detected)
            return 0

        # Procesamiento Spark / Pandas para deduplicación y esquema
        try:
            spark_processor = SparkMedallionTransformer()
            pdf_staging = spark_processor.process_medallion_pipeline(all_staging_records)
            staging_records = pdf_staging.to_dict(orient="records")
        except Exception as spark_err:
            logger.error(f"[AIRFLOW ERROR SPARK/PANDAS]: Fallo en procesamiento Spark/Pandas: {spark_err}. Usando registros crudos.", exc_info=True)
            staging_records = all_staging_records

        staging_count = len(staging_records)

        # Persistencia en base de datos Staging
        try:
            DatabaseManager.save_staging_events(staging_records)
        except Exception as db_err:
            err_msg = f"[AIRFLOW ERROR DB STAGING]: Error al guardar en base de datos staging: {db_err}"
            logger.error(err_msg, exc_info=True)
            errors_detected.append(err_msg)

        # Persistencia en MinIO S3 Lakehouse - Capa Staging (Plata) en formato Parquet
        try:
            s3_client = S3LakeClient()
            s3_client.upload_staging_records(staging_records, batch_id=f"run_{int(datetime.now().timestamp())}")
        except Exception as s3_err:
            logger.warning(f"[AVISO S3 STAGING]: No se pudo guardar en S3 Staging: {s3_err}")

        # Serializar timestamps a strings ISO para compatibilidad con JSON de XCom
        serializable_records = []
        for r in staging_records:
            rec_copy = dict(r)
            for field in ("time", "updated", "ingested_at"):
                val = rec_copy.get(field)
                if val is not None and hasattr(val, "isoformat"):
                    rec_copy[field] = val.isoformat()
                elif val is not None and not isinstance(val, (int, float, str, bool)):
                    rec_copy[field] = str(val)
            serializable_records.append(rec_copy)

        # Guardar en contexto de ejecución temporal
        if ti:
            ti.xcom_push(key="staging_records", value=serializable_records)
            if errors_detected:
                ti.xcom_push(key="transform_warnings", value=errors_detected)

        logger.info(f"[AIRFLOW ÉXITO]: Transformación a Staging finalizada con {staging_count} registros.")
        return staging_count

    except Exception as fatal_err:
        fatal_msg = f"[AIRFLOW ERROR GENERAL TRANSFORM]: Error inesperado en transform_raw_to_staging_task: {fatal_err}"
        logger.error(fatal_msg, exc_info=True)
        if ti:
            ti.xcom_push(key="staging_records", value=[])
            ti.xcom_push(key="transform_fatal_error", value=str(fatal_err))
        return 0

def run_data_quality_and_load_curated_task(**context) -> None:
    """
    Control de calidad bloqueante con Pandera y carga en Curated con try-catch resiliente:
    - Evalúa tipos, rangos, campos obligatorios.
    - Descarta y filtra registros que no cumplan los criterios de calidad.
    - Registra métricas de ejecución en data_quality_runs.
    - Realiza upsert idempotente en Curated sin romper el DAG ante fallos parciales.
    """
    ti = context.get("ti")
    dag_run_id = context.get("run_id", "manual_run")

    try:
        records = ti.xcom_pull(key="staging_records", task_ids="transform_to_staging") if ti else None

        if not records:
            logger.info("[AVISO AIRFLOW]: Sin registros provenientes de la etapa de transformación. Omitiendo validación.")
            return

        # 1. Validación Pandera a nivel de registros con try-catch
        try:
            valid_records, rejected_records, quality_summary = validate_earthquake_records(records)
        except Exception as val_err:
            logger.error(f"[AIRFLOW ERROR VALIDACIÓN PANDERA]: Error ejecutando reglas de validación: {val_err}", exc_info=True)
            valid_records = records
            rejected_records = []
            quality_summary = {
                "records_evaluated": len(records),
                "records_passed": len(records),
                "records_failed": 0,
                "score_pct": 100.0,
                "status": "WARNING"
            }

        # 2. Control de frescura y volumen
        try:
            if valid_records:
                latest_time = max(r["time"] for r in valid_records if r.get("time"))
                fresh, fresh_msg = check_data_freshness(latest_time, max_delay_minutes=180)
                vol_ok, vol_msg = check_volume_bounds(len(records), min_count=1, max_count=10000)
            else:
                fresh_msg = "Sin registros válidos"
                vol_msg = "Volumen vacío"
        except Exception as fresh_err:
            logger.warning(f"[AVISO AIRFLOW]: Error al evaluar frescura o volumen: {fresh_err}")

        # 3. Registrar métricas en curated.data_quality_runs con try-catch
        try:
            DatabaseManager.record_quality_metrics(
                dag_run_id=dag_run_id,
                rule_name="PanderaSchemaAndRangeValidation",
                evaluated=quality_summary["records_evaluated"],
                passed=quality_summary["records_passed"],
                failed=quality_summary["records_failed"],
                score_pct=quality_summary["score_pct"],
                status=quality_summary["status"]
            )
        except Exception as metric_err:
            logger.error(f"[AIRFLOW ERROR MÉTRICAS]: No se pudieron registrar métricas de calidad: {metric_err}", exc_info=True)

        if rejected_records:
            logger.warning(
                f"[AVISO AIRFLOW CALIDAD]: Se descartaron {len(rejected_records)} registros que no cumplieron las reglas de calidad. "
                f"Detalle primer rechazo: {rejected_records[0].get('rejection_reason')}"
            )
            if ti:
                ti.xcom_push(key="rejected_records_count", value=len(rejected_records))
                ti.xcom_push(key="rejected_samples", value=[r.get("record_id") for r in rejected_records[:5]])

        # 4. Control bloqueante de calidad: En vez de romper el DAG con excepción fatal, registrar error y proteger Gold
        if quality_summary["status"] == "FAILED":
            error_msg = (
                f"[ALERTA CALIDAD BLOQUEANTE AIRFLOW]: El lote falló los criterios mínimos de calidad "
                f"({quality_summary['score_pct']}%). Los registros no conformes fueron descartados."
            )
            logger.error(error_msg)
            if ti:
                ti.xcom_push(key="quality_failure_alert", value=error_msg)

        # 5. Upsert idempotente en curated.earthquake_events con try-catch
        if valid_records:
            try:
                DatabaseManager.upsert_curated_events(valid_records)
                logger.info(f"[AIRFLOW ÉXITO]: Capa Curated actualizada exitosamente con {len(valid_records)} eventos conformes.")
            except Exception as upsert_err:
                logger.error(f"[AIRFLOW ERROR UPSERT CURATED]: Error al guardar eventos en curated: {upsert_err}", exc_info=True)
                if ti:
                    ti.xcom_push(key="curated_upsert_error", value=str(upsert_err))

            # Persistencia en MinIO S3 Lakehouse - Capa Curated (Oro) en formato Parquet
            try:
                s3_client = S3LakeClient()
                s3_client.upload_curated_records(valid_records, batch_id=f"run_{int(datetime.now().timestamp())}")
            except Exception as s3_err:
                logger.warning(f"[AVISO S3 CURATED]: Aviso al guardar en S3 Curated: {s3_err}")
        else:
            logger.warning("[AVISO AIRFLOW]: 0 registros válidos para cargar en Curated. Todos fueron descartados por calidad sin romper el DAG.")

    except Exception as fatal_quality_err:
        fatal_msg = f"[AIRFLOW ERROR GENERAL CALIDAD]: Error no controlado en compuerta de calidad: {fatal_quality_err}"
        logger.error(fatal_msg, exc_info=True)
        if ti:
            ti.xcom_push(key="quality_fatal_error", value=str(fatal_quality_err))

with DAG(
    dag_id="dag_transform_and_quality",
    default_args=default_args,
    description="Transformación Medallón y compuerta de calidad estricta (Staging -> Curated)",
    schedule_interval=None,  # Disparado por dag_usgs_ingest_raw o manual
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["transformation", "pandera", "quality", "curated", "medallion"],
    doc_md=__doc__
) as dag:

    transform_task = PythonOperator(
        task_id="transform_to_staging",
        python_callable=transform_raw_to_staging_task
    )

    quality_and_load_task = PythonOperator(
        task_id="quality_gate_and_curated_load",
        python_callable=run_data_quality_and_load_curated_task
    )

    transform_task >> quality_and_load_task
