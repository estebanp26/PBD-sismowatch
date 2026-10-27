"""
SismoWatch - Cliente S3 / MinIO
Almacenamiento de objetos para la Capa Raw (Bronce) y artefactos del Lago de Datos (Lakehouse).
"""

from datetime import datetime, timezone
import io
import json
import logging
from typing import Any, Dict, List, Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import pandas as pd

from include.config import (
    S3_ENDPOINT_URL,
    S3_BUCKET_NAME,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_DEFAULT_REGION
)

logger = logging.getLogger(__name__)

class S3LakeClient:
    """Cliente para interactuar con MinIO o AWS S3 asegurando las 3 capas Medallón en el Lakehouse."""

    def __init__(
        self,
        endpoint_url: str = S3_ENDPOINT_URL,
        bucket_name: str = S3_BUCKET_NAME,
        access_key: str = AWS_ACCESS_KEY_ID,
        secret_key: str = AWS_SECRET_ACCESS_KEY,
        region_name: str = AWS_DEFAULT_REGION
    ):
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(signature_version="s3v4")
        )
        self.ensure_bucket_exists()

    def ensure_bucket_exists(self) -> None:
        """Verifica que el bucket exista en MinIO; si no, lo crea de forma transparente."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchBucket"):
                logger.info(f"Creando bucket S3: {self.bucket_name}")
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                except Exception as create_err:
                    logger.warning(f"Aviso al crear bucket: {create_err}")
            else:
                logger.warning(f"Aviso al verificar bucket S3 ({self.bucket_name}): {e}")

    def upload_raw_payload(self, payload: Dict[str, Any], payload_hash: str) -> str:
        """
        1. Capa Raw (Bronce): Guarda el GeoJSON tal como llegó en el Data Lake particionado temporalmente:
        s3://sismowatch-lake/raw/YYYY/MM/DD/usgs_feed_<hash>.geojson
        """
        now = datetime.now(timezone.utc)
        s3_key = f"raw/{now.year:04d}/{now.month:02d}/{now.day:02d}/usgs_feed_{payload_hash[:16]}.geojson"
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=payload_bytes,
                ContentType="application/geo+json",
                Metadata={
                    "payload_hash": payload_hash,
                    "ingested_at": now.isoformat(),
                    "source": "USGS Earthquake Catalog",
                    "layer": "bronze_raw"
                }
            )
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Capa Raw (Bronce) guardada en S3: {s3_uri}")
            return s3_uri
        except Exception as e:
            logger.error(f"Error subiendo raw payload a S3 ({s3_key}): {e}")
            raise

    def upload_staging_records(self, records: List[Dict[str, Any]], batch_id: Optional[str] = None) -> str:
        """
        2. Capa Staging (Plata): Guarda eventos limpios, aplanados y tipados en formato columnar Parquet:
        s3://sismowatch-lake/staging/YYYY/MM/DD/staging_events_<batch_id>.parquet
        """
        if not records:
            return ""

        now = datetime.now(timezone.utc)
        batch = (batch_id or f"{int(now.timestamp())}")[:16]
        s3_key = f"staging/{now.year:04d}/{now.month:02d}/{now.day:02d}/staging_events_{batch}.parquet"

        try:
            df = pd.DataFrame(records)
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
            parquet_bytes = parquet_buffer.getvalue()

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=parquet_bytes,
                ContentType="application/vnd.apache.parquet",
                Metadata={
                    "record_count": str(len(records)),
                    "processed_at": now.isoformat(),
                    "layer": "silver_staging"
                }
            )
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Capa Staging (Plata) guardada en S3: {s3_uri} ({len(records)} filas en Parquet)")
            return s3_uri
        except Exception as e:
            logger.error(f"Error subiendo staging Parquet a S3 ({s3_key}): {e}")
            raise

    def upload_curated_records(self, records: List[Dict[str, Any]], batch_id: Optional[str] = None) -> str:
        """
        3. Capa Curated (Oro): Guarda eventos validados y conformes en formato columnar Parquet:
        s3://sismowatch-lake/curated/YYYY/MM/DD/curated_events_<batch_id>.parquet
        """
        if not records:
            return ""

        now = datetime.now(timezone.utc)
        batch = (batch_id or f"{int(now.timestamp())}")[:16]
        s3_key = f"curated/{now.year:04d}/{now.month:02d}/{now.day:02d}/curated_events_{batch}.parquet"

        try:
            df = pd.DataFrame(records)
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
            parquet_bytes = parquet_buffer.getvalue()

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=parquet_bytes,
                ContentType="application/vnd.apache.parquet",
                Metadata={
                    "record_count": str(len(records)),
                    "quality_validated": "true",
                    "processed_at": now.isoformat(),
                    "layer": "gold_curated"
                }
            )
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Capa Curated (Oro) guardada en S3: {s3_uri} ({len(records)} eventos conformes en Parquet)")
            return s3_uri
        except Exception as e:
            logger.error(f"Error subiendo curated Parquet a S3 ({s3_key}): {e}")
            raise

    def upload_curated_report(self, report_data: Dict[str, Any], report_id: str) -> str:
        """
        3b. Capa Curated (Oro): Guarda reportes ejecutivos narrativos generados por IA en S3:
        s3://sismowatch-lake/curated/reports/YYYY/MM/ai_report_<report_id>.json
        """
        now = datetime.now(timezone.utc)
        s3_key = f"curated/reports/{now.year:04d}/{now.month:02d}/ai_report_{report_id}.json"
        report_bytes = json.dumps(report_data, ensure_ascii=False, indent=2, default=str).encode("utf-8")

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=report_bytes,
                ContentType="application/json",
                Metadata={
                    "report_id": str(report_id),
                    "created_at": now.isoformat(),
                    "layer": "gold_curated_reports"
                }
            )
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Reporte Ejecutivo de IA (Oro) guardado en S3: {s3_uri}")
            return s3_uri
        except Exception as e:
            logger.error(f"Error subiendo reporte IA a S3 ({s3_key}): {e}")
            raise
