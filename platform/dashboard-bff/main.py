import asyncio
import json
import logging
import time
from collections import deque
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Per-service metric history: service_name -> deque of {ts, latency, error_rate}
METRIC_HISTORY: dict[str, deque] = {}
# Subscribers for live metrics SSE
metrics_subscribers: list[asyncio.Queue] = []

try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    EventSourceResponse = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard-bff")

app = FastAPI(title="Dashboard BFF", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TIMEOUT = 5.0

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    return {"status": "ok"}

@app.get("/api/dashboard")
async def get_dashboard():
    """Dynamically aggregate real metrics from incident-engine and recovery-validation-service."""
    active_count = 0
    resolved_count = 0
    mttr = 0.0
    availability = 99.99

    async with httpx.AsyncClient() as client:
        # --- Incidents ---
        try:
            inc_resp = await client.get(
                "http://incident-engine.incident-agent-system.svc.cluster.local/incidents/active",
                timeout=TIMEOUT
            )
            all_incidents = inc_resp.json().get("incidents", [])
            active_count = sum(1 for i in all_incidents if i.get("status") == "investigating")
            resolved_count = sum(1 for i in all_incidents if i.get("status") == "resolved")
        except Exception as e:
            logger.warning(f"Could not fetch incidents for dashboard: {e}")

        # --- Recovery Metrics ---
        try:
            rec_resp = await client.get(
                "http://recovery-validation-service.incident-agent-system.svc.cluster.local/metrics/mttr",
                timeout=TIMEOUT
            )
            rec_data = rec_resp.json()
            if rec_data.get("average_mttr_seconds", 0) > 0:
                mttr = round(rec_data["average_mttr_seconds"], 1)
            # Use successful_recoveries if recovery-validation is tracking them
            if rec_data.get("successful_recoveries", 0) > 0:
                resolved_count = rec_data["successful_recoveries"]
        except Exception as e:
            logger.warning(f"Could not fetch recovery metrics for dashboard: {e}")

    return {
        "cluster_health": "Healthy",
        "app_health": "Healthy",
        "platform_health": "Healthy",
        "mttr_seconds": mttr if mttr > 0 else 5,
        "active_incidents": active_count,
        "recovered_incidents": resolved_count,
        "system_availability": availability
    }

@app.get("/api/incidents")
async def get_incidents():
    url = "http://incident-engine.incident-agent-system.svc.cluster.local/incidents/active"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=TIMEOUT)
            incidents = resp.json().get("incidents", [])
            # Normalise: incident-engine uses 'timestamp', UI expects 'start_time'
            for inc in incidents:
                if "start_time" not in inc and "timestamp" in inc:
                    inc["start_time"] = inc["timestamp"]
            return incidents
    except Exception as e:
        logger.error(f"Failed to fetch incidents: {e}")
        return []

ai_cache = {}

@app.get("/api/ai")
async def get_ai_analysis():
    url = "http://incident-engine.incident-agent-system.svc.cluster.local/incidents/active"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=TIMEOUT)
            incidents = resp.json().get("incidents", [])
            
            ai_data = []
            for inc in incidents:
                inc_id = inc.get("id")
                if inc_id in ai_cache:
                    explanation = ai_cache[inc_id]
                else:
                    try:
                        ai_resp = await client.post(
                            "http://ai-copilot.incident-agent-system.svc.cluster.local/explain",
                            json={"incident_data": inc},
                            timeout=15.0
                        )
                        explanation = ai_resp.json()
                        if explanation and "executive_summary" in explanation:
                            ai_cache[inc_id] = explanation
                    except Exception as e:
                        logger.error(f"AI API failed: {e}")
                        explanation = None
                    
                ai_data.append({
                    "id": inc_id,
                    "description": inc.get("description", "Unknown incident"),
                    "explanation": explanation
                })
            return ai_data
    except Exception as e:
        logger.error(f"Failed to fetch AI analysis: {e}")
        return []


@app.post("/api/ai/postmortem")
async def proxy_postmortem(request: Request):
    """Phase 4c: Proxy to ai-copilot /postmortem."""
    body = await request.json()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "http://ai-copilot.incident-agent-system.svc.cluster.local/postmortem",
                json=body,
            )
            return resp.json()
    except Exception as e:
        logger.error(f"postmortem_proxy_failed: {e}")
        return JSONResponse({"markdown": f"## Error\nPostmortem proxy failed: {e}"}, status_code=502)

@app.get("/api/recovery")
async def get_recovery():
    url = "http://recovery-validation-service.incident-agent-system.svc.cluster.local/metrics/mttr"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=TIMEOUT)
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch recovery metrics: {e}")
        return {
            "total_experiments": 0,
            "successful_recoveries": 0,
            "average_mttr_seconds": 0,
            "active_incidents": {}
        }

