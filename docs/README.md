# Índice de Documentación Técnica — SismoWatch

Bienvenido a la documentación oficial y completa de la plataforma **SismoWatch**.

A continuación, encontrarás el índice organizado de todos los manuales técnicos, guías operativas, especificaciones de arquitectura y guías de despliegue diseñadas tanto para desarrolladores e ingenieros de datos como para operadores del sistema.

---

## 📚 1. Visión General e Instalación

- 🌐 **[00. Documentación General del Sistema y Arquitectura Medallón](00_SISTEMA_GENERAL.md)**  
  *Explicación integral del programa, flujo de datos end-to-end, decisiones técnicas, cuadro maestro de credenciales y buenas prácticas de ingeniería.*

- 🚀 **[01. Guía de Instalación y Despliegue desde Cero](01_GUIA_INSTALACION_DESDE_CERO.md)**  
  *Procedimiento paso a paso para clonar, configurar variables de entorno, levantar Docker Compose y verificar el sistema en un equipo o servidor nuevo.*

- 🏗️ **[Análisis Formal de Arquitectura y Compensaciones](ARQUITECTURA.md)**  
  *Justificación teórica de trade-offs, escalabilidad, decisiones de base de datos y patrones de resiliencia.*

---

## 🛠️ 2. Documentación Especializada por Tecnología

Cada tecnología cuenta con su propio manual independiente que detalla su funcionamiento, puertos, usuarios, contraseñas, volúmenes de Docker Desktop y comandos operativos:

| Documento | Tecnología | Propósito en SismoWatch |
|---|---|---|
| 🪣 **[01. MinIO Object Storage](tecnologias/01_MINIO.md)** | MinIO (API S3) | Data Lakehouse Bronze inmutable (`sismowatch-lake/raw/`). Usuarios, claves, consola web y particionamiento. |
| 🌪️ **[02. Apache Airflow](tecnologias/02_AIRFLOW.md)** | Apache Airflow 2.9 | Orquestador de DAGs (LocalExecutor). Ingesta cada 5 min, transformación Silver/Gold y reportes diarios. |
| 🐘 **[03. PostgreSQL](tecnologias/03_POSTGRESQL.md)** | PostgreSQL 16 | Almacén relacional Medallón (`raw`, `staging`, `curated`). Modelo de 4 roles RBAC y política de Cero Cuarentena. |
| ⚡ **[04. FastAPI Backend](tecnologias/04_FASTAPI.md)** | FastAPI | API REST gobernada (rol `sismo_app`), seguridad JWT, streaming SSE en tiempo real y catálogo de endpoints. |
| ⚛️ **[05. Plataforma Web React](tecnologias/05_REACT_FRONTEND.md)** | React + Vite + Tailwind | Interfaz analítica, mapas Leaflet, feed reactivo, asistente IA conversacional y visualización de linaje. |
| 🛡️ **[06. Pandera y Calidad de Datos](tecnologias/06_PANDERA_CALIDAD.md)** | Pandera Framework | Compuerta bloqueante, reglas físicas y geográficas, descarte inmediato y auditoría en `data_quality_runs`. |
| 🦙 **[07. Ollama e Inteligencia Artificial](tecnologias/07_OLLAMA_IA.md)** | Ollama (Llama 3 / Qwen) | Reportes ejecutivos con detección Z-score y Chatbot interactivo con enrutador ultrarrápido (< 10 ms). |
| 🔍 **[08. OpenMetadata y Linaje de Datos](tecnologias/08_OPENMETADATA_LINAJE.md)** | OpenMetadata 1.3 | Catálogo de activos, especificación formal JSON de 12 nodos, topología de datos y volúmenes Docker Desktop. |

---

## 📊 3. Especificaciones y Artefactos

- 📄 **[Especificación JSON de Linaje de Datos (OpenMetadata Spec 1.3)](openmetadata/pipeline_metadata.json)**  
  *Definición completa en formato estándar JSON de los nodos, capas y relaciones del pipeline.*
