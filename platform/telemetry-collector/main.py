from fastapi import FastAPI, Request

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("telemetry-collector")
app = FastAPI(title="Telemetry Collector", version="1.0.0")

bootstrap_telemetry(app, "telemetry-collector", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "telemetry-collector")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")


@app.on_event("startup")
async def startup():
    await event_bus.connect()
    logger.info("Telemetry Collector started")


@app.post("/ingest/logs")
async def ingest_logs(request: Request):
    """
    Ingests raw JSON logs from the cluster (via FluentBit/OTel), normalizes them,
    and publishes them to the 'telemetry_stream' for the Monitoring Engine.
    """
    payload = await request.json()
    logger.debug("ingesting_logs", size=len(payload))
    await event_bus.publish("telemetry_stream", "LOG_INGESTED", {"data": payload})
    return {"status": "ingested"}


@app.post("/ingest/metrics")
async def ingest_metrics(request: Request):
    """Ingests raw metrics and publishes for Anomaly detection."""
    payload = await request.json()
    logger.debug("ingesting_metrics", size=len(payload))
    await event_bus.publish("telemetry_stream", "METRIC_INGESTED", {"data": payload})
    return {"status": "ingested"}
