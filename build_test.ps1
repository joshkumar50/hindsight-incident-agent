$ErrorActionPreference = "Continue"

Write-Host "Building base image..."
docker build -f scripts/Dockerfile.python.base -t hindsight_agent-python-base:latest . > base_build.log 2>&1
$base_exit = $LASTEXITCODE
Write-Host "Base Image Exit Code: $base_exit"

Write-Host "Building test-bff..."
docker build -f platform/dashboard-bff/Dockerfile -t test-bff . > bff_build.log 2>&1
$bff_exit = $LASTEXITCODE

Write-Host "Building test-audit..."
docker build -f platform/audit-engine/Dockerfile -t test-audit . > audit_build.log 2>&1
$audit_exit = $LASTEXITCODE

Write-Host "Building test-k8s..."
docker build -f platform/kubernetes-controller/Dockerfile -t test-k8s . > k8s_build.log 2>&1
$k8s_exit = $LASTEXITCODE

Write-Host "--- Results ---"
Write-Host "BFF Exit Code: $bff_exit"
Write-Host "Audit Exit Code: $audit_exit"
Write-Host "K8s Exit Code: $k8s_exit"

Write-Host "--- BFF Last 20 Lines ---"
Get-Content bff_build.log | Select-Object -Last 20
Write-Host "--- Audit Last 20 Lines ---"
Get-Content audit_build.log | Select-Object -Last 20
Write-Host "--- K8s Last 20 Lines ---"
Get-Content k8s_build.log | Select-Object -Last 20
