"""
SismoWatch - Manejador de Alertas de Fallos (on_failure_callback)
Registro estructurado y notificación ante anomalías de ejecución en Airflow.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def failure_alert_callback(context: Dict[str, Any]) -> None:
    """
    Callback ejecutado automáticamente cuando una tarea de Airflow falla.
    Extrae contexto, DAG, tarea, tiempo de ejecución y excepción para trazabilidad.
    """
    dag_id = context.get("dag", "UNKNOWN_DAG")
    task_id = context.get("task_instance", {}).task_id if context.get("task_instance") else "UNKNOWN_TASK"
    execution_date = context.get("execution_date", "N/A")
    exception = context.get("exception", "No exception detail")

    alert_message = (
        f"🚨 [ALERTA SISMO-WATCH] Fallo en Pipeline de Monitoreo Sísmico\n"
        f"DAG: {dag_id}\n"
        f"Tarea: {task_id}\n"
        f"Fecha de Ejecución: {execution_date}\n"
        f"Causa raíz: {exception}\n"
        f"Acción recomendada: Verificar logs del contenedor Airflow y estado de conectividad."
    )

    logger.critical(alert_message)
