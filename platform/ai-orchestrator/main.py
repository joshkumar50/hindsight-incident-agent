import asyncio
import os

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

# ---------------------------------------------------------------------------
# Hindsight SDK initialisation
# Signatures verified in PHASE1_SDK.md from hindsight-client==0.10.1:
#   Hindsight(base_url: str, api_key: str | None = None, ...)
#   arecall(bank_id: str, query: str, ...) -> RecallResponse
#   aretain(bank_id: str, content: str | list[dict], ...) -> RetainResponse
# ---------------------------------------------------------------------------
_HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")
_HINDSIGHT_BASE_URL = os.getenv(
    "HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"
)

HINDSIGHT_ENABLED: bool = False
hindsight = None

if not _HINDSIGHT_API_KEY:
    logger.warning(
        "hindsight_disabled",
        reason="HINDSIGHT_API_KEY env var not set — memory recall/retain will be skipped",
    )
else:
    try:
        from hindsight_client import Hindsight  # noqa: E402 — conditional import

        hindsight = Hindsight(
            _HINDSIGHT_BASE_URL,          # base_url: str  (required positional)
            api_key=_HINDSIGHT_API_KEY,   # api_key: str | None
        )
        HINDSIGHT_ENABLED = True
        logger.info("hindsight_enabled", base_url=_HINDSIGHT_BASE_URL)
    except Exception as _e:
        logger.warning("hindsight_init_failed", error=str(_e))

_HINDSIGHT_BANK_ID = "incident-memory-bank"
_MEMORY_HIT_THRESHOLD = 0.8


async def coordinate_ai_workflow(event_type: str, payload: dict, message_id: str):
    if event_type == "INCIDENT_DECLARED":
        incident_id = payload.get("incident_id")
        incident_description = payload.get("description", payload.get("root_cause", ""))
        logger.info("orchestrating_incident_resolution", incident_id=incident_id)

        # -----------------------------------------------------------------------
        # MEMORY RECALL — short-circuit path
        # If Hindsight returns a high-confidence hit (>= 0.8), skip the full
        # AI pipeline and replay the historical playbook immediately.
        # -----------------------------------------------------------------------
        if HINDSIGHT_ENABLED:
            try:
                memory_results = await hindsight.arecall(
                    bank_id=_HINDSIGHT_BANK_ID,
                    query=incident_description,
                )
                
                def _extract_score(s) -> float:
                    if s is None:
                        return 0.0
                    if isinstance(s, dict):
                        return float(s.get("final") or s.get("similarity") or 0.0)
                    return float(getattr(s, "final", 0.0) or 0.0)

                top_score = 0.0
                top_item = None
                if memory_results.results:
                    top_item = memory_results.results[0]
                    top_score = _extract_score(top_item.scores)

                if top_item is not None and top_score >= _MEMORY_HIT_THRESHOLD:
                    # High-confidence memory hit — short-circuit full pipeline
                    logger.info(
                        "memory_hit_short_circuit",
                        incident_id=incident_id,
                        score=top_score,
                    )
                    
                    await event_bus.publish(
                        "ai_stream",
                        "RECOVERY_PLAN_READY",
                        {
                            "incident_id": incident_id,
                            "memory_hit": True,
                            "rca": top_item.text,
                            "plan": top_item.text,
                        },
                    )
                    await event_bus.publish(
                        "audit_events",
                        "AUTONOMOUS_DECISION",
                        {
                            "incident_id": incident_id,
                            "event_type": "AUTONOMOUS_DECISION",
                            "decision": "MEMORY_RECALL",
                            "confidence_score": top_score,
                            "human_approved": False,
                            "model_name": "hindsight",
                            "rca": top_item.text,
                        },
                    )
                    logger.info(
                        "orchestration_complete_via_memory",
                        incident_id=incident_id,
                    )
                    return  # <-- short-circuit: no LLM pipeline needed
            except Exception as _recall_err:
                # Recall failure must NOT block the normal pipeline
                logger.warning(
                    "hindsight_recall_failed",
                    incident_id=incident_id,
                    error=str(_recall_err),
                )

        # -----------------------------------------------------------------------
        # FULL AI PIPELINE — memory miss path
        # -----------------------------------------------------------------------
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

                # 5. Output Final Package (memory miss path — memory_hit=False)
                await event_bus.publish(
                    "ai_stream",
                    "RECOVERY_PLAN_READY",
                    {
                        "incident_id": incident_id,
                        "memory_hit": False,
                        "rca": rca_data,
                        "plan": plan_data,
                    },
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

                # ---------------------------------------------------------------
                # MEMORY RETAIN — store resolved incident for future recall
                # Wrapped in try/except: retain failure must NOT crash the pipeline
                # ---------------------------------------------------------------
                if HINDSIGHT_ENABLED:
                    try:
                        await hindsight.aretain(
                            bank_id=_HINDSIGHT_BANK_ID,
                            content=(
                                f"Incident {incident_id} resolved. "
                                f"Root cause: {rca_data}. "
                                f"Recovery plan: {plan_data}."
                            ),
                        )
                        logger.info("hindsight_retained", incident_id=incident_id)
                    except Exception as _retain_err:
                        logger.warning(
                            "hindsight_retain_failed",
                            incident_id=incident_id,
                            error=str(_retain_err),
                        )

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
