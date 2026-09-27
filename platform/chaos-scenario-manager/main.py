import asyncio
import logging
import httpx
from fastapi import FastAPI
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.core.health import register_health_endpoints
from pkg.eventbus.client import EventBusClient

configure_logging("chaos-scenario-manager")
logger = logging.getLogger("chaos-scenario-manager")

app = FastAPI(title="Chaos Scenario Manager")
bootstrap_telemetry(app, "chaos-scenario-manager", "http://otel-collector.incident-agent-observability.svc.cluster.local:4317")
event_bus = EventBusClient("redis://redis-master.incident-agent-system.svc.cluster.local:6379")
register_health_endpoints(app, "chaos-scenario-manager")

SCENARIOS = {
    "1": {"name": "Database Lock", "fault_type": "database_lock", "traffic_mode": "normal"},
    "2": {"name": "CPU Spike", "fault_type": "cpu_stress", "traffic_mode": "burst"},
    "3": {"name": "Memory Leak", "fault_type": "memory_stress", "traffic_mode": "normal"},
    "4": {"name": "Network Latency", "fault_type": "network_delay", "traffic_mode": "high_latency"},
    "5": {"name": "Packet Loss", "fault_type": "packet_loss", "traffic_mode": "normal"},
    "6": {"name": "CrashLoopBackOff", "fault_type": "container_restart", "traffic_mode": "normal"},
    "7": {"name": "Pod Crash", "fault_type": "pod_deletion", "traffic_mode": "normal"},
    "8": {"name": "Deployment Failure", "fault_type": "deployment_restart", "traffic_mode": "normal"},
    "9": {"name": "Replica Failure", "fault_type": "replica_reduction", "traffic_mode": "normal"},
    "10": {"name": "Node Drain Simulation", "fault_type": "pod_eviction", "traffic_mode": "normal"},
    "11": {"name": "Redis Failure", "fault_type": "redis_lock", "traffic_mode": "normal"},
    "12": {"name": "API Gateway Failure", "fault_type": "service_timeout", "traffic_mode": "mixed"},
    "13": {"name": "High Error Rate", "fault_type": "http_error", "traffic_mode": "random"},
    "14": {"name": "Slow Database Queries", "fault_type": "artificial_latency", "traffic_mode": "constant"},
    "15": {"name": "Cascading Failure", "fault_type": "thread_blocking", "traffic_mode": "burst"}
}

async def trigger_traffic(mode: str):
    url = "http://traffic-generator.hindsight-agent-apps.svc.cluster.local:8000/start"
    payload = {"mode": mode, "rate": 20, "target_url": "http://api-gateway.hindsight-agent-apps.svc.cluster.local"}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=5.0)
            logger.info(f"Triggered traffic generator in mode: {mode}")
    except Exception as e:
        logger.error(f"Failed to trigger traffic generator: {e}")

async def stop_traffic():
    url = "http://traffic-generator.hindsight-agent-apps.svc.cluster.local:8000/stop"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, timeout=5.0)
            logger.info("Stopped traffic generator")
    except Exception as e:
        logger.error(f"Failed to stop traffic generator: {e}")

async def handle_chaos_event(event_type: str, event: dict, message_id: str):
    if event_type == "ChaosStarted":
        scenario_id = str(event.get("scenario_id"))
        scenario = SCENARIOS.get(scenario_id)
        if not scenario:
            logger.error(f"Unknown scenario ID: {scenario_id}")
            return
            
        logger.info(f"Executing Scenario: {scenario['name']}")
        
        # 1. Trigger Traffic Generator
        await trigger_traffic(scenario['traffic_mode'])
        
        # 2. Trigger Fault Injection
        await event_bus.publish("fault.stream", "InjectFault", {
            "fault_type": scenario['fault_type'],
            "target_service": event.get("target_service"),
            "duration_seconds": event.get("duration_seconds")
        })
        
    elif event_type == "ChaosStopped":
        await stop_traffic()
        await event_bus.publish("fault.stream", "StopFault", {})

@app.on_event("startup")
async def startup_event():
    logger.info("Starting chaos-scenario-manager consumer in background...")
    asyncio.create_task(event_bus.consume(
        stream="chaos.stream",
        group="scenario_manager_group",
        consumer="scenario_manager_1",
        callback=handle_chaos_event
    ))
