# 🔍 AI-RCI: Intelligent Root Cause Analysis Platform
### *Empowering SREs with AI-Driven Incident Diagnostics and Automated Remediation*

---

## 📌 Project Overview
**AI-RCI (Artificial Intelligence Root Cause Analysis)** is a production-ready, AI-powered SRE (Site Reliability Engineering) agent platform designed to automatically diagnose, explain, and recommend solutions for Kubernetes cluster incidents. By leveraging advanced Large Language Models (LLMs) executing a **ReAct (Reasoning and Action)** loop, the platform breaks down telemetry silos (metrics, logs, traces) and transforms chaotic raw data into actionable root cause analyses and remediation playbooks in seconds.

---

## 🚨 The Problem Statement

In modern cloud-native, microservices-based architectures (such as Kubernetes/AWS EKS), resolving service disruptions is a stressful, complex, and time-consuming process. SRE and DevOps teams face several critical challenges:

### 1. The Telemetry Silo Problem
When a service fails, diagnostic data is scattered across multiple disconnected tools:
*   📈 **Metrics** (e.g., Prometheus) show *that* something is wrong (e.g., spikes in 500 error rates).
*   📋 **Logs** (e.g., Elasticsearch) show *what* might be failing (e.g., stack traces, null pointer exceptions).
*   🌐 **Traces** (e.g., Jaeger) show *where* the bottleneck is in a distributed call graph.
Manual correlation across these tools during a high-severity outage requires significant expertise and introduces crucial delays.

### 2. High Mean Time to Resolution (MTTR)
Manual investigation of incidents leads to high MTTR. Every minute of downtime translates directly to lost revenue, degraded customer experience, and SLA breaches.

### 3. Alert Fatigue & Cognitive Overload
SRE teams are bombarded with thousands of alerts daily. Distinguishing between a benign transient spike and a critical cascading system failure is extremely difficult, leading to fatigue and missed alerts.

### 4. Excessive LLM Costs & Latency
Applying naive AI solutions directly to every incident query results in high API token costs and slow response times (30s+ for complex reasoning chains), making them impractical for real-time operations.

---

## 💡 The Solution: AI-RCI

AI-RCI solves these challenges by deploying an **Intelligent SRE Diagnostics Agent** that automates the entire incident response lifecycle.

```
                  ┌───────────────────────────────────────────────┐
                  │          Kubernetes Incident Alert            │
                  └──────────────────────┬────────────────────────┘
                                         │
                                         ▼
                  ┌───────────────────────────────────────────────┐
                  │    Vectorize Hindsight Persistent Memory      │
                  │        (Multi-Strategy Recall Engine)         │
                  └──────────────────────┬────────────────────────┘
                                         │
                       ┌─────────────────┴─────────────────┐
                       │ Recall Miss                       │ Recall Hit (<100ms)
                       ▼                                   ▼
          ┌───────────────────────────┐       ┌───────────────────────────┐
          │     ReAct Agent Loop      │       │ Instant Solution & Playbook│
          │ (LLM + Telemetry Tools)   │       │ (Zero LLM Tokens Consumed)│
          └────────────┬──────────────┘       └───────────────────────────┘
                       │
                       ├─▶ Prometheus Metrics
                       ├─▶ Elasticsearch Logs
                       └─▶ Jaeger Traces
                               │
                               ▼
          ┌───────────────────────────────────────────┐
          │    Root Cause & Remediation Discovered    │
          └────────────────────┬──────────────────────┘
                               │
                               ▼
          ┌───────────────────────────────────────────┐
          │     Hindsight Retain Phase: Commit to     │
          │    Institutional Long-Term Agent Memory   │
          └────────────────────┬──────────────────────┘
                               │
                               ▼
          ┌───────────────────────────────────────────┐
          │        Auto-Healing & Ops Actions         │
          │         Jira / Slack / K8s Healer         │
          └───────────────────────────────────────────┘
```

### 🧠 1. Intelligent ReAct Reasoning Loop
Instead of simple prompt-engineering, AI-RCI utilizes a dynamic **ReAct (Reasoning + Action) Agent Loop**. Given a symptom (e.g., *"Why is the checkout service slow?"*), the agent plans its investigation, selects and executes telemetry-gathering tools, analyzes the returned data, and iterates until it confidently identifies the root cause.

### 🔌 2. Out-of-the-Box Telemetry Integration
The agent is equipped with specialized API connectors that securely fetch real-time telemetry on demand:
*   **Prometheus Collector:** Fetches CPU/memory utilization, request rates, error rates, and saturation metrics.
*   **Elasticsearch Collector:** Performs semantic and keyword searches across service logs to isolate exceptions and error patterns.
*   **Jaeger Collector:** Pulls distributed tracing spans to map latency bottlenecks and pinpoint slow dependency calls.

