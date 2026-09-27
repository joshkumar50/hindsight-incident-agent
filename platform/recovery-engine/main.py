"""
Recovery Engine — stub that bridges execution-engine to recovery sub-services.
Consumes recovery_stream for RECOVERY_PLAN_READY events and fans out to
recovery-planning-engine. This keeps the topology diagram accurate.
"""
import asyncio
import os
from fastapi import FastAPI
from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient
import httpx

config = get_config()
logger = configure_logging("recovery-engine")
app = FastAPI(title="Recovery Engine", version="1.0.0")

bootstrap_telemetry(app, "recovery-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "recovery-engine")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")

async def handle_recovery(event_type: str, payload: dict, message_id: str):
    if event_type == "RECOVERY_PLAN_READY":
        incident_id = payload.get("incident_id")
        logger.info("recovery_engine_dispatching", incident_id=incident_id)
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                await client.post(
                    "http://recovery-planning-engine.incident-agent-system.svc.cluster.local/plan",
                    json=payload,
                )
                logger.info("recovery_engine_dispatched_to_planner", incident_id=incident_id)
            except Exception as e:
                logger.error("recovery_engine_dispatch_failed", error=str(e))

async def run_consumer():
    await event_bus.connect()
    await event_bus.consume("recovery_stream", "recovery_engine_group", "recovery_1", handle_recovery)

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())
    logger.info("Recovery Engine started")
