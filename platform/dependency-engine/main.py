import asyncio

from fastapi import FastAPI

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("dependency-engine")
app = FastAPI(title="Dependency Engine", version="1.0.0")

bootstrap_telemetry(app, "dependency-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "dependency-engine")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")

# Hardcoded topology for Phase 4. Phase 7 could use Kube API for dynamic mapping.
topology = {
    "auth-service": ["payment-service"],
    "payment-service": ["order-service"],
    "inventory-service": ["order-service"],
}


async def analyze_blast_radius(event_type: str, payload: dict, message_id: str):
    if event_type == "ANOMALY_DETECTED":
        root_service = payload.get("service")
        impacted = topology.get(root_service, [])
        logger.warn("blast_radius_calculated", root=root_service, impacted=impacted)

        await event_bus.publish(
            "incident_stream",
            "BLAST_RADIUS_MAPPED",
            {
                "root_cause_candidate": root_service,
                "impacted_services": impacted,
                "anomaly_details": payload,
            },
        )


async def run_consumer():
    await event_bus.connect()
    await event_bus.consume(
        "dependency_stream", "dependency_group", "dep_1", analyze_blast_radius
    )


@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())
    logger.info("Dependency Engine started")
