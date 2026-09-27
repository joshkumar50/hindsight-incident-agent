import json
import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry

config = get_config()
logger = configure_logging("ai-copilot")
app = FastAPI(title="AI Copilot", version="1.0.0")

bootstrap_telemetry(app, "ai-copilot", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "ai-copilot")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

class IncidentReportRequest(BaseModel):
    incident_data: dict

@app.post("/explain")
async def generate_explanation(request: IncidentReportRequest):
    """
    Uses the Google Gemini API for real natural language explanation and postmortems.
    """
    logger.info("generating_copilot_explanation_via_gemini")

    prompt = f"""
    You are an expert Kubernetes SRE. Summarize this incident for an executive.
    Data: {request.incident_data}
    
    You MUST return YOUR ENTIRE RESPONSE as a single valid JSON object with EXACTLY these three keys:
    "executive_summary": A concise 2-3 sentence paragraph summarizing the incident and impact. (MUST be a String)
    "technical_summary": A technical paragraph explaining the root cause and affected components. (MUST be a String)
    "postmortem": Next steps and recommendations for preventing this in the future. (MUST be a String)
    
    CRITICAL: The values for all three keys MUST be simple text strings. Do NOT output nested JSON arrays or objects as values.
    Do NOT include any markdown formatting like \\\json or anything outside the JSON object.
    """

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not found! Falling back to mock response.")
        rca = request.incident_data.get("root_cause", "unknown service")
        desc = request.incident_data.get("description", "Anomalous behavior detected.")
        services = ", ".join(request.incident_data.get("impacted_services", []))
        return {
            "executive_summary": f"[MOCK] Incident triggered by {rca}. The AI Orchestrator mitigated the issue.",
            "technical_summary": f"[MOCK] Metrics indicated {desc} Impact extended to {services}.",
            "postmortem": "[MOCK] No GEMINI_API_KEY configured."
        }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                GEMINI_API_URL,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                },
                headers={'Content-Type': 'application/json'},
                timeout=15.0
            )
            res.raise_for_status()
            content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            
            try:
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Gemini response as JSON: {content}")
                return {
                    "executive_summary": "Failed to parse AI response.",
                    "technical_summary": content,
                    "postmortem": ""
                }
                
    except Exception as e:
        logger.error(f"gemini_api_failed: {str(e)}")
        return {
            "executive_summary": "AI generation failed.",
            "technical_summary": str(e),
            "postmortem": "Please check Gemini API key and network connectivity."
        }


# ============================================================
# Phase 4a: POST /postmortem
# ============================================================
class PostmortemRequest(BaseModel):
    incident_id: str


@app.post("/postmortem")
async def generate_postmortem(request: PostmortemRequest):
    """
    Gathers audit-engine logs + incident-engine incident data + pilot_stream XREVRANGE history,
    then prompts Gemini to produce a structured markdown postmortem.
    Falls back to a rich mock markdown when GEMINI_API_KEY is absent.
    """
    incident_id = request.incident_id
    logger.info("generating_postmortem", incident_id=incident_id)

    audit_logs = []
    incident_data = {}
    pilot_history = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Collect audit logs
        try:
            res = await client.get(
                "http://audit-engine.incident-agent-system.svc.cluster.local/api/internal/logs",
                params={"limit": 50}
            )
            audit_logs = [l for l in res.json() if l.get("incident_id") == incident_id]
        except Exception as e:
            logger.warning("postmortem_audit_fetch_failed", error=str(e))

        # Collect incident data
        try:
            res = await client.get(
                "http://incident-engine.incident-agent-system.svc.cluster.local/incidents/active"
            )
            incidents = res.json().get("incidents", [])
            incident_data = next((i for i in incidents if i.get("id") == incident_id), {})
        except Exception as e:
            logger.warning("postmortem_incident_fetch_failed", error=str(e))

    # Build pilot timeline from audit logs
    pilot_events = [
        l for l in audit_logs
        if l.get("event_type", "").startswith(("DIAGNOSING", "APPLYING", "VERIFYING", "STABILIZED", "ROLLBACK"))
    ]

    timeline_md = "\n".join(
        f"- **{l.get('event_type', 'EVENT')}** at {l.get('timestamp', 'N/A')}"
        for l in pilot_events
    ) or "- No pilot events recorded"

    context = {
        "incident_id": incident_id,
        "description": incident_data.get("description", "Unknown incident"),
        "root_cause": incident_data.get("root_cause", "Pending analysis"),
        "impacted_services": incident_data.get("impacted_services", []),
        "audit_events_count": len(audit_logs),
        "timeline_summary": timeline_md,
    }

    prompt = f"""
You are a senior SRE writing a production postmortem. Output ONLY a JSON object with key "markdown".
The markdown value must contain:
## Timeline
(chronological events from: {context['timeline_summary']})
## Root Cause Analysis
(explain root cause: {context['root_cause']})
## Remediation Steps
(what was done automatically by the autonomous pilot)
## Preventative Recommendations
(3-5 actionable steps to prevent recurrence)

Context: {json.dumps(context)}
Return ONLY: {{"markdown": "..."}}
"""

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not found, returning mock postmortem")
        mock_md = f"""## Timeline
{timeline_md}

## Root Cause Analysis
{context['root_cause']}

## Remediation Steps
The Autonomous SRE Pilot detected, diagnosed, and applied a fix for `{incident_id}` targeting `{', '.join(context['impacted_services']) or 'unknown services'}`.

## Preventative Recommendations
1. Add resource limits to all deployments in the `hindsight-agent-apps` namespace.
2. Configure HPA (Horizontal Pod Autoscaler) for critical services.
3. Implement circuit breakers on inter-service HTTP calls.
4. Set up PagerDuty alerting on error rate > 2% sustained 5m.
5. Schedule monthly chaos engineering exercises to validate autonomous healing.
"""
        return {"markdown": mock_md}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                GEMINI_API_URL,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
                },
                headers={"Content-Type": "application/json"},
            )
            res.raise_for_status()
            content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(content)
            return {"markdown": parsed.get("markdown", content)}
    except Exception as e:
        logger.error(f"postmortem_gemini_failed: {e}")
        return {"markdown": f"## Error\nPostmortem generation failed: {e}"}

