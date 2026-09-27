import asyncio
import time
from fastapi import FastAPI
from pydantic import BaseModel
from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("incident-engine")
app = FastAPI(title="Incident Engine", version="1.0.0")

bootstrap_telemetry(app, "incident-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "incident-engine")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")

# Store active incidents. Key: incident_id, Value: incident dict
active_incidents = {}

@app.get("/incidents/active")
async def get_active_incidents():
    """Endpoint required by dashboard-bff to show active incidents in UI."""
    return {"incidents": list(active_incidents.values())}

async def manage_incident(event_type: str, payload: dict, message_id: str):
    if event_type == "BLAST_RADIUS_MAPPED":
        root_cause = payload.get("root_cause_candidate")

        # Suppress duplicates if service already has an active investigating incident
        if any(inc.get("root_cause") == root_cause and inc.get("status") == "investigating" for inc in active_incidents.values()):
            logger.debug("duplicate_incident_suppressed", root=root_cause)
            return

        incident_id = f"INC-{len(active_incidents) + 1000}-{str(int(time.time()))[-4:]}"
        
        incident_data = {
            "id": incident_id,
            "description": f"Anomalous behavior detected in {root_cause}",
            "status": "investigating",
            "severity": "high",
            "root_cause": root_cause,
            "impacted_services": payload.get("impacted_services", []),
            "timestamp": time.time()
        }
        
        active_incidents[incident_id] = incident_data

        logger.critical(
            "incident_created",
            incident_id=incident_id,
            root_cause=root_cause,
            severity="SEV-1",
        )

        await event_bus.publish(
            "ai_stream",
            "INCIDENT_DECLARED",
            {
                "incident_id": incident_id,
                "root_cause_candidate": root_cause,
                "impacted_services": incident_data["impacted_services"],
                "status": "investigating",
            },
        )
        
    elif event_type == "RECOVERY_COMPLETED":
        incident_id = payload.get("incident_id")
        if incident_id in active_incidents:
            logger.info("incident_resolved", incident_id=incident_id)
            active_incidents[incident_id]["status"] = "resolved"

async def run_consumer():
    await event_bus.connect()
    # Listen to both incident_stream (for creation) and recovery_stream (for resolution)
    await event_bus.consume(
        "incident_stream", "incident_group", "inc_1", manage_incident
    )
    
async def run_recovery_consumer():
    await event_bus.connect()
    await event_bus.consume(
        "recovery_stream", "incident_recovery_group", "inc_rec_1", manage_incident
    )

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())
    asyncio.create_task(run_recovery_consumer())
    logger.info("Incident Engine started")
