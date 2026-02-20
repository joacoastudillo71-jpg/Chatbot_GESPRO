from fastapi import APIRouter
from pydantic import BaseModel
import logging
import psycopg
from src.config.settings import settings

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "0.0.1"

logger = logging.getLogger("voice_health")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    db_status = "unknown"

    try:
        # Intentamos conexión directa a Postgres
        with psycopg.connect(settings.db_connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return HealthResponse(status="ok", database=db_status)
