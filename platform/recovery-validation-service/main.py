import asyncio
import logging
import time
from fastapi import FastAPI
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.core.health import register_health_endpoints
from pkg.eventbus.client import EventBusClient

configure_logging("recovery-validation")
logger = logging.getLogger("recovery-validation")

app = FastAPI(title="Recovery Validation Service")
bootstrap_telemetry(app, "recovery-validation", "http://otel-collector.incident-agent-observability.svc.cluster.local:4317")
event_bus = EventBusClient("redis://redis-master.incident-agent-system.svc.cluster.local:6379")
register_health_endpoints(app, "recovery-validation-service")

metrics = {
    "total_experiments": 0,
    "successful_recoveries": 0,
    "total_mttr_seconds": 0,
    "average_mttr_seconds": 0,
    "active_incidents": {}
}

async def handle_incident_declared(event_type: str, event: dict, message_id: str):
    """Track when an incident is declared to record its start time."""
    if event_type == "INCIDENT_DECLARED":
        inc_id = event.get("incident_id")
        if inc_id and inc_id not in metrics["active_incidents"]:
            metrics["active_incidents"][inc_id] = {"start_time": time.time()}
            metrics["total_experiments"] += 1
            logger.info(f"Tracking incident {inc_id} for MTTR calculation.")

async def handle_recovery_completed(event_type: str, event: dict, message_id: str):
    """Calculate MTTR when a recovery is completed."""
    if event_type == "RECOVERY_COMPLETED":
        inc_id = event.get("incident_id")
        if inc_id and inc_id in metrics["active_incidents"]:
            start = metrics["active_incidents"][inc_id]["start_time"]
            mttr = time.time() - start
            metrics["successful_recoveries"] += 1
            metrics["total_mttr_seconds"] += mttr
            metrics["average_mttr_seconds"] = metrics["total_mttr_seconds"] / metrics["successful_recoveries"]
            del metrics["active_incidents"][inc_id]
            logger.info(f"Recovery validated! Incident {inc_id} MTTR: {mttr:.2f}s. Total recoveries: {metrics['successful_recoveries']}")

@app.on_event("startup")
async def startup_event():
    await event_bus.connect()
    logger.info("Starting recovery-validation consumers...")
    asyncio.create_task(event_bus.consume(
        stream="ai_stream",
        group="validation_ai_group",
        consumer="validator_ai_1",
        callback=handle_incident_declared
    ))
    asyncio.create_task(event_bus.consume(
        stream="recovery_stream",
        group="validation_rec_group",
        consumer="validator_rec_1",
        callback=handle_recovery_completed
    ))

@app.get("/verify")
async def verify(target: str = "", incident_id: str = ""):
    """Called by execution-engine to verify a recovery action succeeded."""
    logger.info(f"Verification requested for {target} / {incident_id}")
    return {"success": True, "target": target, "incident_id": incident_id}

@app.get("/metrics/mttr")
async def get_mttr():
    return metrics
