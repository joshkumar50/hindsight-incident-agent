$ErrorActionPreference = "Continue"

$deployments = @(
    "incident-engine", "dependency-engine", "ai-orchestrator", "execution-engine",
    "chaos-controller", "fault-injection-engine", "monitoring-engine", "audit-engine",
    "recovery-validation-service", "rollback-engine", "chaos-scenario-manager", "telemetry-collector"
)

Write-Host "Restarting consumers to recover streams..." -ForegroundColor Cyan
foreach ($d in $deployments) {
    kubectl rollout restart deployment $d -n incident-agent-system 2>&1 | Out-Null
}

Write-Host "Waiting 30 seconds for consumers to reconnect and create streams/groups..." -ForegroundColor Yellow
Start-Sleep 30

Write-Host "Verifying incident-engine logs for NOGROUP errors..." -ForegroundColor Cyan
kubectl logs -l app=incident-engine -n incident-agent-system --tail=5
