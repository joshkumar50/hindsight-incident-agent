# Demo Video Script: Autonomous Kubernetes SRE Agent

**Target Duration:** 60 - 90 seconds
**Pacing:** Fast, technical, showing real UI interactions.

| Time | Visuals | Audio / Voiceover |
| :--- | :--- | :--- |
| **0:00 - 0:05** | **Title Card:** Building an Autonomous SRE Agent with Semantic Memory. Fade into the Executive Dashboard showing 12 healthy services. | "When a Kubernetes cluster goes down, the last thing you want to do is manually dig through logs and metrics to find the root cause." |
| **0:05 - 0:15** | Click "Inject Chaos" on the `order-service`. The dashboard flashes red, error rates spike to 14.8%, and P99 latency jumps to 2450ms. | "Let's simulate a production outage on our order service. Latency is spiking, and errors are climbing." |
| **0:15 - 0:25** | Open the SRE Diagnostic Console. Type: *"Why is order-service returning 500 errors?"* Hit "Run Diagnostics". A loading spinner appears: *"ReAct SRE Agent is reasoning..."* | "Instead of opening three different monitoring tools, I ask our Autonomous SRE agent to investigate." |
| **0:25 - 0:40** | Split screen: Left shows the UI loading. Right shows terminal logs of the agent's ReAct loop calling `get_prometheus_metrics` and `get_elasticsearch_logs`. The UI updates with a "🔍 FRESH REASONING" amber badge and a detailed root cause (e.g., Database connection pool exhaustion). | "Using a ReAct loop, the agent autonomously queries Prometheus and Elasticsearch, triangulating the root cause and generating a remediation playbook. This took about 15 seconds." |
| **0:40 - 0:50** | The operator clicks the "👍 Accept Runbook" button under the recommended actions. A toast notification confirms: *"Feedback recorded... Hindsight memory evolved."* | "Once the issue is resolved, we accept the runbook. Here's where it gets interesting: the agent commits this fix to its Vectorize Hindsight persistent memory bank." |
| **0:50 - 1:05** | Refresh the page. Click "Inject Chaos" on `order-service` again. Enter the exact same query: *"Why is the checkout service returning 500 errors?"* Hit "Run Diagnostics". | "What happens if this exact same issue strikes again a week later?" |
| **1:05 - 1:15** | Instantly, the UI populates. The prominent pulsing purple badge appears: *"🧠 HINDSIGHT RECALL HIT | 0.1s · 0 LLM tokens"* | "Because it remembers, the agent recalls the exact playbook in under 100 milliseconds. No expensive LLM calls, no redundant telemetry scraping." |
| **1:15 - 1:30** | Slowly zoom out on the dashboard showing the "System Availability" and "MTTR Reduction" KPI cards. | "By giving our agent semantic memory, we've turned stateless troubleshooting into a self-healing system. Check out the repo to build your own." |