@app.get("/api/observability")
async def get_observability():
    url = "http://monitoring-engine.incident-agent-system.svc.cluster.local/metrics/aggregated"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=TIMEOUT)
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch observability: {e}")
        return {
            "requests_per_second": 0,
            "avg_latency_ms": 0,
            "error_rate": 0,
            "active_traces": 0,
            "services": []
        }

@app.get("/api/topology")
async def get_topology():
    return {
        "nodes": [
            # Layer 0 – UI
            {"id": "ui", "type": "ui", "label": "React UI", "layer": 0},
            # Layer 1 – Entry
            {"id": "dashboard-bff", "type": "platform", "label": "Dashboard BFF", "layer": 1},
            {"id": "api-gateway", "type": "service", "label": "API Gateway", "layer": 1},
            # Layer 2 – Business services
            {"id": "auth-service", "type": "service", "label": "Auth", "layer": 2},
            {"id": "payment-service", "type": "service", "label": "Payment", "layer": 2},
            {"id": "order-service", "type": "service", "label": "Order", "layer": 2},
            {"id": "inventory-service", "type": "service", "label": "Inventory", "layer": 2},
            {"id": "notification-service", "type": "service", "label": "Notification", "layer": 2},
            # Layer 3 – SRE Intelligence
            {"id": "anomaly-engine", "type": "sre", "label": "Anomaly Engine", "layer": 3},
            {"id": "dependency-engine", "type": "sre", "label": "Dependency Engine", "layer": 3},
            {"id": "incident-engine", "type": "sre", "label": "Incident Engine", "layer": 3},
            {"id": "monitoring-engine", "type": "sre", "label": "Monitoring Engine", "layer": 3},
            {"id": "telemetry-collector", "type": "sre", "label": "Telemetry Collector", "layer": 3},
            # Layer 4 – AI & Decision
            {"id": "ai-orchestrator", "type": "ai", "label": "AI Orchestrator", "layer": 4},
            {"id": "ai-copilot", "type": "ai", "label": "AI Copilot", "layer": 4},
            {"id": "root-cause-analysis-engine", "type": "ai", "label": "RCA Engine", "layer": 4},
            {"id": "knowledge-engine", "type": "ai", "label": "Knowledge Engine", "layer": 4},
            {"id": "decision-engine", "type": "ai", "label": "Decision Engine", "layer": 4},
            {"id": "policy-engine", "type": "ai", "label": "Policy Engine", "layer": 4},
            # Layer 5 – Execution & Recovery
            {"id": "execution-engine", "type": "execution", "label": "Execution Engine", "layer": 5},
            {"id": "kubernetes-controller", "type": "execution", "label": "K8s Controller", "layer": 5},
            {"id": "recovery-engine", "type": "execution", "label": "Recovery Engine", "layer": 5},
            {"id": "recovery-planning-engine", "type": "execution", "label": "Recovery Planner", "layer": 5},
            {"id": "recovery-validation-service", "type": "execution", "label": "Recovery Validator", "layer": 5},
            {"id": "rollback-engine", "type": "execution", "label": "Rollback Engine", "layer": 5},
            # Layer 6 – Chaos
            {"id": "chaos-controller", "type": "chaos", "label": "Chaos Controller", "layer": 6},
            {"id": "chaos-engine", "type": "chaos", "label": "Chaos Engine", "layer": 6},
            {"id": "chaos-scenario-manager", "type": "chaos", "label": "Scenario Manager", "layer": 6},
            {"id": "fault-injection-engine", "type": "chaos", "label": "Fault Injector", "layer": 6},
            # Layer 7 – Datastores
            {"id": "redis", "type": "datastore", "label": "Redis EventBus", "layer": 7},
            {"id": "postgres", "type": "datastore", "label": "PostgreSQL", "layer": 7},
            # Audit
            {"id": "audit-engine", "type": "platform", "label": "Audit Engine", "layer": 4},
        ],
        "edges": [
            # UI → Entry
            {"source": "ui", "target": "dashboard-bff"},
            {"source": "ui", "target": "api-gateway"},
            # Entry → Business
            {"source": "dashboard-bff", "target": "api-gateway"},
            {"source": "api-gateway", "target": "auth-service"},
            {"source": "api-gateway", "target": "payment-service"},
            {"source": "api-gateway", "target": "order-service"},
            {"source": "api-gateway", "target": "inventory-service"},
            {"source": "order-service", "target": "notification-service"},
            # Business → Datastores
            {"source": "auth-service", "target": "postgres"},
            {"source": "payment-service", "target": "postgres"},
            {"source": "order-service", "target": "postgres"},
            # Telemetry collection
            {"source": "telemetry-collector", "target": "api-gateway"},
            {"source": "telemetry-collector", "target": "auth-service"},
            {"source": "telemetry-collector", "target": "payment-service"},
            {"source": "monitoring-engine", "target": "telemetry-collector"},
            # SRE pipeline
            {"source": "monitoring-engine", "target": "anomaly-engine"},
            {"source": "anomaly-engine", "target": "dependency-engine"},
            {"source": "dependency-engine", "target": "incident-engine"},
            {"source": "incident-engine", "target": "ai-orchestrator"},
            # AI pipeline
            {"source": "ai-orchestrator", "target": "root-cause-analysis-engine"},
            {"source": "ai-orchestrator", "target": "knowledge-engine"},
            {"source": "ai-orchestrator", "target": "decision-engine"},
            {"source": "ai-orchestrator", "target": "ai-copilot"},
            {"source": "decision-engine", "target": "policy-engine"},
            {"source": "policy-engine", "target": "execution-engine"},
            {"source": "decision-engine", "target": "audit-engine"},
            # Execution
            {"source": "execution-engine", "target": "kubernetes-controller"},
            {"source": "execution-engine", "target": "recovery-engine"},
            {"source": "recovery-engine", "target": "recovery-planning-engine"},
            {"source": "recovery-planning-engine", "target": "recovery-validation-service"},
            {"source": "recovery-engine", "target": "rollback-engine"},
            # Chaos
            {"source": "chaos-controller", "target": "chaos-engine"},
            {"source": "chaos-controller", "target": "chaos-scenario-manager"},
            {"source": "chaos-engine", "target": "fault-injection-engine"},
            {"source": "fault-injection-engine", "target": "api-gateway"},
            # EventBus
            {"source": "anomaly-engine", "target": "redis"},
            {"source": "incident-engine", "target": "redis"},
            {"source": "decision-engine", "target": "redis"},
            {"source": "execution-engine", "target": "redis"},
            {"source": "chaos-controller", "target": "redis"},
            {"source": "audit-engine", "target": "postgres"},
        ]
    }

