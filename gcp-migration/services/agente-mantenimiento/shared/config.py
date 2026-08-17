"""
config — Configuración centralizada para todos los servicios GCP.

Lee de variables de entorno con defaults para desarrollo local.
"""

import os


class Config:
    """Configuración del proyecto ADO MobilityIA en GCP."""

    # GCP Project
    PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "ado-mobilityia")
    REGION = os.environ.get("GCP_REGION", "us-central1")

    # Cloud Storage
    GCS_BUCKET = os.environ.get("GCS_BUCKET", "proy-ado-telemetria-dev-data-v1")
    GCS_PREFIX = os.environ.get("GCS_PREFIX", "aws_bl_hackathon")
    GCS_CATALOGO_KEY = os.environ.get("GCS_CATALOGO_KEY", "aws_bl_hackathon/hackathon-data/catalogo/motor_spn.json")
    GCS_VIAJES_KEY = os.environ.get("GCS_VIAJES_KEY", "aws_bl_hackathon/hackathon-data/simulacion/viajes_consolidados.json")
    GCS_FALLAS_KEY = os.environ.get("GCS_FALLAS_KEY", "aws_bl_hackathon/hackathon-data/fallas-simuladas/data_fault.json")
    GCS_EMBEDDINGS_KEY = os.environ.get("GCS_EMBEDDINGS_KEY", "aws_bl_hackathon/knowledge-base/faiss_index.bin")
    GCS_KB_TEXTS_KEY = os.environ.get("GCS_KB_TEXTS_KEY", "aws_bl_hackathon/knowledge-base/documents.json")

    # Firestore
    FIRESTORE_COLLECTION_TELEMETRIA = os.environ.get("FIRESTORE_TELEMETRIA", "telemetria-live")
    FIRESTORE_COLLECTION_ALERTAS = os.environ.get("FIRESTORE_ALERTAS", "alertas")

    # Gemini / Vertex AI
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-002")
    GEMINI_LOCATION = os.environ.get("GEMINI_LOCATION", "us-central1")

    # Cloud Run service URLs (se configuran post-deploy)
    AGENTE_COMBUSTIBLE_URL = os.environ.get("AGENTE_COMBUSTIBLE_URL", "http://localhost:8081")
    AGENTE_MANTENIMIENTO_URL = os.environ.get("AGENTE_MANTENIMIENTO_URL", "http://localhost:8082")

    # Simulador
    BURST_COUNT = int(os.environ.get("BURST_COUNT", "6"))
    TICK_INTERVAL = int(os.environ.get("TICK_INTERVAL", "10"))
    STEP_SECONDS = int(os.environ.get("STEP_SECONDS", "10"))

    # Frontend (Firebase)
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,https://ado-mobilityia.web.app"
    ).split(",")


config = Config()
