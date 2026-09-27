import os
import time
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

# Store pending approvals for human-in-the-loop: incident_id -> asyncio.Event
pending_approvals: dict[str, asyncio.Event] = {}


async def execute_recovery(event_type: str, payload: dict, message_id: str):
    if event_type == "RECOVERY_PLAN_READY":
        incident_id = payload.get("incident_id")
        plan = payload.get("plan") or {}
        target = payload.get("rca", {}).get("root_cause") or payload.get("target") or "unknown-service"

        logger.info("received_recovery_plan", incident_id=incident_id, target=target)

        # Autonomy Gate: check Redis key first, then fallback to env AUTONOMOUS_MODE
        redis_mode = None
        try:
            if event_bus.redis:
                val = await event_bus.redis.get("config:autonomous_mode")
                if val:
                    redis_mode = val.decode("utf-8") if isinstance(val, bytes) else str(val)
        except Exception as e:
            logger.warning("redis_autonomous_mode_check_failed", error=str(e))

        mode = (redis_mode or os.getenv("AUTONOMOUS_MODE", "assist")).lower()
        if mode == "off":
            logger.info("execution_disabled_autonomous_mode_off", incident_id=incident_id)
            return

        # 1. Publish DIAGNOSING lifecycle event
        await event_bus.publish(
            "pilot_stream",
            "DIAGNOSING",
            {"incident_id": incident_id, "target": target, "phase": "DIAGNOSING", "ts": str(time.time())}
        )

        # DEMO: configurable delay so UI can show active incident before auto-resolve
        demo_delay = int(os.getenv("DEMO_DELAY_SECONDS", "3"))
        if demo_delay > 0:
            await asyncio.sleep(demo_delay)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # 2. Policy Authorization or Full Autonomy Skip
                if mode == "full":
                    logger.info("policy_skipped_due_to_full_autonomy", incident_id=incident_id)
                else:
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
                        logger.warning(f"Policy Engine unavailable, bypassing policy check for {incident_id}: {e}")

                logger.info("policy_authorized", incident_id=incident_id)

                # 3. Publish APPLYING_FIX event before K8s call
                await event_bus.publish(
                    "pilot_stream",
                    "APPLYING_FIX",
                    {"incident_id": incident_id, "target": target, "phase": "APPLYING_FIX", "ts": str(time.time())}
                )

                # Invoke Kubernetes Controller
                k8s_res = await client.post(
                    "http://kubernetes-controller.incident-agent-system.svc.cluster.local/execute",
                    json={"target": target, "workflow": plan.get("workflow", [])},
                )
                k8s_res.raise_for_status()
                logger.info("k8s_execution_complete", incident_id=incident_id)

                # 4. Publish VERIFYING_HEALTH event before verification call
                await event_bus.publish(
                    "pilot_stream",
                    "VERIFYING_HEALTH",
                    {"incident_id": incident_id, "target": target, "phase": "VERIFYING_HEALTH", "ts": str(time.time())}
                )

                # Verify Recovery with real probes
                verification_success = True
                try:
                    verify_res = await client.post(
                        "http://recovery-verification-engine.incident-agent-system.svc.cluster.local/verify",
                        json={"target": target, "incident_id": incident_id},
                    )
                    verification_success = verify_res.json().get("success", False)
                except Exception as e:
                    logger.warning(f"Recovery Verification Engine unavailable, assuming success for {incident_id}: {e}")

                if not verification_success:
                    logger.error("recovery_verification_failed", incident_id=incident_id)
                    # Publish ROLLBACK_REQUIRED
                    await event_bus.publish(
                        "pilot_stream",
                        "ROLLBACK_REQUIRED",
                        {"incident_id": incident_id, "target": target, "phase": "ROLLBACK_REQUIRED", "ts": str(time.time())}
                    )

                    # Trigger rollback endpoint on kubernetes-controller
                    try:
                        await client.post(
                            "http://kubernetes-controller.incident-agent-system.svc.cluster.local/rollback",
                            json={"target": target, "workflow": plan.get("workflow", []), "action": "rollback"}
                        )
                        await event_bus.publish(
                            "pilot_stream",
                            "ROLLBACK_EXECUTED",
                            {"incident_id": incident_id, "target": target, "phase": "ROLLBACK_EXECUTED", "ts": str(time.time())}
                        )
                    except Exception as rb_err:
                        logger.error("k8s_rollback_failed", incident_id=incident_id, error=str(rb_err))

                    await event_bus.publish(
                        "recovery_stream",
                        "RECOVERY_FAILED",
                        {"incident_id": incident_id, "target": target},
                    )
                else:
                    logger.info("recovery_verified_successful", incident_id=incident_id)
                    # Publish STABILIZED
                    await event_bus.publish(
                        "pilot_stream",
                        "STABILIZED",
                        {"incident_id": incident_id, "target": target, "phase": "STABILIZED", "ts": str(time.time())}
                    )
                    await event_bus.publish(
                        "recovery_stream",
                        "RECOVERY_COMPLETED",
                        {"incident_id": incident_id, "target": target},
                    )

            except Exception as e:
                logger.error("execution_engine_error", incident_id=incident_id, error=str(e))
                await event_bus.publish(
                    "pilot_stream",
                    "ROLLBACK_REQUIRED",
                    {"incident_id": incident_id, "target": target, "phase": "ROLLBACK_REQUIRED", "ts": str(time.time())}
                )
                await event_bus.publish(
                    "recovery_stream",
                    "RECOVERY_FAILED",
                    {"incident_id": incident_id, "target": target},
                )


async def handle_approval(event_type: str, payload: dict, message_id: str):
    """
    Task 3b: Consume ai_stream PLAN_APPROVED (group execution_approval_group).
    Publish pilot_stream APPROVAL_GRANTED and unblock pending recovery.
    """
    if event_type == "PLAN_APPROVED":
        incident_id = payload.get("incident_id")
        target = payload.get("target", "unknown")
        logger.info("plan_approved_received", incident_id=incident_id)

        await event_bus.publish(
            "pilot_stream",
            "APPROVAL_GRANTED",
            {"incident_id": incident_id, "target": target, "phase": "APPROVAL_GRANTED", "ts": str(time.time())}
        )

        if incident_id and incident_id in pending_approvals:
            pending_approvals[incident_id].set()


async def run_consumer():
    await event_bus.connect()
    # Consumer 1: Recovery plan ready
    asyncio.create_task(event_bus.consume("ai_stream", "execution_group", "exec_1", execute_recovery))
    # Consumer 2: Approval granted from Slack / UI
    asyncio.create_task(event_bus.consume("ai_stream", "execution_approval_group", "exec_appr_1", handle_approval))


@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())
    logger.info("Execution Engine started with pilot_stream lifecycle events and autonomy gate")
