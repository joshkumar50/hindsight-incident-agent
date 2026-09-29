# Hindsight Incident Agent — Autonomous SRE Platform Architecture

This document holds the official architecture specification for Hindsight Incident Agent — Autonomous SRE Platform.

## 1. Top Level Architecture
Event-driven architecture with React Dashboard -> API Gateway -> Core APIs -> Redis Event Bus -> Autonomous SRE Engines (Anomaly, Dependency, Incident, AI, Decision, Recovery).

## 2. Microservices
- **Target Apps**: `auth-service`, `payment-service`, `order-service`, `inventory-service`, `notification-service`, `traffic-generator`
- **Platform**: `api-gateway`, `telemetry-collector`, `monitoring-engine`, `anomaly-engine`, `dependency-engine`, `incident-engine`, `audit-engine`
- **Autonomous AI Platform**: `ai-orchestrator`, `root-cause-analysis-engine`, `knowledge-engine`, `decision-engine`, `recovery-planning-engine`, `ai-copilot`
- **Execution Platform**: `execution-engine`, `policy-engine`, `kubernetes-controller`, `recovery-verification-engine`, `rollback-engine`
## 3. Communication
Redis Streams are used for at-least-once, persistent event delivery between SRE engines.
Synchronous HTTP is only used in the target `apps/` microservice data plane.

## 4. Databases
- PostgreSQL: Relational storage (Audit, Incident tracking)
- Redis: Event Bus, DLQ, and Caching
- Hindsight: Persistent memory of resolved incident post-mortems

## 5. Security & Infrastructure
Deployed natively to Kubernetes. Uses strict RBAC (only `recovery-engine` can mutate K8s resources). Uses JWT for service-to-service auth in the data plane.
