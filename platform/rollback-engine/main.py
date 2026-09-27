import asyncio
import logging
import os
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("rollback-engine")
app = FastAPI(title="Rollback Engine", version="1.0.0")

bootstrap_telemetry(app, "rollback-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "rollback-engine")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")

KUBE_CONTROLLER_URL = os.getenv(
    "KUBE_CONTROLLER_URL",
    "http://kubernetes-controller.incident-agent-system.svc.cluster.local",
)
TARGET_NAMESPACE = os.getenv("TARGET_NAMESPACE", "hindsight-agent-apps")


class RollbackRequest(BaseModel):
    incident_id: str
    target: str
    reason: str = "Automated recovery verification failed"


async def execute_rollback(incident_id: str, target: str, reason: str = "") -> bool:
    logger.warn("initiating_rollback", incident_id=incident_id, target=target, reason=reason)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "target": target,
                "workflow": [
                    {
                        "step": 1,
                        "command": f"kubectl rollout undo deployment/{target} -n {TARGET_NAMESPACE}",
                    },
                    {"step": 2, "command": "verify_health_probes"},
                ],
            }
            res = await client.post(f"{KUBE_CONTROLLER_URL}/execute", json=payload)
            res.raise_for_status()

        logger.info("rollback_executed_successfully", incident_id=incident_id, target=target)

        await event_bus.publish(
            "recovery_stream",
            "ROLLBACK_COMPLETED",
            {
                "incident_id": incident_id,
                "target": target,
                "status": "rolled_back",
                "details": f"Rollback executed successfully for {target}",
            },
        )

        await event_bus.publish(
            "audit_events",
            "ROLLBACK_EXECUTED",
            {
                "incident_id": incident_id,
                "target": target,
                "status": "success",
                "action": "rollout_undo",
                "reason": reason,
            },
        )
        return True

    except Exception as e:
        logger.error("rollback_execution_failed", incident_id=incident_id, target=target, error=str(e))
        await event_bus.publish(
            "recovery_stream",
            "ROLLBACK_FAILED",
            {
                "incident_id": incident_id,
                "target": target,
                "error": str(e),
            },
        )
        return False


async def handle_recovery_event(event_type: str, payload: dict, message_id: str):
    if event_type == "RECOVERY_FAILED":
        incident_id = payload.get("incident_id", "UNKNOWN")
        target = payload.get("target") or payload.get("root_cause")
        if target:
            await execute_rollback(
                incident_id=incident_id,
                target=target,
                reason="Recovery plan verification returned failure",
            )


@app.post("/rollback")
async def trigger_manual_rollback(req: RollbackRequest):
    success = await execute_rollback(
        incident_id=req.incident_id,
        target=req.target,
        reason=req.reason,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Rollback execution failed")
    return {"status": "executed", "incident_id": req.incident_id, "target": req.target}


async def run_consumer():
    await event_bus.connect()
    await event_bus.consume(
        stream="recovery_stream",
        group="rollback_group",
        consumer="rollback_1",
        callback=handle_recovery_event,
    )


@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())
    logger.info("Rollback Engine started")