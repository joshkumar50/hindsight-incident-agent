# Known Limitations

## Current Constraints
1. **AI Hallucination Risk**: The `decision-engine` currently relies on LLM output. While confidence scores are tracked, unforeseen Kubernetes states may result in suboptimal recovery recommendations. Human-in-the-loop is advised for initial rollout.
2. **PostgreSQL Single Point of Failure**: The `audit-engine` logs directly to a single PostgreSQL instance. In a true enterprise environment, this needs to be a highly available cluster.
3. **Environment Dependency**: `network-policies.yaml` requires a compatible CNI (like Calico) running on the cluster to actually enforce the traffic blocking.
