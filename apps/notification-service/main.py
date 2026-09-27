"""
Phase 3 — Slack ChatOps upgrade for notification-service.
Keeps the existing order_events consumer intact.
Adds:
  - Slack Block Kit alerts via SLACK_WEBHOOK_URL
  - Consumers for ai_stream, recovery_stream, pilot_stream
  - POST /slack/interactive for approve_fix / enable_auto
  - GET /slack/status
"""
import asyncio
import json
import os
import urllib.parse

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from pkg.core.config import get_config
from pkg.core.logging import configure_logging
from pkg.core.health import register_health_endpoints
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("notification-service")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
REDIS_URL = f"redis://{config.redis_host}:{config.redis_port}"

event_bus = EventBusClient(REDIS_URL)

app = FastAPI(title="Notification Service")
register_health_endpoints(app, "notification-service")


# ============================================================
# Slack helpers
# ============================================================

async def post_slack(blocks: list) -> None:
    """Send a Slack Block Kit message. No-op if SLACK_WEBHOOK_URL is unset."""
    if not SLACK_WEBHOOK_URL:
        logger.info("slack_disabled", reason="SLACK_WEBHOOK_URL not set")
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(SLACK_WEBHOOK_URL, json={"blocks": blocks})
            resp.raise_for_status()
    except Exception as e:
        logger.warning("slack_post_failed", error=str(e))


# ============================================================
# Existing: Order Events
# ============================================================

async def handle_order_event(event_type: str, payload: dict, message_id: str):
    logger.info(
        "received_event", event_type=event_type, payload=payload, message_id=message_id
    )
    if event_type == "ORDER_PLACED":
        logger.info("sending_email", order_id=payload.get("order_id"))
        await asyncio.sleep(0.5)  # Simulate email send time
        logger.info("email_sent")


# ============================================================
# Phase 3a: ai_stream consumer — INCIDENT_DECLARED
# ============================================================

async def handle_ai_event(event_type: str, payload: dict, message_id: str):
    if event_type == "INCIDENT_DECLARED":
        incident_id = payload.get("incident_id", "N/A")
        root_cause = payload.get("root_cause", "Pending RCA")
        impacted = ", ".join(payload.get("impacted_services", []) or [])
        logger.info("incident_declared_slack_notify", incident_id=incident_id)

        await post_slack([
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 SEV-1 INCIDENT DECLARED", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident ID:*\n`{incident_id}`"},
                    {"type": "mrkdwn", "text": f"*Root Cause:*\n{root_cause}"},
                    {"type": "mrkdwn", "text": f"*Impacted Services:*\n{impacted or 'Unknown'}"},
                    {"type": "mrkdwn", "text": "*Status:*\nAutonomous Pilot Diagnosing"},
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Approve Fix", "emoji": True},
                        "action_id": "approve_fix",
                        "value": incident_id,
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "⚡ Enable Full Autonomous Mode", "emoji": True},
                        "action_id": "enable_auto",
                        "value": incident_id,
                        "style": "danger",
                    }
                ]
            }
        ])


# ============================================================
# Phase 3a: recovery_stream consumer — RECOVERY_COMPLETED
# ============================================================

async def handle_recovery_event(event_type: str, payload: dict, message_id: str):
    if event_type == "RECOVERY_COMPLETED":
        incident_id = payload.get("incident_id", "N/A")
        target = payload.get("target", "unknown-service")
        logger.info("recovery_completed_slack_notify", incident_id=incident_id)

        # Fetch MTTR from recovery-validation-service
        mttr_text = "N/A"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                mttr_resp = await client.get(
                    "http://recovery-validation-service.incident-agent-system.svc.cluster.local/metrics/mttr"
                )
                mttr_data = mttr_resp.json()
                mttr_text = f"{mttr_data.get('average_mttr_seconds', 'N/A')}s"
        except Exception as e:
            logger.warning("mttr_fetch_failed", error=str(e))

        await post_slack([
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Incident Resolved — System Stabilized", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident ID:*\n`{incident_id}`"},
                    {"type": "mrkdwn", "text": f"*Target Service:*\n{target}"},
                    {"type": "mrkdwn", "text": f"*MTTR:*\n{mttr_text}"},
                    {"type": "mrkdwn", "text": "*Result:*\nAutonomously healed ✓"},
                ]
            }
        ])


