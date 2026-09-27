# Expected Judge Q&A & Rebuttals

**Q1: "Why use Redis Streams instead of Kafka?"**
*A1: "Kafka requires heavy JVM tuning and Zookeeper/Kraft overhead. For a control-plane SRE loop where ultra-low latency and minimal resource footprint are critical, Redis Streams provide perfect persistent append-only logs with consumer groups without the infrastructure bloat."*

**Q2: "How do you prevent the AI from destroying the cluster?"**
*A2: "Zero-Trust Architecture. The AI Decision Engine has ZERO access to the Kubernetes API. It only outputs a JSON payload to a Redis Stream. The Execution Engine consumes that payload, validates it against hardcoded safety constraints, and only executes whitelisted actions via a least-privilege Service Account."*

**Q3: "Why did you build your own UI instead of just using Grafana?"**
*A3: "Grafana is incredible for metrics, but we are building an actionable AI Governance product. We needed a Backend-for-Frontend (BFF) to aggregate AI decision confidence scores, human-in-the-loop approvals, and immutable audit logs into a single executive view. Grafana remains our backend telemetry visualization layer."*
