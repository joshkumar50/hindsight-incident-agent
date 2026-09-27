# Installation Guide
1. `kubectl create namespace incident-agent-system`
2. `kubectl create namespace hindsight-agent-apps`
3. Deploy PostgreSQL and Redis: `helm install data-tier infra/helm/data/`
4. Deploy Hindsight Incident Agent: `helm install hindsight_agent infra/helm/hindsight-agent/`
