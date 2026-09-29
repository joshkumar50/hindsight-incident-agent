import os
from fastapi import FastAPI
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry

config = get_config()
logger = configure_logging("knowledge-engine")
app = FastAPI(title="Knowledge Engine", version="1.0.0")

bootstrap_telemetry(app, "knowledge-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "knowledge-engine")

# ---------------------------------------------------------------------------
# Hindsight SDK initialisation
# Signatures verified in PHASE1_SDK.md from hindsight-client==0.10.1:
#   Hindsight(base_url: str, api_key: str | None = None, ...)
#   recall(bank_id: str, query: str, ...) -> RecallResponse
#   retain(bank_id: str, content: str | list[dict], ...) -> RetainResponse
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
            _HINDSIGHT_BASE_URL,         # base_url: str  (required positional)
            api_key=_HINDSIGHT_API_KEY,  # api_key: str | None
        )
        HINDSIGHT_ENABLED = True
        logger.info("hindsight_enabled", base_url=_HINDSIGHT_BASE_URL)
    except Exception as _e:
        logger.warning("hindsight_init_failed", error=str(_e))

_HINDSIGHT_BANK_ID = "incident-memory-bank"


class SearchQuery(BaseModel):
    root_cause: str


class RetainQuery(BaseModel):
    incident_id: str
    resolution: str


@app.post("/search")
async def search_history(query: SearchQuery):
    """
    Search historical incident memory using Hindsight SDK recall().
    Returns empty list — never fake data — when Hindsight is unavailable.
    """
    logger.info("searching_knowledge_base", query=query.root_cause)

    if not HINDSIGHT_ENABLED:
        logger.warning("hindsight_not_enabled_search_skipped")
        return {"historical_matches": []}

    try:
        results = await hindsight.arecall(
            bank_id=_HINDSIGHT_BANK_ID,
            query=query.root_cause,
        )
        def _extract_score(s) -> float:
            if s is None:
                return 0.0
            if isinstance(s, dict):
                return float(s.get("final") or s.get("similarity") or 0.0)
            return float(getattr(s, "final", 0.0) or 0.0)

        matches = []
        for item in results.results:
            score = _extract_score(item.scores)
            matches.append({
                "document_id": getattr(item, "document_id", None),
                "text": item.text,
                "score": score,
                "metadata": item.metadata or {},
            })
        return {"historical_matches": matches}
    except Exception as e:
        logger.error("hindsight_recall_failed", error=str(e))
        return {"historical_matches": []}


@app.post("/retain")
async def retain_history(data: RetainQuery):
    """
    Store new incident resolution into Hindsight memory using retain().
    """
    logger.info("retaining_knowledge_base", incident_id=data.incident_id)

    if not HINDSIGHT_ENABLED:
        logger.warning("hindsight_not_enabled_retain_skipped")
        return {"status": "skipped", "reason": "HINDSIGHT_API_KEY not configured"}

    try:
        await hindsight.aretain(
            bank_id=_HINDSIGHT_BANK_ID,
            content=f"Incident {data.incident_id} was resolved by: {data.resolution}",
        )
    except Exception as e:
        logger.error("hindsight_retain_failed", error=str(e))
        return {"status": "error", "message": str(e)}

    return {"status": "success"}


@app.get("/memory/stats")
async def memory_stats():
    """
    Return memory bank stats.
    # TODO: SDK has no count method — total_memories is always -1.
    """
    # TODO: SDK has no count method — hindsight_client==0.10.1 exposes no
    # list/count endpoint for total retained memories in a bank.
    return {"bank_id": _HINDSIGHT_BANK_ID, "total_memories": -1}
