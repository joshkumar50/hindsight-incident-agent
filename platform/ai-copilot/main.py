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

    # Using Groq API for lightning fast inference
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                GROQ_API_URL,
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'Content-Type': 'application/json'
                },
                timeout=15.0
            )
            res.raise_for_status()
            content = res.json()["choices"][0]["message"]["content"]
            
            try:
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Groq response as JSON: {content}")
                return {
                    "executive_summary": "Failed to parse AI response.",
                    "technical_summary": content,
                    "postmortem": ""
                }
                
    except Exception as e:
        logger.error(f"groq_api_failed: {str(e)}")
        return {
            "executive_summary": "Groq AI generation failed.",
            "technical_summary": str(e),
            "postmortem": "Please ensure the Groq API key is valid and network is accessible."
        }
