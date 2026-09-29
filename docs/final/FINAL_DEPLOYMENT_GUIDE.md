# Final Deployment Guide

1. **Pre-requisites**: A running Kubernetes cluster (v1.24+) with Calico/Cilium CNI installed.
2. **Data Tier**: Deploy Redis and PostgreSQL.
3. **Platform Tier**: `helm install hindsight-agent infra/helm/hindsight-agent/`
4. **Validation**: Run `test_critical_paths.py` against the API Gateway Ingress.