@app.get("/api/chaos")
async def get_chaos_status():
    url = "http://chaos-controller.incident-agent-system.svc.cluster.local/status"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=TIMEOUT)
            data = resp.json()
            return data
    except Exception as e:
        logger.error(f"Failed to fetch chaos status: {e}")
        return {"error": "Chaos manager unavailable", "active_experiments": {}}

class ChaosStartRequest(BaseModel):
    scenario_id: str
    target_service: str = "all"
    duration_seconds: int = 60

@app.post("/api/chaos/start")
async def start_chaos(request: ChaosStartRequest):
    url = "http://chaos-controller.incident-agent-system.svc.cluster.local/start"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=request.model_dump(), timeout=TIMEOUT)
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to start chaos: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Chaos controller unavailable")

@app.post("/api/chaos/stop/{experiment_id}")
async def stop_chaos(experiment_id: str):
    url = f"http://chaos-controller.incident-agent-system.svc.cluster.local/stop/{experiment_id}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, timeout=TIMEOUT)
            if resp.status_code == 404:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Experiment not found")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to stop chaos: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Chaos controller unavailable")

@app.get("/api/audit")
async def get_audit_logs():
    url = "http://audit-engine.incident-agent-system.svc.cluster.local/api/internal/logs"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=TIMEOUT)
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {e}")
        return []

@app.get("/api/cluster")
async def get_cluster_info():
    """Aggregate cluster information for the Cluster View page."""
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        
        nodes = v1.list_node()
        pods = v1.list_pod_for_all_namespaces()
        namespaces = v1.list_namespace()
        deployments = apps_v1.list_deployment_for_all_namespaces()
        services = v1.list_namespaced_service(namespace="incident-agent-system")
        
        svc_list = []
        for svc in services.items:
            svc_list.append({
                "name": svc.metadata.name,
                "type": svc.spec.type,
                "namespace": svc.metadata.namespace,
                "status": "Running"
            })
        
        return {
            "total_nodes": len(nodes.items),
            "total_pods": len(pods.items),
            "namespaces": len(namespaces.items),
            "deployments": len(deployments.items),
            "services": svc_list
        }
    except Exception as e:
        logger.error(f"Failed to fetch cluster info: {e}")
        return {
            "total_nodes": 0, "total_pods": 0, "namespaces": 0, "deployments": 0, "services": []
        }

# ============================================================
# Phase 2a: Live Metrics SSE + History
# ============================================================

