# Pandera & Calidad de Datos — Compuerta Bloqueante y Política de Cero Cuarentena

## 1. ¿Qué es Pandera y por qué se eligió para SismoWatch?
**Pandera** es un framework de validación estadística y de esquemas de datos declarativo y fuertemente tipado para Python (diseñado para trabajar de forma nativa con DataFrames de **Pandas** y **PySpark**).

### Justificación Técnica frente a otras herramientas:
En el diseño de la arquitectura se evaluaron herramientas como *Great Expectations*, *Soda Core* y validaciones mediante restricciones SQL (*CHECK constraints*):
- **Great Expectations:** Aunque es potente, introduce una sobrecarga considerable de memoria, configuración pesada de suites en JSON y dependencias complejas dentro de los contenedores de Airflow.
- **Validaciones en SQL puro:** Ocurren a nivel de base de datos una vez que los datos ya fueron transferidos, lo que incrementa el tráfico de red y dificulta la obtención de diagnósticos detallados a nivel de fila y columna.
- **Por qué Pandera es la mejor opción:**
  - Se ejecuta directamente en la memoria de los procesos Python/PySpark durante la fase de transformación.
  - Proporciona diagnósticos de fallo a nivel de registro (`Check.check_range`, `Check.str_length`, etc.).
  - Es extremadamente liviano, rápido y no requiere servicios adicionales ni conexiones a nubes externas.

---

## 2. El Principio de "Cero Cuarentena" (Zero Quarantine)

Una de las decisiones arquitectónicas centrales de SismoWatch es la **eliminación total de tablas o esquemas de cuarentena**:

### ¿Por qué NO usamos cuarentena?
1. **Evita la deuda técnica y la acumulación de datos zombi:** En la industria, las tablas de cuarentena suelen convertirse en basureros de datos que nadie limpia ni monitorea, consumiendo espacio y generando confusión sobre qué es confiable y qué no.
2. **Protección absoluta de la Capa Gold:** Ningún dato no conforme bajo ninguna circunstancia ingresa a `curated.earthquake_events`.
3. **Descarte Inmediato con Auditoría Transparente:** Los registros inválidos son rechazados de inmediato. El motivo específico del rechazo (ej. latitud errónea, magnitud fuera de rango) se guarda en la tabla de auditoría `curated.data_quality_runs` con su correspondiente métrica para evaluación de calidad en el dashboard.
4. **Resiliencia Operativa (El DAG no se rompe):** Si un lote presenta una tasa de fallo alta (score $< 70\%$), los registros corruptos son descartados, se emite una alerta `logger.error` y se almacena en XCom en Airflow para conocimiento del operador, pero el DAG **continúa su ejecución de forma segura** protegiendo la integridad de la capa Gold sin detener los ciclos posteriores.

---

## 3. Reglas Formales de Calidad Validadas por Pandera

La compuerta de calidad de Pandera se ejecuta en la tarea `validate_quality_gate` del DAG `dag_transform_and_quality`. Aplica las siguientes reglas deterministas:

| Regla | Parámetro Validado | Condición Aceptable | Acción en Fallo |
|---|---|---|---|
| **R1: Integridad de ID** | `id` | Cadena no vacía, tipo string, longitud $> 2$ caracteres | Rechazo del registro individual |
| **R2: Límite de Latitud** | `latitude` | Flotante en el rango $[-90.0, 90.0]$ | Rechazo del registro individual |
| **R3: Límite de Longitud** | `longitude` | Flotante en el rango $[-180.0, 180.0]$ | Rechazo del registro individual |
| **R4: Profundidad Hipocentral** | `depth` | Flotante en el rango $[-10.0, 1000.0]$ km | Rechazo del registro individual |
| **R5: Magnitud Física Plausible** | `magnitude` | Flotante en el rango $[-2.0, 10.0]$ | Rechazo del registro individual |
| **R6: Frescura Temporal** | `time` | Fecha válida en UTC, nunca superior al tiempo actual $+ 5\text{ min}$ | Rechazo del registro individual |
| **R7: Alerta de Tsunami** | `tsunami` | Entero binario $\in \{0, 1\}$ o booleano estricto | Rechazo del registro individual |
| **R8: Estado del Evento** | `status` | Pertenencia al conjunto `{'automatic', 'reviewed'}` | Imputación controlada a 'automatic' |

---

## 4. Definición del Esquema Pandera en Código Python

El esquema está implementado en [`airflow/include/quality/quality_gate.py`](file:///home/cohorte5/Escritorio/PBD-sismowatch/airflow/include/quality/quality_gate.py) utilizando el formato declarativo de Pandera:

```python
import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

earthquake_quality_schema = DataFrameSchema(
    columns={
        "id": Column(str, Check.str_length(min_value=3), nullable=False),
        "latitude": Column(float, Check.in_range(-90.0, 90.0), nullable=False),
        "longitude": Column(float, Check.in_range(-180.0, 180.0), nullable=False),
        "depth": Column(float, Check.in_range(-10.0, 1000.0), nullable=False),
        "magnitude": Column(float, Check.in_range(-2.0, 10.0), nullable=False),
        "tsunami": Column(int, Check.isin([0, 1]), nullable=False),
        "time": Column(pa.DateTime, nullable=False),
    },
    coerce=True,
    strict=False  # Permite columnas complementarias sin descartar el DataFrame
)
```

---

## 5. Auditoría de Calidad en la Base de Datos

Cada vez que se ejecuta el pipeline, los resultados de la validación se registran en la tabla `curated.data_quality_runs`:

```sql
CREATE TABLE IF NOT EXISTS curated.data_quality_runs (
    id SERIAL PRIMARY KEY,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dag_run_id VARCHAR(100),
    total_evaluated INT NOT NULL,
    total_passed INT NOT NULL,
    total_rejected INT NOT NULL,
    pass_rate_percentage NUMERIC(5, 2) NOT NULL,
    rejection_details JSONB,
    freshness_lag_seconds INT
);
```

### Ejemplo de Consulta para Verificar la Salud de los Datos:
```sql
SELECT 
    executed_at,
    total_evaluated,
    total_passed,
    total_rejected,
    pass_rate_percentage || '%' AS tasa_aprobacion,
    rejection_details
FROM curated.data_quality_runs
ORDER BY executed_at DESC
LIMIT 5;
```

Si la tasa de aprobación cae por debajo del **95%**, la API emite una advertencia en el endpoint `/api/kpis` y el dashboard web resalta el estado del pipeline en color ámbar.
