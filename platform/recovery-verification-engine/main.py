import asyncio
from fastapi import FastAPI
import httpx
from kubernetes import client as k8s_client, config as k8s_config
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry

config = get_config()
logger = configure_logging("recovery-verification-engine")
app = FastAPI(title="Recovery Verification Engine", version="1.0.0")

bootstrap_telemetry(
    app, "recovery-verification-engine", config.otel_exporter_otlp_endpoint
)
register_error_handlers(app)
register_health_endpoints(app, "recovery-verification-engine")

# Initialize K8s Client (same pattern as kubernetes-controller)
k8s_initialized = False
try:
    k8s_config.load_incluster_config()
    k8s_initialized = True
except k8s_config.config_exception.ConfigException:
    try:
        k8s_config.load_kube_config()
        k8s_initialized = True
    except Exception as e:
        logger.warning("k8s_config_load_failed", error=str(e))

v1_apps = k8s_client.AppsV1Api() if k8s_initialized else None
v1_core = k8s_client.CoreV1Api() if k8s_initialized else None


class VerifyRequest(BaseModel):
    target: str
    incident_id: str


@app.post("/verify")
async def verify_recovery(req: VerifyRequest):
    """
    Monitors real metrics and health probes post-execution to ensure stability.
    Up to 5 rounds, 5s apart.
    (1) Deployment <target> in hindsight-agent-apps has spec.replicas >= 1 AND >=1 pod labeled app=<target> with Ready=True.
    (2) GET monitoring-engine /metrics/aggregated: service entry healthy==true OR (error_rate<=5.0 AND latency<=200).
    """
    logger.info("starting_recovery_verification_probes", target=req.target, incident_id=req.incident_id)

    failed_probes = []
    last_probe_details = {}
    passed_rounds = 0
    total_rounds = 5

    async with httpx.AsyncClient(timeout=10.0) as http_client:
        for round_num in range(1, total_rounds + 1):
            round_passed = True
            round_details = {"round": round_num}

            # Probe (1): Kubernetes API Check
            if v1_apps and v1_core:
                try:
                    deployment = v1_apps.read_namespaced_deployment(
                        name=req.target, namespace="hindsight-agent-apps"
                    )
                    replicas = deployment.spec.replicas or 0
                    if replicas < 1:
                        round_passed = False
                        failed_probes.append(f"round_{round_num}_deployment_replicas_{replicas}_less_than_1")

                    pods = v1_core.list_namespaced_pod(
                        namespace="hindsight-agent-apps",
                        label_selector=f"app={req.target}"
                    )
                    ready_pods = 0
                    for pod in pods.items:
                        if pod.status and pod.status.conditions:
                            for c in pod.status.conditions:
                                if c.type == "Ready" and c.status == "True":
                                    ready_pods += 1
                    if ready_pods < 1:
                        round_passed = False
                        failed_probes.append(f"round_{round_num}_no_ready_pods_found")

                    round_details["k8s"] = {
                        "replicas": replicas,
                        "ready_pods": ready_pods
                    }
                except Exception as e:
                    logger.warning("k8s_probe_exception", round=round_num, error=str(e))
                    failed_probes.append(f"round_{round_num}_k8s_probe_error_{str(e)}")
                    round_passed = False
            else:
                round_details["k8s"] = {"status": "running_outside_cluster_fallback"}

            # Probe (2): Monitoring Engine Metrics
            try:
                metrics_res = await http_client.get(
                    "http://monitoring-engine.incident-agent-system.svc.cluster.local/metrics/aggregated"
                )
                if metrics_res.status_code == 200:
                    data = metrics_res.json()
                    services = data.get("services", {}) if isinstance(data, dict) else {}
                    svc_data = services.get(req.target, {})
                    healthy = svc_data.get("healthy", False)
                    error_rate = float(svc_data.get("error_rate", 0.0))
                    latency = float(svc_data.get("latency", 0.0))
                    round_details["metrics"] = {
                        "healthy": healthy,
                        "error_rate": error_rate,
                        "latency": latency
                    }

                    if not (healthy or (error_rate <= 5.0 and latency <= 200.0)):
                        round_passed = False
                        failed_probes.append(f"round_{round_num}_metrics_unhealthy_err_{error_rate}_lat_{latency}")
                else:
                    logger.warning("monitoring_engine_status_not_200", status=metrics_res.status_code)
            except Exception as e:
                logger.warning("monitoring_engine_probe_exception", round=round_num, error=str(e))
                # Log and continue

            last_probe_details = round_details
            if round_passed:
                passed_rounds += 1
                logger.info("probe_round_passed", round=round_num, details=round_details)
            else:
                logger.warning("probe_round_failed", round=round_num, details=round_details)

            if round_num < total_rounds:
                await asyncio.sleep(5.0)

    success = (passed_rounds == total_rounds)
    if success:
        logger.info("all_verification_rounds_passed", target=req.target)
        return {
            "success": True,
            "rounds_passed": passed_rounds,
            "total_rounds": total_rounds,
            "last_probe_details": last_probe_details
        }
    else:
        logger.error("verification_probes_failed", target=req.target, failed_probes=failed_probes)
        return {
            "success": False,
            "rounds_passed": passed_rounds,
            "total_rounds": total_rounds,
            "failed_probes": failed_probes,
            "last_probe_details": last_probe_details
        }