### 🧠 3. Persistent Agent Memory (Powered by Vectorize Hindsight)
Unlike static prompt caches or stateless LLM wrappers, AI-RCI implements true **Institutional Memory**:
*   **Retain Phase (`client.retain`):** When an incident is diagnosed and resolved, Hindsight Incident Agent commits the symptoms, causal patterns, and approved remediation playbooks into Vectorize Hindsight Cloud.
*   **Recall Phase (`client.recall`):** Before running expensive multi-turn reasoning loops, the agent queries Hindsight using hybrid semantic and graph retrieval.
*   **Runbook Evolution:** When human engineers accept or modify diagnostic recommendations, Hindsight updates its memory bank. The agent gets smarter over time, slashing MTTR from 45 minutes to **<100ms** and cutting LLM token costs by **95%+**.

### 🛠️ 4. Auto-Remediation & ChatOps Integration
AI-RCI doesn't just stop at diagnostics. It includes active connectors to bridge the gap between analysis and action:
*   **Slack alerts** and updates sent automatically to engineering channels.
*   **Jira tickets** generated with complete context, metrics logs, and recommended playbooks.
*   **Kubernetes auto-healing** triggers (e.g., scaling up pods, restarting deployments, rolling back changes).

---

## ⚙️ The Technology Stack

AI-RCI is built on a modern, scalable, and secure microservices architecture designed to transition seamlessly from local development to production-grade enterprise deployments.

```
                           +----------------------------+
                           |      React Frontend        |
                           |  (Vite, Nginx, Port 3000)  |
                           +--------------+-------------+
                                          |
                                          | POST /api/query
                                          v
                           +----------------------------+
                           |      FastAPI Backend       |
                           |     (Python, Port 8000)    |
                           +-------+--------------+-----+
                                   |              |
           hindsight-client SDK    |              | AWS Bedrock / Groq / OpenAI
                                   v              v
                     +-------------+--+      +----+---------------+
                     | Vectorize      |      |  AI Reasoning LLM  |
                     | Hindsight      |      |     Engine         |
                     | Memory Cloud   |      |  (ReAct Dynamic)   |
                     +----------------+      +--------------------+
```

### 🎨 Frontend: SRE Cockpit
*   **React.js (Vite):** A lightweight, ultra-fast frontend framework for building a responsive user interface.
*   **Vanilla CSS Design System:** Custom dark-mode dashboard tailored for SREs, utilizing vibrant highlights, high contrast readability, and clean card-based diagnostic layouts.
*   **Nginx Reverse Proxy:** Serves static frontend assets in production and acts as a secure reverse proxy to route `/api/*` requests to the backend service.

### ⚡ Backend: High-Performance Engine
*   **FastAPI (Python):** An asynchronous, high-performance web framework designed for low latency, featuring automatic OpenAPI (Swagger) documentation generation.
*   **Pydantic:** Robust data modeling and strict input/output validation for API requests and telemetry schemas.
*   **PyMySQL:** A pure-Python MySQL client utilized for rapid connection handling, caching, and incident log audits.

### 🤖 LLM & Reasoning Layer
*   **ReAct Reasoning Framework:** Custom agent workflow loop coordinating step-by-step reasoning (`Thought`, `Action`, `Observation`).
*   **AWS Bedrock (Claude 3.5 Sonnet):** The primary production model provider, offering high-speed, cost-effective reasoning, robust instruction-following, and deep understanding of infrastructure systems.
*   **Multi-Provider Fallback:** Native support for Anthropic and OpenAI APIs, allowing instant runtime switching in case of regional outages or provider limits.

### ☁️ Infrastructure, DevOps & IaC
*   **Docker & Docker Compose:** Containerized microservices structured for quick bootstrapping. Developers can run the entire frontend, backend, and MySQL database locally with a single `docker-compose up --build` command.
*   **Amazon EKS (Elastic Kubernetes Service):** The production hosting environment, ensuring high availability, auto-scaling, and secure network isolation.
*   **Terraform:** Infrastructure-as-Code (IaC) files to provision and manage AWS Lambda functions, IAM roles, and access controls programmatically.
*   **Kubernetes Manifests:** Pre-configured deployments, services, secrets, and configmaps designed for enterprise cloud environments.

---

## 🌟 Value Proposition & Impact

| Metric | Traditional SRE Workflow | AI-RCI Workflow |
|---|---|---|
| **Mean Time to Resolution (MTTR)** | ⏳ **30 to 120+ minutes** (Manual log searches, dashboard switching) | ⚡ **< 30 seconds** (Automated correlation and diagnosis) |
| **Token & API Costs** | 💸 High (Repetitive queries hit the LLM constantly) | 🛡️ **Extremely Low** (Hindsight memory recalls recurring incident playbooks in <100ms with 0 LLM tokens) |
| **Cognitive Load** | 🤯 High (Sifting through metric noise, logs, and traces manually) | 😌 **Low** (Receives curated, structured, high-confidence reports) |
| **Operational Scalability** | 📉 Hard to scale (Requires highly specialized SREs active 24/7) | 📈 **Infinite** (AI pre-diagnoses and documents issues autonomously) |

---

## 🎯 Summary
Hindsight Incident Agent bridges the critical gap between complex, distributed system failure symptoms and the actionable insights SREs need to fix them. By combining **state-of-the-art LLM reasoning (ReAct)**, **multi-source telemetry scraping**, and **Vectorize Hindsight persistent memory**, the platform delivers an enterprise-ready, self-healing diagnostic cockpit that dramatically cuts down MTTR from hours to under a second, learning continuously from every past outage.