# ============================================================
# Phase 3a: pilot_stream consumer — phase transitions
# ============================================================

async def handle_pilot_event(event_type: str, payload: dict, message_id: str):
    phase = payload.get("phase", event_type)
    incident_id = payload.get("incident_id", "N/A")
    target = payload.get("target", "")
    phase_emoji = {
        "DIAGNOSING": "🔍", "APPLYING_FIX": "🔧",
        "VERIFYING_HEALTH": "📡", "STABILIZED": "🟢",
        "ROLLBACK_REQUIRED": "⚠️", "ROLLBACK_EXECUTED": "🔄",
        "APPROVAL_GRANTED": "✅",
    }.get(phase, "ℹ️")
    await post_slack([
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{phase_emoji} *Pilot Phase:* `{phase}` — Incident `{incident_id}` on `{target}`"}
        }
    ])


# ============================================================
# Phase 3a: POST /slack/interactive
# ============================================================

@app.post("/slack/interactive")
async def slack_interactive(request: Request):
    """
    Receives Slack interactive payload (button clicks).
    approve_fix → publish ai_stream PLAN_APPROVED
    enable_auto → Redis SET config:autonomous_mode full EX 86400
    """
    body = await request.body()
    form_data = urllib.parse.parse_qs(body.decode())
    raw_payload = form_data.get("payload", ["{}"])[0]
    try:
        slack_payload = json.loads(raw_payload)
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid_payload"}, status_code=400)

    for action in slack_payload.get("actions", []):
        action_id = action.get("action_id")
        incident_id = action.get("value", "unknown")
        user = slack_payload.get("user", {}).get("name", "slack-operator")

        if action_id == "approve_fix":
            logger.info("slack_approve_fix", incident_id=incident_id, user=user)
            await event_bus.publish(
                "ai_stream",
                "PLAN_APPROVED",
                {"incident_id": incident_id, "approved_by": "slack", "user": user}
            )

        elif action_id == "enable_auto":
            logger.info("slack_enable_full_autonomy", incident_id=incident_id, user=user)
            try:
                if event_bus.redis:
                    await event_bus.redis.set("config:autonomous_mode", "full", ex=86400)
            except Exception as e:
                logger.warning("redis_set_autonomous_mode_failed", error=str(e))

    return JSONResponse({"ok": True})


# ============================================================
# Phase 3a: GET /slack/status
# ============================================================

@app.get("/slack/status")
async def slack_status():
    return {
        "webhook_configured": bool(SLACK_WEBHOOK_URL),
        "interactive_url": os.getenv("SLACK_INTERACTIVE_URL", "Not configured"),
    }


# ============================================================
# Startup: wire all consumers
# ============================================================

@app.on_event("startup")
async def startup_event():
    logger.info("Notification Service starting...")
    await event_bus.connect()

    asyncio.create_task(event_bus.consume(
        stream="order_events",
        group="notification_group",
        consumer="notifier_1",
        callback=handle_order_event,
    ))
    asyncio.create_task(event_bus.consume(
        stream="ai_stream",
        group="notification_ai_group",
        consumer="notifier_ai_1",
        callback=handle_ai_event,
    ))
    asyncio.create_task(event_bus.consume(
        stream="recovery_stream",
        group="notification_recovery_group",
        consumer="notifier_rec_1",
        callback=handle_recovery_event,
    ))
    asyncio.create_task(event_bus.consume(
        stream="pilot_stream",
        group="notification_pilot_group",
        consumer="notifier_pilot_1",
        callback=handle_pilot_event,
    ))
    logger.info("Notification Service started with Slack ChatOps consumers")
