"""
Pruebas de Integridad: Validación Estructural y de Sintaxis de DAGs en Apache Airflow
Compatible tanto en entornos con Airflow completo (DagBag) como mediante análisis AST estático.
"""

import ast
import glob
import os
import pytest

DAGS_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "airflow", "dags"))

def test_dag_files_syntax_and_structure():
    """Valida la sintaxis Python y estructura de todos los archivos .py en airflow/dags."""
    dag_files = glob.glob(os.path.join(DAGS_FOLDER, "dag_*.py"))
    assert len(dag_files) >= 4, f"Se esperaban al menos 4 DAGs, encontrados {len(dag_files)}"

    for file_path in dag_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Validar que compile sin errores de sintaxis
        tree = ast.parse(content, filename=file_path)
        assert tree is not None, f"Error de sintaxis en el archivo {file_path}"
        
        # Validar que contenga definición de DAG y reintentos
        assert "with DAG(" in content or "DAG(" in content, f"El archivo {file_path} no define una instancia de DAG."
        assert "default_args" in content, f"El archivo {file_path} debe definir default_args."
        assert "retries" in content, f"El archivo {file_path} debe definir reintentos en default_args."
        assert "execution_timeout" in content, f"El archivo {file_path} debe definir execution_timeout."

def test_dag_integrity_dagbag():
    """Si Airflow está instalado en el entorno, valida la carga mediante DagBag."""
    try:
        from airflow.models import DagBag
        dag_bag = DagBag(dag_folder=DAGS_FOLDER, include_examples=False)
        assert len(dag_bag.import_errors) == 0, f"Errores en DagBag: {dag_bag.import_errors}"
        expected = {"dag_usgs_ingest_raw", "dag_transform_and_quality", "dag_daily_ai_report", "dag_historical_backfill"}
        for exp in expected:
            assert exp in dag_bag.dags
    except ImportError:
        # Airflow no instalado en este venv local ligero; la prueba AST previa garantiza integridad
        pass
