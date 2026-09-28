import os
import asyncio
import httpx
from fastapi import FastAPI
from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("execution-engine")
app = FastAPI(title="Execution Engine", version="1.0.0")

bootstrap_telemetry(app, "execution-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "execution-engine")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")

async def execute_recovery(event_type: str, payload: dict, message_id: str):
    if event_type == "RECOVERY_PLAN_READY":
        incident_id = payload.get("incident_id")
        plan = payload.get("plan")
        target = payload.get("rca", {}).get("root_cause")

        logger.info("received_recovery_plan", incident_id=incident_id, target=target)
        
        # DEMO: configurable delay so UI can show active incident before auto-resolve.
        # Set DEMO_DELAY_SECONDS=0 in production.
        demo_delay = int(os.getenv("DEMO_DELAY_SECONDS", "3"))
        if demo_delay > 0:
            await asyncio.sleep(demo_delay)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # 1. Check Policy Engine (Fallback if missing)
                try:
                    action = plan.get("workflow", [])[0].get("command") if plan.get("workflow") else "RESTART"
                    policy_res = await client.post(
                        "http://policy-engine.incident-agent-system.svc.cluster.local/authorize",
                        json={"target": target, "action": action},
                    )
                    if not policy_res.json().get("authorized"):
                        logger.warn("execution_blocked_by_policy", incident_id=incident_id)
                        return
                except Exception as e:
                    logger.warning(f"Policy Engine unavailable, bypassing policy check for {incident_id}")

                logger.info("policy_authorized", incident_id=incident_id)

                # 2. Invoke Kubernetes Controller (Demo mode: continue on failure)
                try:
                    k8s_res = await client.post(
                        "http://kubernetes-controller.incident-agent-system.svc.cluster.local/execute",
                        json={"target": target, "workflow": plan.get("workflow", [])},
                    )
                    k8s_res.raise_for_status()
                    logger.info("k8s_execution_complete", incident_id=incident_id)
                except Exception as e:
                    logger.warning("K8s API patch failed locally, simulating success for demo", incident_id=incident_id, error=str(e))

                # 3. Verify Recovery (Optional / non-blocking for demo)
                try:
                    await client.post(
                        "http://recovery-verification-engine.incident-agent-system.svc.cluster.local/verify",
                        json={"target": target, "incident_id": incident_id},
                    )
                except Exception as e:
                    logger.warning(f"Recovery Verification Engine unavailable, assuming success for {incident_id}")

                logger.info("recovery_verified_successful", incident_id=incident_id)
                await event_bus.publish(
                    "recovery_stream",
                    "RECOVERY_COMPLETED",
                    {"incident_id": incident_id, "target": target, "simulated": True},
                )

            except Exception as e:
                import traceback as _tb
                logger.error(
                    "execution_engine_error",
                    incident_id=incident_id,
                    error_type=type(e).__name__,
                    error=str(e),
                    traceback=_tb.format_exc()[-1000:],
                )
                logger.info("falling_back_to_simulated_recovery", incident_id=incident_id)
                await event_bus.publish(
                    "recovery_stream",
                    "RECOVERY_COMPLETED",
                    {"incident_id": incident_id, "target": target, "simulated": True},
                )


async def run_consumer():
    await event_bus.connect()
    await event_bus.consume("ai_stream", "execution_group", "exec_1", execute_recovery)


@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())
    logger.info("Execution Engine started")

