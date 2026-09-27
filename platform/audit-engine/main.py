"""
Audit & Governance Engine
Persists to PostgreSQL via asyncpg. DSN from POSTGRES_DSN env var.
Retry-until-ready on startup (handles slow PostgreSQL pod start).
"""
import asyncio
import json
import logging
import os

import asyncpg
from fastapi import FastAPI

from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.core.health import register_health_endpoints
from pkg.eventbus.client import EventBusClient

configure_logging("audit-engine")
logger = logging.getLogger("audit-engine")

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://hindsight_user:incident_agent_secret@postgres-db.incident-agent-system.svc.cluster.local:5432/hindsight_db",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis-master.incident-agent-system.svc.cluster.local:6379")

app = FastAPI(title="Audit & Governance Engine")
bootstrap_telemetry(app, "audit-engine", os.getenv("OTEL_ENDPOINT", "http://otel-collector.incident-agent-observability.svc.cluster.local:4317"))
event_bus = EventBusClient(REDIS_URL)
register_health_endpoints(app, "audit-engine")

db_pool = None

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id               SERIAL PRIMARY KEY,
    timestamp        TIMESTAMPTZ DEFAULT NOW(),
    event_type       VARCHAR(100),
    incident_id      VARCHAR(100),
    prompt_id        VARCHAR(100),
    model_name       VARCHAR(100),
    confidence_score FLOAT,
    decision         VARCHAR(255),
    human_approved   BOOLEAN,
    payload          JSONB
);
"""


async def init_db_pool(max_retries: int = 10, delay: float = 3.0):
    global db_pool
    for attempt in range(1, max_retries + 1):
        try:
            db_pool = await asyncpg.create_pool(POSTGRES_DSN, min_size=1, max_size=5)
            async with db_pool.acquire() as conn:
                await conn.execute(CREATE_TABLE_SQL)
            logger.info(f"audit_db_ready attempt={attempt}")
            return
        except Exception as e:
            logger.warning(f"audit_db_connect_failed attempt={attempt}/{max_retries}: {e}")
            if attempt == max_retries:
                logger.error("audit_db_unavailable_giving_up — running without persistence")
                return
            await asyncio.sleep(delay)


async def handle_audit_event(event_type: str, event: dict, message_id: str):
    incident_id = event.get("incident_id", "N/A")
    logger.info(f"Auditing event {event_type} for incident {incident_id}")
    if db_pool is None:
        logger.error("audit_db_not_initialized, dropping event")
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO audit_logs
                   (event_type, incident_id, prompt_id, model_name, confidence_score, decision, human_approved, payload)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
                event_type, incident_id,
                event.get("prompt_id"), event.get("model_name"),
                event.get("confidence_score"), event.get("decision"),
                bool(event.get("human_approved", False)),
                json.dumps(event),
            )
    except Exception as e:
        logger.error(f"Failed to persist audit log: {e}")


@app.on_event("startup")
async def startup_event():
    await init_db_pool()
    asyncio.create_task(
        event_bus.consume(stream="audit_events", group="audit_group", consumer="audit_1", callback=handle_audit_event)
    )
    logger.info("audit_engine_started")


@app.on_event("shutdown")
async def shutdown_event():
    if db_pool:
        await db_pool.close()


@app.get("/api/internal/logs")
async def get_logs(limit: int = 50):
    if db_pool is None:
        return []
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT $1", limit)
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to read audit logs: {e}")
        return []