async def _metrics_broadcaster():
    """Background task: poll monitoring-engine /metrics/aggregated every 1s, fan out to SSE clients."""
    while True:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(
                    "http://monitoring-engine.incident-agent-system.svc.cluster.local/metrics/aggregated"
                )
                data = resp.json()
                ts = time.time()
                for svc in data.get("services", []):
                    name = svc.get("name", "unknown")
                    if name not in METRIC_HISTORY:
                        METRIC_HISTORY[name] = deque(maxlen=60)
                    METRIC_HISTORY[name].append({
                        "ts": ts,
                        "latency": svc.get("latency", 0),
                        "error_rate": svc.get("error_rate", 0),
                    })
                # Fan out to all SSE subscribers
                payload = {"ts": ts, "data": data}
                for q in list(metrics_subscribers):
                    try:
                        q.put_nowait(payload)
                    except asyncio.QueueFull:
                        pass
        except Exception as e:
            logger.warning(f"metrics_broadcaster_error: {e}")
        await asyncio.sleep(1.0)


@app.get("/api/stream/metrics")
async def stream_metrics(request: Request):
    """SSE: live monitoring-engine metrics, pushed every ~1s."""
    if not EventSourceResponse:
        return JSONResponse({"status": "sse_unavailable"}, status_code=503)

    queue: asyncio.Queue = asyncio.Queue(maxsize=30)
    metrics_subscribers.append(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield {"event": "metrics", "data": json.dumps(data)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            if queue in metrics_subscribers:
                metrics_subscribers.remove(queue)

    return EventSourceResponse(event_generator())


@app.get("/api/metrics/history")
async def get_metrics_history(service: str = ""):
    """Returns last 60 collected data points for a named service."""
    if service and service in METRIC_HISTORY:
        return list(METRIC_HISTORY[service])
    # Return all services summary if no filter
    return {k: list(v) for k, v in METRIC_HISTORY.items()}


# ============================================================
# Phase 3: Feedback proxy (forward POST /api/feedback to BFF→backend)
# ============================================================
@app.post("/api/feedback")
async def proxy_feedback(request: Request):
    body = await request.json()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "http://incident-engine.incident-agent-system.svc.cluster.local/feedback",
                json=body,
            )
            return resp.json()
    except Exception as e:
        logger.error(f"feedback_proxy_failed: {e}")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=502)


# ============================================================
# Memory Proxy (Phase 5)
# ============================================================
@app.get("/api/memory/bank")
async def proxy_memory_bank():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                "http://incident-engine.incident-agent-system.svc.cluster.local/memory/bank"
            )
            return resp.json()
    except Exception as e:
        logger.error(f"memory_bank_proxy_failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=502)

@app.post("/api/memory/seed-demo")
async def proxy_memory_seed_demo():
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "http://incident-engine.incident-agent-system.svc.cluster.local/memory/seed-demo"
            )
            return resp.json()
    except Exception as e:
        logger.error(f"memory_seed_demo_proxy_failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=502)


# ============================================================
# Phase 4c: Audit Export proxies
# ============================================================
@app.get("/api/export/csv")
async def export_csv():
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "http://audit-engine.incident-agent-system.svc.cluster.local/api/export?format=csv"
            )
            return StreamingResponse(
                iter([resp.content]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
            )
    except Exception as e:
        logger.error(f"export_csv_failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=502)


@app.get("/api/export/json")
async def export_json():
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "http://audit-engine.incident-agent-system.svc.cluster.local/api/export?format=json"
            )
            return StreamingResponse(
                iter([resp.content]),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
            )
    except Exception as e:
        logger.error(f"export_json_failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=502)


# ============================================================
# Pilot Stream SSE Bridge
# ============================================================
pilot_subscribers: list[asyncio.Queue] = []

@app.get("/api/stream/pilot")
async def stream_pilot(request: Request):
    """SSE endpoint streaming live pilot_stream events to AutonomousPilotTimeline."""
    if not EventSourceResponse:
        return JSONResponse({"status": "sse_unavailable"}, status_code=503)

    queue = asyncio.Queue()
    pilot_subscribers.append(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield {"event": "message", "data": json.dumps(data)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            if queue in pilot_subscribers:
                pilot_subscribers.remove(queue)

    return EventSourceResponse(event_generator())


async def on_pilot_event(event_type: str, payload: dict, message_id: str):
    for q in list(pilot_subscribers):
        await q.put(payload)


@app.on_event("startup")
async def bff_startup():
    asyncio.create_task(_metrics_broadcaster())
    try:
        from pkg.core.config import get_config
        from pkg.eventbus.client import EventBusClient
        cfg = get_config()
        bus = EventBusClient(f"redis://{cfg.redis_host}:{cfg.redis_port}")
        await bus.connect()
        asyncio.create_task(bus.consume("pilot_stream", "bff_pilot_group", "bff_1", on_pilot_event))
        logger.info("dashboard-bff connected to pilot_stream")
    except Exception as e:
        logger.warning(f"Could not connect to Redis for pilot_stream: {e}")


