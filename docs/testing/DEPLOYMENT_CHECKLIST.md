# Production Deployment Checklist

## Pre-Flight
- [ ] Ensure K8s cluster has Calico or Cilium CNI installed for NetworkPolicies.
- [ ] Provision highly available Redis and PostgreSQL instances outside the cluster if possible.
- [ ] Inject `JWT_SECRET` and AI Provider API Keys into the `hindsight-agent-secrets` Vault.

## Deployment Phase
- [ ] `kubectl apply -f infra/k8s/namespaces.yaml`
- [ ] `kubectl apply -f infra/k8s/security/`
- [ ] `kubectl apply -f platform/`
- [ ] `kubectl apply -f apps/`

## Post-Flight
- [ ] Run `test_critical_paths.py` against production API Gateway.
- [ ] Execute Chaos Scenario 1 (Memory Leak) and verify auto-recovery within 60 seconds.
