import asyncio
import logging
from fastapi import FastAPI
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.core.health import register_health_endpoints
from pkg.eventbus.client import EventBusClient

configure_logging("chaos-engine")
logger = logging.getLogger("chaos-engine")

app = FastAPI(title="Chaos Engine")
bootstrap_telemetry(app, "chaos-engine", "http://otel-collector.incident-agent-observability.svc.cluster.local:4317")
event_bus = EventBusClient("redis://redis-master.incident-agent-system.svc.cluster.local:6379")
register_health_endpoints(app, "chaos-engine")

async def handle_chaos_event(event_type: str, event: dict, message_id: str):
    if event_type == "ChaosStarted":
        logger.info(f"Received ChaosStarted event for scenario {event.get('scenario_id')}")
        
        target = event.get("target_service", "all")
        scenario = event.get("scenario_id", "1")
        
        fault_type = "pod_deletion"
        if scenario in ["2", "3", "13"]:
            fault_type = "cpu_stress"
        elif scenario in ["8", "9"]:
            fault_type = "replica_reduction"
            
        await event_bus.publish("fault.stream", "InjectFault", {
            "fault_type": fault_type,
            "target_service": target,
            "duration_seconds": event.get("duration_seconds", 60)
        })
        logger.info(f"Published InjectFault for {target} with type {fault_type}")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting chaos-engine consumer in background...")
    asyncio.create_task(event_bus.consume(
        stream="chaos.stream",
        group="chaos_engine_group",
        consumer="chaos_engine_1",
        callback=handle_chaos_event
    ))
