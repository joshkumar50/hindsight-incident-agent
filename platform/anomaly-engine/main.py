import asyncio

from fastapi import FastAPI

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient
from pkg.math_engine.anomaly import RollingStatistics

config = get_config()
logger = configure_logging("anomaly-engine")
app = FastAPI(title="Anomaly Engine", version="1.0.0")

bootstrap_telemetry(app, "anomaly-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "anomaly-engine")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")

# Stateful trackers per service/metric
# In production, this would be backed by Redis for multi-pod consistency
trackers = {}


async def process_anomaly(event_type: str, payload: dict, message_id: str):
    if event_type == "AGGREGATED_METRIC":
        service = payload.get("data", {}).get("service", "unknown")
        value = payload.get("data", {}).get("latency_ms", 0.0)

        if service not in trackers:
            trackers[service] = RollingStatistics(window_size=30)

        z_score = trackers[service].update(value)

        if z_score and abs(z_score) > 3.0:
            logger.warn(
                "anomaly_detected", service=service, z_score=z_score, value=value
            )
            await event_bus.publish(
                "dependency_stream",
                "ANOMALY_DETECTED",
                {
                    "service": service,
                    "z_score": z_score,
                    "metric": "latency_ms",
                    "value": value,
                },
            )


async def run_consumer():
    await event_bus.connect()
    await event_bus.consume(
        "anomaly_stream", "anomaly_group", "anomaly_1", process_anomaly
    )


@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())
    logger.info("Anomaly Engine started")
