"""
Chaos Controller — state stored in Redis (survives pod restarts).
"""
import asyncio
import json
import logging
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.core.health import register_health_endpoints
from pkg.eventbus.client import EventBusClient

configure_logging("chaos-controller")
logger = logging.getLogger("chaos-controller")

app = FastAPI(title="Chaos Controller")
bootstrap_telemetry(app, "chaos-controller", "http://otel-collector.incident-agent-observability.svc.cluster.local:4317")
event_bus = EventBusClient("redis://redis-master.incident-agent-system.svc.cluster.local:6379")
register_health_endpoints(app, "chaos-controller")

# ── Redis key for persistent experiment state ──────────────────────────
REDIS_KEY = "chaos:active_experiments"

class ChaosExperiment(BaseModel):
    scenario_id: str
    target_service: str = "all"
    duration_seconds: int = 60

# ── Helpers that read/write from Redis ────────────────────────────────
async def _load_experiments() -> dict:
    await event_bus._ensure_connected()
    raw = await event_bus.client.get(REDIS_KEY)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}

async def _save_experiments(experiments: dict):
    await event_bus._ensure_connected()
    await event_bus.client.set(REDIS_KEY, json.dumps(experiments))

async def _add_experiment(exp_id: str, data: dict):
    exps = await _load_experiments()
    exps[exp_id] = data
    await _save_experiments(exps)

async def _remove_experiment(exp_id: str):
    exps = await _load_experiments()
    exps.pop(exp_id, None)
    await _save_experiments(exps)

# ── API endpoints ─────────────────────────────────────────────────────
@app.post("/start")
async def start_chaos(experiment: ChaosExperiment):
    exps = await _load_experiments()
    if exps:
        raise HTTPException(status_code=400, detail="An experiment is already running. Stop it first.")

    exp_id = f"exp_{int(time.time())}"

    await event_bus.publish("chaos.stream", "ChaosStarted", {
        "experiment_id": exp_id,
        "scenario_id": experiment.scenario_id,
        "target_service": experiment.target_service,
        "duration_seconds": experiment.duration_seconds
    })

    await _add_experiment(exp_id, {
        **experiment.dict(),
        "experiment_id": exp_id,
        "started_at": time.time()
    })

    logger.info(f"Started chaos experiment {exp_id} for scenario {experiment.scenario_id}")
    return {"status": "started", "experiment_id": exp_id}


@app.post("/stop/{experiment_id}")
async def stop_chaos(experiment_id: str):
    exps = await _load_experiments()
    if experiment_id not in exps:
        raise HTTPException(status_code=404, detail="Experiment not found")

    await event_bus.publish("chaos.stream", "ChaosStopped", {
        "experiment_id": experiment_id
    })

    await _remove_experiment(experiment_id)
    logger.info(f"Stopped chaos experiment {experiment_id}")
    return {"status": "stopped"}


@app.post("/stop/all")
async def stop_all_chaos():
    """Emergency: clear all active experiments."""
    exps = await _load_experiments()
    for exp_id in list(exps.keys()):
        await event_bus.publish("chaos.stream", "ChaosStopped", {"experiment_id": exp_id})
    await _save_experiments({})
    logger.info("Stopped all chaos experiments")
    return {"status": "all stopped"}


@app.get("/status")
async def get_status():
    exps = await _load_experiments()
    return {"active_experiments": exps}


# ── Background: auto-stop on recovery ────────────────────────────────
async def handle_recovery(event_type: str, payload: dict, message_id: str):
    if event_type == "RECOVERY_COMPLETED":
        target = payload.get("target")
        exps = await _load_experiments()
        for exp_id, exp_data in list(exps.items()):
            if exp_data.get("target_service") in (target, "all"):
                logger.info(f"Auto-stopping chaos {exp_id} due to recovery of {target}")
                await event_bus.publish("chaos.stream", "ChaosStopped", {"experiment_id": exp_id})
                await _remove_experiment(exp_id)


async def run_consumer():
    await event_bus.connect()
    await event_bus.consume(
        "recovery_stream", "chaos_controller_group", "chaos_ctrl_1", handle_recovery
    )


@app.on_event("startup")
async def startup():
    await event_bus.connect()
    asyncio.create_task(run_consumer())
    logger.info("Chaos Controller started (Redis-backed state)")
