# Incident Response Agent Demo Runbook

**Last rehearsed**: 2026-09-27

## One-Liner Pitch
"We built the Incident Response Agent for Hindsight — production outages get resolved from memory, not re-diagnosis."

## Pre-Demo Checklist
- [ ] **Kubernetes Port-Forwards**: Ensure the BFF proxy and backend are reachable locally (e.g. `.\start.ps1` is running).
- [ ] **Backend Health**: Navigate to Settings and check that all services are green.
- [ ] **Memory Bank Seeded**: Ensure there are at least 5 memories in the Hindsight Cloud bank.
- [ ] **Browser Prepared**: Load `http://localhost:5173/`, close all non-essential tabs, disable system notifications.
- [ ] **Viewport**: Full screen your browser to maximize the visual impact of the dashboard.

## Exact 60-Second Sequence

### [0:00] Show Dashboard
- **Action**: Start on the `/` (Dashboard) page. Point at the top right header badge that says "Live · updated 2s ago".
- **Talk Track**: "Our platform monitors all microservices in real time. As you can see, we're currently polling live data directly from the cluster."

### [0:10] Run Fresh Diagnostic
- **Action**: Click the "Run demo" button in the top right Demo Bar (ensure "Checkout 500s" is selected). Wait for the app to navigate to the `/incidents` page.
- **Talk Track**: "Let's simulate a sudden spike in 500 errors on the checkout service. The agent kicks off an autonomous diagnostic using a standard LLM reasoning loop to identify the root cause."

### [0:20] Show FRESH REASONING Badge
- **Action**: Hover or point to the AI Analysis badge that shows "FRESH" (e.g. ~24 seconds of reasoning time).
- **Talk Track**: "It took about 20 seconds to diagnose and build a recovery playbook. That's great, but in production, seconds matter."

### [0:30] Reset & Seed
- **Action**: Click the "Reset" button in the Demo Bar. Note the green toast: "Memory bank reset · 5 incidents seeded".
- **Talk Track**: "Once an incident is resolved and human-approved, we retain the exact playbook in Hindsight Memory. Let's see what happens when that exact same issue happens again."

### [0:35] Run Recall Diagnostic
- **Action**: Click the "Run demo" button again with the exact same scenario.
- **Talk Track**: "Another checkout outage occurs..."

### [0:40] Show HINDSIGHT RECALL HIT Badge
- **Action**: Point to the new badge displaying "RECALL HIT" (sub-second duration, 0 tokens).
- **Talk Track**: "This time, the agent bypassed the LLM entirely. It recognized the symptom signature and instantly recalled the proven playbook from memory in milliseconds."

### [0:50] Navigate to Memory Bank
- **Action**: Click "Memory Bank" in the sidebar. Scroll through the seeded incidents.
- **Talk Track**: "This isn't a static cache. It's an actively growing knowledge base. Every outage makes the system permanently faster and more resilient."

### [1:00] End on Memory Bank
- **Action**: Pause on the Memory Bank page, showing the success rates and playbooks.
- **Talk Track**: "This is what the agent learned. Thank you."

---

## Fallback Scripts

**a) Hindsight Cloud Unreachable**
- **Action**: The UI will gracefully fail over to the local dictionary cache. Point it out on the Settings page or Memory Bank page.
- **Talk Track**: "Our upstream cloud is currently unreachable, but our system is built for resilience. We've automatically fallen back to the local memory cache to ensure no downtime in resolution."

**b) K8s Port-Forward Died**
- **Action**: Run `.\start.ps1 -SkipBuild` in the terminal to restart the tunnels.
- **Talk Track**: "It looks like our local tunnel to the cluster just dropped. Let me quickly restart the port-forwards. The agent itself continues running autonomously in the cluster even when the UI disconnects."

**c) LLM Provider 429 (Rate Limit)**
- **Action**: The agent automatically fails over to a deterministic analyzer path (Amber badge).
- **Talk Track**: "We just hit an LLM rate limit, but the agent automatically downgraded to deterministic heuristics to keep operations moving without stalling."

**d) Memory Bank Empty**
- **Action**: Click "Seed memory" in the Memory Bank page or the Demo Bar.
- **Talk Track**: "We started with a clean slate to show how it learns. Let me quickly seed the bank with a few historical incidents to demonstrate the recall mechanism."
