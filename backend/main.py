"""
====================================================================
main.py - Web API Entry Point for AI-RCI SRE Agent
====================================================================
Purpose: Exposes a high-performance web API with /query and /feedback
         endpoints to invoke the ReAct troubleshooting SRE Agent,
         manage Vectorize Hindsight persistent memory, and process
         human-in-the-loop runbook feedback.
====================================================================
"""

import json
import logging
import os
import sys
import time
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

# Ensure workspace root directory is in sys.path for native imports
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Load configuration, models, and database auditor / cache manager
from shared.config import config
from shared.models import (
    AnalysisRequest,
    AnalysisResponse,
    FeedbackRequest,
    HindsightIncidentAgentException
)
from shared.database import save_analysis, get_cached_analysis, hindsight_memory, get_all_memories
from agent.agent_workflow import AgentWorkflow

# ---- Structlog Setup ----
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = structlog.get_logger("main_api")

# Initialize FastAPI App with metadata
app = FastAPI(
    title="Hindsight Incident Agent Diagnostics API",
    description="Autonomous ReAct troubleshooting SRE Agent with Vectorize Hindsight persistent memory.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Exception handler for platform standard exceptions
@app.exception_handler(HindsightIncidentAgentException)
async def hindsight_exception_handler(request: Request, exc: HindsightIncidentAgentException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details, "status_code": exc.status_code}
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Agent Workflow Instance
logger.info("init_agent_workflow", message="Initializing SRE Agent Workflow engine...")
agent_workflow = AgentWorkflow()


@app.get("/")
def read_root():
    """Welcome screen with details about active LLM providers and agent capabilities."""
    provider = config.default_llm_provider
    model_id = "unknown"
    if provider == "bedrock":
        model_id = config.aws.bedrock_model_id
    elif hasattr(config, provider):
        model_id = getattr(getattr(config, provider), "model_id", "unknown")

    return {
        "status": "online",
        "service": "Hindsight Incident Agent Diagnostics API",
        "active_llm_provider": provider,
        "active_model": model_id,
        "registered_tools": [
            "get_prometheus_metrics",
            "get_elasticsearch_logs",
            "get_jaeger_traces",
            "get_cluster_status"
        ],
        "hindsight_bank": hindsight_memory.bank_id,
        "interactive_docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Simple status check for operations pipelines."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "provider": config.default_llm_provider
    }


@app.post("/query", response_model=AnalysisResponse)
async def execute_agent_query(request: AnalysisRequest):
    """
    Primary endpoint to trigger the ReAct Agent Workflow.
    Accepts a structured AnalysisRequest JSON containing symptoms, namespace, service.
    Returns comprehensive AnalysisResponse with RootCauseAnalysis and telemetry snaps.
    """
    logger.info("agent_query_received", query=request.query, target_service=request.target_service)
    start_time = time.time()

    try:
        # Execute ReAct loop with Hindsight memory recall & retention
        response = await agent_workflow.run(request)
        
        # Backward-compatible cache sync
        save_analysis(request, response)

        duration = time.time() - start_time
        logger.info("agent_query_completed", duration_sec=round(duration, 2), request_id=request.request_id)
        return response

    except HindsightIncidentAgentException:
        raise
    except Exception as e:
        logger.error("agent_query_failed", error=str(e))
        raise HindsightIncidentAgentException(
            message=f"Troubleshooting agent execution failed: {str(e)}",
            status_code=500,
            details={"query": request.query}
        )


@app.get("/query")
async def execute_agent_query_get(
    q: str,
    service: Optional[str] = None,
    namespace: Optional[str] = None,
    lookback: Optional[int] = 30,
    trace_id: Optional[str] = None
):
    """Convenience GET endpoint for quick testing directly from browser URL."""
    logger.info("get_query_received", q=q, service=service)

    req = AnalysisRequest(
        query=q,
        target_service=service,
        target_namespace=namespace,
        lookback_minutes=lookback,
        trace_id=trace_id,
        source="http_get"
    )

    try:
        response = await agent_workflow.run(req)
        save_analysis(req, response)
        return response.model_dump()
    except HindsightIncidentAgentException:
        raise
    except Exception as e:
        logger.error("get_query_failed", error=str(e))
        raise HindsightIncidentAgentException(
            message=f"Troubleshooting agent execution failed: {str(e)}",
            status_code=500
        )


@app.post("/feedback")
async def record_feedback(feedback: FeedbackRequest):
    """
    Task 3: Runbook Evolution (human feedback) endpoint.
    Records operator verdict (accept | reject | modify) and updates Hindsight memory.
    """
    logger.info(
        "runbook_feedback_received",
        incident_id=feedback.incident_id,
        verdict=feedback.verdict,
        user=feedback.user
    )

    if feedback.verdict == "accept":
        await hindsight_memory.retain(
            incident_id=feedback.incident_id,
            symptoms=f"Incident {feedback.incident_id}",
            root_cause="Human Accepted Playbook",
            playbook=feedback.corrected_playbook or ["Verified Runbook Steps"],
            human_approved=True,
            outcome="human_validated"
        )
    elif feedback.verdict == "modify":
        corrected = feedback.corrected_playbook or "Updated operator remediation steps"
        logger.info(
            "runbook_feedback_diff",
            incident_id=feedback.incident_id,
            user=feedback.user,
            diff=f"Modified playbook to: {corrected}"
        )
        await hindsight_memory.retain(
            incident_id=feedback.incident_id,
            symptoms=f"Incident {feedback.incident_id}",
            root_cause="Human Modified Playbook",
            playbook=[corrected] if isinstance(corrected, str) else corrected,
            human_approved=True,
            outcome="human_modified"
        )
    elif feedback.verdict == "reject":
        await hindsight_memory.retain(
            incident_id=feedback.incident_id,
            symptoms=f"Incident {feedback.incident_id}",
            root_cause="Human Rejected Playbook",
            playbook=["Rejected playbook - do not recommend"],
            human_approved=False,
            outcome="human_rejected"
        )
    else:
        raise HindsightIncidentAgentException(
            message=f"Invalid feedback verdict: {feedback.verdict}. Must be accept, reject, or modify.",
            status_code=400
        )

    # Persist feedback to existing PostgreSQL audit table if reachable
    db_persisted = False
    pg_host = os.getenv("POSTGRES_HOST")
    if pg_host:
        try:
            import asyncpg
            conn = await asyncpg.connect(
                host=pg_host,
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                database=os.getenv("POSTGRES_DB", "kubepilot"),
                timeout=3.0
            )
            await conn.execute("""
                INSERT INTO audit_logs (incident_id, action, actor, details, timestamp)
                VALUES ($1, $2, $3, $4, NOW())
            """, feedback.incident_id, f"feedback_{feedback.verdict}", feedback.user, json.dumps(feedback.model_dump()))
            await conn.close()
            db_persisted = True
        except Exception as pg_err:
            logger.warning("postgres_audit_persist_failed", error=str(pg_err))

    # Log structlog event
    logger.info(
        "runbook_feedback",
        incident_id=feedback.incident_id,
        suggestion_id=feedback.suggestion_id,
        verdict=feedback.verdict,
        user=feedback.user,
        corrected_playbook=feedback.corrected_playbook,
        persisted_to_db=db_persisted
    )

    return {
        "status": "success",
        "verdict": feedback.verdict,
        "incident_id": feedback.incident_id,
        "message": f"Runbook feedback '{feedback.verdict}' committed to Hindsight Memory."
    }


@app.get("/memory/bank")
def get_memory_bank():
    """Returns all retained incidents from the Hindsight memory bank."""
    memories = get_all_memories()
    return {
        "bank_id": hindsight_memory.bank_id,
        "total_memories": len(memories),
        "memories": memories
    }


@app.post("/memory/seed-demo")
async def seed_memory_demo():
    """Triggers the seeding of realistic past incidents for demo purposes."""
    import seed_memory
    await seed_memory.seed()
    return {"status": "success", "message": "Demo memories seeded successfully"}

class DemoTriggerRequest(BaseModel):
    scenario: str

@app.post("/demo/reset")
async def demo_reset():
    """Clears fallback cache and re-seeds memory."""
    hindsight_memory._fallback_cache.clear()
    import seed_memory
    await seed_memory.seed()
    return {"status": "reset", "memories_seeded": len(seed_memory.INCIDENTS)}

@app.post("/demo/trigger", response_model=AnalysisResponse)
async def demo_trigger(request: DemoTriggerRequest):
    """Triggers an incident scenario diagnostic."""
    scenario_map = {
        "checkout_500": "checkout service returning 500 errors",
        "auth_oom": "auth-service pods crashing with OOMKilled status",
        "payment_timeout": "payment-service timeout calling upstream auth after 3s"
    }
    query = scenario_map.get(request.scenario, "system is returning 500 errors")
    target = "unknown-service"
    if request.scenario == "checkout_500": target = "checkout-service"
    elif request.scenario == "auth_oom": target = "auth-service"
    elif request.scenario == "payment_timeout": target = "payment-service"
    
    req = AnalysisRequest(
        query=query,
        target_service=target,
        source="demo_trigger"
    )
    
    response = await agent_workflow.run(req)
    save_analysis(req, response)
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting API Server on http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
