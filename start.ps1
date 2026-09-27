# ============================================================
#  Hindsight Incident Agent - One-Shot Startup Script
#  Usage:
#    .\start.ps1              - Normal start (uses Docker cache)
#    .\start.ps1 -SkipBuild   - Fastest (~30s), no Docker builds
#    .\start.ps1 -Rebuild     - Full clean rebuild (10+ min)
# ============================================================
param(
    [switch]$Rebuild,
    [switch]$SkipBuild
)
$ErrorActionPreference = "Continue"

function Step($msg)  { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function OK($msg)    { Write-Host "    [OK] $msg" -ForegroundColor Green }
function WARN($msg)  { Write-Host "    [!!] $msg" -ForegroundColor Yellow }

# ?? 1. Start Minikube ?????????????????????????????????????????????????
Step "Starting Minikube..."
$mk = (minikube status --format "{{.Host}}" 2>$null)
if ($mk -ne "Running") {
    minikube start --driver=docker | Out-Null
    OK "Minikube started"
} else {
    OK "Minikube already running"
}

# ?? 2. Configure Docker ? Minikube daemon ?????????????????????????????
Step "Configuring Docker..."
& minikube -p minikube docker-env | Invoke-Expression
OK "Docker environment set"

# ?? 3. Build images (only changed layers rebuild automatically) ????????
if (-not $SkipBuild) {
    Step "Building Docker images (Docker cache reused automatically)..."
    Write-Host "    Building hindsight_agent-python-base:latest..." -ForegroundColor Gray
    if ($Rebuild) { docker build --no-cache -f scripts/Dockerfile.python.base -t hindsight_agent-python-base:latest . 2>&1 | Out-Null }
    else          { docker build             -f scripts/Dockerfile.python.base -t hindsight_agent-python-base:latest . 2>&1 | Out-Null }
    
    $images = @(
        @{ tag="hindsight-agent/dashboard-bff:latest";    df="platform/dashboard-bff/Dockerfile";    arg="platform/dashboard-bff" },
        @{ tag="hindsight-agent/ai-copilot:latest";       df="platform/ai-copilot/Dockerfile";       arg="platform/ai-copilot" },
        @{ tag="hindsight-agent/chaos-controller:latest"; df="platform/chaos-controller/Dockerfile"; arg="platform/chaos-controller" },
        @{ tag="hindsight-agent/incident-engine:latest";  df="platform/incident-engine/Dockerfile";  arg="platform/incident-engine" },
        @{ tag="hindsight-agent/decision-engine:latest";  df="platform/decision-engine/Dockerfile";  arg="platform/decision-engine" },
        @{ tag="hindsight-agent/fault-injection-engine:latest"; df="platform/fault-injection-engine/Dockerfile"; arg="platform/fault-injection-engine" },
        @{ tag="hindsight-agent/dependency-engine:latest"; df="platform/dependency-engine/Dockerfile"; arg="platform/dependency-engine" },
        @{ tag="hindsight-agent/ai-orchestrator:latest"; df="platform/ai-orchestrator/Dockerfile"; arg="platform/ai-orchestrator" },
        @{ tag="hindsight-agent/audit-engine:latest"; df="platform/audit-engine/Dockerfile"; arg="platform/audit-engine" },
        @{ tag="hindsight-agent/execution-engine:latest"; df="platform/execution-engine/Dockerfile"; arg="platform/execution-engine" },
        @{ tag="hindsight-agent/knowledge-engine:latest"; df="platform/knowledge-engine/Dockerfile"; arg="platform/knowledge-engine" },
        @{ tag="hindsight-agent/kubernetes-controller:latest"; df="platform/kubernetes-controller/Dockerfile"; arg="platform/kubernetes-controller" },
        @{ tag="hindsight-agent/policy-engine:latest"; df="platform/policy-engine/Dockerfile"; arg="platform/policy-engine" },
        @{ tag="hindsight-agent/recovery-planning-engine:latest"; df="platform/recovery-planning-engine/Dockerfile"; arg="platform/recovery-planning-engine" },
        @{ tag="hindsight-agent/recovery-validation-service:latest"; df="platform/recovery-validation-service/Dockerfile"; arg="platform/recovery-validation-service" },
        @{ tag="hindsight-agent/recovery-verification-engine:latest"; df="platform/recovery-verification-engine/Dockerfile"; arg="platform/recovery-verification-engine" },
        @{ tag="hindsight-agent/root-cause-analysis-engine:latest"; df="platform/root-cause-analysis-engine/Dockerfile"; arg="platform/root-cause-analysis-engine" },
        @{ tag="hindsight-agent/ui:latest"; df="ui/Dockerfile"; arg="ui" }
    )
    foreach ($img in $images) {
        if (Test-Path $img.df) {
            Write-Host "    Building $($img.tag)..." -ForegroundColor Gray
            if ($Rebuild) { docker build --no-cache --build-arg dir=$($img.arg) -f $img.df -t $img.tag . 2>&1 | Out-Null }
            else          { docker build             --build-arg dir=$($img.arg) -f $img.df -t $img.tag . 2>&1 | Out-Null }
            if ($LASTEXITCODE -eq 0) { OK $img.tag } else { WARN "Build failed: $($img.tag)" }
        }
    }
} else {
    OK "Skipped Docker builds (-SkipBuild)"
}

# ?? 4. Apply correct nginx ConfigMap (permanent fix, idempotent) ???????
Step "Applying nginx config (api-gateway)..."
kubectl create configmap api-gateway-config `
    --from-file=nginx.conf=platform/api-gateway/nginx.conf `
    -n incident-agent-system --dry-run=client -o yaml | kubectl apply -f - 2>&1 | Out-Null
OK "nginx.conf applied"

# ?? 5. Rollout updated pods ????????????????????????????????????????????
if (-not $SkipBuild) {
    Step "Rolling out updated pods..."
    $deployments = @(
        "chaos-controller", "ai-copilot", "dashboard-bff", "incident-engine", 
        "decision-engine", "api-gateway", "ai-orchestrator", "audit-engine", 
        "execution-engine", "knowledge-engine", "kubernetes-controller", 
        "policy-engine", "recovery-planning-engine", "recovery-validation-service", 
        "recovery-verification-engine", "root-cause-analysis-engine", "ui", "dependency-engine", "fault-injection-engine"
    )
    foreach ($d in $deployments) {
        kubectl rollout restart deployment $d -n incident-agent-system 2>&1 | Out-Null
    }
    OK "Rollouts triggered ? waiting for api-gateway..."
    $ready = $false; $tries = 0
    while (-not $ready -and $tries -lt 20) {
        Start-Sleep 3
        $r = kubectl get deploy api-gateway -n incident-agent-system -o jsonpath='{.status.readyReplicas}' 2>$null
        if ($r -ge 1) { $ready = $true }; $tries++
    }
    OK "api-gateway ready"
}

# ?? 6. Self-healing port-forward watchdog ?????????????????????????????
Step "Starting self-healing port-forwards (UI :56115, API :58663)..."

# Kill any previous watchdog jobs
Get-Job | Where-Object { $_.Name -like "kube-watchdog*" } | Remove-Job -Force -ErrorAction SilentlyContinue

# Watchdog function ? restarts the port-forward if it dies
$watchdogScript = {
    param($svc, $localPort, $ns)
    while ($true) {
        $proc = Start-Process -FilePath "kubectl" `
            -ArgumentList "port-forward","svc/$svc","${localPort}:80","-n","$ns" `
            -PassThru -NoNewWindow
        $proc.WaitForExit()
        Start-Sleep 2   # Brief pause before auto-restart
    }
}

Start-Job -Name "kube-watchdog-ui"  -ScriptBlock $watchdogScript -ArgumentList "ui",        56115, "incident-agent-system" | Out-Null
Start-Job -Name "kube-watchdog-api" -ScriptBlock $watchdogScript -ArgumentList "api-gateway",58663, "incident-agent-system" | Out-Null
Start-Sleep 3
OK "Port-forwards running with auto-restart watchdog"

# ?? 7. Verify ??????????????????????????????????????????????????????????
Step "Verifying endpoints..."
$uiOK  = (Invoke-WebRequest -Uri "http://127.0.0.1:56115"               -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue)
$apiOK = (Invoke-WebRequest -Uri "http://localhost:58663/api/dashboard"  -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue)
if ($uiOK)  { OK "UI  -> http://127.0.0.1:56115 (HTTP $($uiOK.StatusCode))" }  else { WARN "UI not responding yet - try refreshing in 10s" }
if ($apiOK) { OK "API -> http://localhost:58663/api/dashboard (HTTP $($apiOK.StatusCode))" } else { WARN "API not responding yet" }

# ?? 8. Pod summary ????????????????????????????????????????????????????
Step "Pod summary..."
$total   = (kubectl get pods -A --no-headers 2>$null | Measure-Object -Line).Lines
$running = (kubectl get pods -A --no-headers 2>$null | Select-String "Running" | Measure-Object -Line).Lines
if ($running -ge $total * 0.9) { OK "$running/$total pods Running" } else { WARN "$running/$total pods Running (some may still be starting)" }

# ?? Final banner ??????????????????????????????????????????????????????
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Hindsight Incident Agent is LIVE!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "  UI Dashboard  :  http://127.0.0.1:56115" -ForegroundColor White
Write-Host "  API Gateway   :  http://localhost:58663/api/dashboard" -ForegroundColor White
Write-Host "  Port-forwards :  Self-healing (auto-restart on crash)" -ForegroundColor White
Write-Host ""
Write-Host "  .\start.ps1 -SkipBuild   <- Fastest restart (30s)" -ForegroundColor Gray
Write-Host "  .\start.ps1              <- Normal restart (2-3 min)" -ForegroundColor Gray
Write-Host "  .\start.ps1 -Rebuild     <- Full clean rebuild" -ForegroundColor Gray
Write-Host "  python verify_all.py     <- Verify all APIs" -ForegroundColor Gray
Write-Host ""

