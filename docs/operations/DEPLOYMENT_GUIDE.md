# Deployment Guide
- Use Helm for production deployments.
- Raw manifests in `infra/k8s/` can be used for debugging.
- Rollouts should proceed: Redis -> PostgreSQL -> Platform -> Apps.
