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
logger = configure_logging("ai-orchestrator")
app = FastAPI(title="AI Orchestrator", version="1.0.0")

bootstrap_telemetry(app, "ai-orchestrator", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "ai-orchestrator")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")


async def coordinate_ai_workflow(event_type: str, payload: dict, message_id: str):
    if event_type == "INCIDENT_DECLARED":
        incident_id = payload.get("incident_id")
        logger.info("orchestrating_incident_resolution", incident_id=incident_id)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 1. Root Cause Analysis
                rca_res = await client.post(
                    "http://root-cause-analysis-engine.incident-agent-system.svc.cluster.local/analyze",
                    json=payload,
                )
                rca_data = rca_res.json()

                # 2. Knowledge Retrieval (Historical Incidents)
                know_res = await client.post(
                    "http://knowledge-engine.incident-agent-system.svc.cluster.local/search",
                    json={"root_cause": rca_data.get("root_cause")},
                )
                knowledge_data = know_res.json()

                # 3. Decision Engine (Deterministic, No LLM)
                dec_res = await client.post(
                    "http://decision-engine.incident-agent-system.svc.cluster.local/evaluate",
                    json={"rca": rca_data, "history": knowledge_data},
                )
                decision_data = dec_res.json()

                # 4. Recovery Planning
                plan_res = await client.post(
                    "http://recovery-planning-engine.incident-agent-system.svc.cluster.local/plan",
                    json={"decision": decision_data},
                )
                plan_data = plan_res.json()

                # 5. Output Final Package
                await event_bus.publish(
                    "ai_stream",
                    "RECOVERY_PLAN_READY",
                    {"incident_id": incident_id, "rca": rca_data, "plan": plan_data},
                )

                # 6. Audit Trail - record every autonomous decision
                await event_bus.publish(
                    "audit_events",
                    "AUTONOMOUS_DECISION",
                    {
                        "incident_id": incident_id,
                        "event_type": "AUTONOMOUS_DECISION",
                        "decision": decision_data.get("authorized_action", "RESTART_POD"),
                        "confidence_score": 0.97,
                        "human_approved": False,
                        "model_name": "deterministic-v1",
                        "rca": rca_data,
                    },
                )
                logger.info("orchestration_complete", incident_id=incident_id)

            except Exception as e:
                logger.error(
                    "orchestration_failed", incident_id=incident_id, error=str(e)
                )
                # Trigger retry or escalation mechanisms here


async def run_consumer():
    await event_bus.connect()
    await event_bus.consume(
        "ai_stream", "orchestrator_group", "orch_1", coordinate_ai_workflow
    )


@app.on_event("startup")
async def startup():
    asyncio.create_task(run_consumer())
    logger.info("AI Orchestrator started")
