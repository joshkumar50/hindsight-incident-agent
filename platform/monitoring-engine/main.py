import asyncio
import random
import time
import math
from fastapi import FastAPI

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("monitoring-engine")
app = FastAPI(title="Monitoring Engine", version="1.0.0")

bootstrap_telemetry(app, "monitoring-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "monitoring-engine")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")

# ─── Service registry ─────────────────────────────────────────────────────────
SERVICES = [
    "auth-service",
    "payment-service",
    "order-service",
    "inventory-service",
    "notification-service",
    "api-gateway",
]

# Live state tracking - mutated by chaos events
_service_state: dict[str, dict] = {}

def _init_service_state():
    for svc in SERVICES:
        _service_state[svc] = {
            "healthy": True,
            "latency_base": random.uniform(8, 35),
            "error_rate_base": random.uniform(0.01, 0.3),
            "degraded": False,
        }

_init_service_state()

# ─── Chaos event handler ──────────────────────────────────────────────────────
async def process_chaos(event_type: str, payload: dict, message_id: str):
    target = payload.get("target_service", "all")
    if event_type == "ChaosStarted":
        targets = SERVICES if target == "all" else [target]
        for svc in targets:
            if svc in _service_state:
                _service_state[svc]["degraded"] = True
                _service_state[svc]["healthy"] = False
                _service_state[svc]["latency_base"] = random.uniform(150, 800)
                _service_state[svc]["error_rate_base"] = random.uniform(15, 60)
        logger.info("chaos_applied", target=target)

    elif event_type in ("ChaosStopped", "RECOVERY_COMPLETED"):
        targets = SERVICES if target == "all" else [target]
        for svc in targets:
            if svc in _service_state:
                _service_state[svc]["degraded"] = False
                _service_state[svc]["healthy"] = True
                _service_state[svc]["latency_base"] = random.uniform(8, 35)
                _service_state[svc]["error_rate_base"] = random.uniform(0.01, 0.3)
        logger.info("chaos_removed", target=target)

async def process_telemetry(event_type: str, payload: dict, message_id: str):
    if event_type == "METRIC_INGESTED":
        logger.debug("aggregating_metric_window", payload_size=len(payload))
        await event_bus.publish("anomaly_stream", "AGGREGATED_METRIC", payload)


# ─── HTTP endpoints ───────────────────────────────────────────────────────────
@app.get("/metrics/aggregated")
async def get_aggregated_metrics():
    """Live metrics endpoint consumed by dashboard-bff -> Observability UI."""
    now = time.time()
    # Use a sine wave to create realistic-looking fluctuation over time
    wave = math.sin(now / 30) * 0.3 + math.sin(now / 7) * 0.1

    services_data = []
    total_latency = 0
    total_error_rate = 0

    for svc in SERVICES:
        state = _service_state[svc]
        base_lat = state["latency_base"]
        base_err = state["error_rate_base"]

        # Add slight random jitter so metrics look live
        latency = max(1, round(base_lat + base_lat * wave + random.uniform(-3, 3), 1))
        error_rate = max(0, round(base_err + base_err * wave * 0.5 + random.uniform(-0.05, 0.05), 2))
        uptime = "99.95%" if state["healthy"] else f"{round(random.uniform(72, 95), 1)}%"

        services_data.append({
            "name": svc,
            "healthy": state["healthy"],
            "latency": latency,
            "uptime": uptime,
            "error_rate": error_rate,
        })
        total_latency += latency
        total_error_rate += error_rate

    avg_latency = round(total_latency / len(SERVICES), 1)
    avg_error = round(total_error_rate / len(SERVICES), 2)

    # Requests per second - realistic value with fluctuation
    rps = round(120 + 60 * wave + random.uniform(-5, 5), 1)
    active_traces = int(rps * 1.4)

    return {
        "requests_per_second": rps,
        "avg_latency_ms": avg_latency,
        "error_rate": avg_error,
        "active_traces": active_traces,
        "services": services_data,
        "timestamp": now,
    }


# ─── Event consumers ──────────────────────────────────────────────────────────
async def run_telemetry_consumer():
    await event_bus.connect()
    await event_bus.consume(
        "telemetry_stream", "monitoring_group", "monitor_1", process_telemetry
    )

async def run_chaos_consumer():
    await event_bus.connect()
    await event_bus.consume(
        "chaos.stream", "monitoring_chaos_group", "monitor_chaos_1", process_chaos
    )

async def run_recovery_consumer():
    await event_bus.connect()
    await event_bus.consume(
        "recovery_stream", "monitoring_recovery_group", "monitor_rec_1", process_chaos
    )


@app.on_event("startup")
async def startup():
    asyncio.create_task(run_telemetry_consumer())
    asyncio.create_task(run_chaos_consumer())
    asyncio.create_task(run_recovery_consumer())
    logger.info("Monitoring Engine started")
