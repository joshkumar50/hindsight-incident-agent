# Demo Guide (5 Minutes)

**0:00 - 0:30 (The Hook)**:
"Good evening. We are Team Nexbit. Modern Kubernetes architectures are too complex for humans to troubleshoot in real-time. We built Hindsight Incident Agent: an Autonomous SRE platform that detects, diagnoses, and repairs cluster failures in seconds, without human intervention."

**0:30 - 2:00 (The Architecture)**:
(Show the React Dashboard) "This is our Enterprise Dashboard. It is fed by a 17-microservice architecture secured by JWT, Network Policies, and powered by Redis Streams."

**2:00 - 4:00 (The Climax - Chaos Injection)**:
"Let's prove it. We are triggering a massive CPU spike via our Chaos Controller. (Click Inject). Watch the Live Topology graph. Within 3 seconds, Prometheus catches the anomaly. The RCA Engine analyzes the traces. The Decision Engine (powered by LLMs) decides to restart the Pod. The Execution Engine applies the fix. Total MTTR: 8 seconds."

**4:00 - 5:00 (The Close)**:
"Everything you just saw was logged immutably to PostgreSQL for AI Governance. Hindsight Incident Agent isn't a toy—it's a production-ready, zero-trust autonomous platform. Thank you."
