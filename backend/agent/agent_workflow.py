"""
====================================================================
agent/agent_workflow.py - ReAct Agent Workflow
====================================================================
Purpose: Implements the dynamic agent reasoning and action loop.
         It coordinates tool executions (Prometheus, Elasticsearch,
         Jaeger queries) and generates structured Root Cause Analyses.
====================================================================
"""

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from shared.config import config
from shared.database import hindsight_memory
from shared.models import (
    AnalysisRequest,
    AnalysisResponse,
    RootCauseAnalysis,
    Severity,
    AnalysisStatus,
    MetricsSnapshot,
    LogSnapshot,
    TraceSnapshot
)
from agent.llm_client import UnifiedLLMClient

# ---- Logging Setup ----
logger = logging.getLogger(__name__)

REGISTERED_TOOLS = {
    "get_prometheus_metrics",
    "get_elasticsearch_logs",
    "get_jaeger_traces",
    "get_cluster_status"
}

# ====================================================================
# ReAct Agent System Prompt
# ====================================================================
REACT_SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) and DevOps specialist troubleshooting a production Kubernetes (EKS) cluster.
Your objective is to diagnose the root cause of the user's reported problem using a step-by-step Reasoning and Acting (ReAct) workflow.

You have access to the following tools to fetch live telemetry:

1. get_prometheus_metrics(time_range_minutes: int, namespace: str)
   - Fetches CPU, Memory, pod restarts, and HTTP error rate metrics.
   - Input Arguments: {"time_range_minutes": 30, "namespace": "optional_namespace_here"}
   
2. get_elasticsearch_logs(time_range_minutes: int, namespace: str, service: str)
   - Fetches warning/error logs and OOM kills.
   - Input Arguments: {"time_range_minutes": 30, "namespace": "optional_namespace", "service": "optional_service"}
   
3. get_jaeger_traces(time_range_minutes: int, namespace: str, service: str, trace_id: str)
   - Fetches distributed traces showing service dependency calls, latencies, and span errors.
   - Input Arguments: {"time_range_minutes": 30, "namespace": "optional_namespace", "service": "optional_service", "trace_id": "optional_trace_id"}

4. get_cluster_status()
   - Quick health overview of cluster nodes and basic status.
   - Input Arguments: {}

INSTRUCTIONS:
You must alternate between "Thought", "Action", and receiving the "Observation" until you have sufficient evidence to determine the root cause.
Always think carefully about what data you need. For example:
- If a service is slow, fetch Jaeger traces to see where latency is high.
- If a service returns 5xx errors, fetch Elasticsearch logs for error messages.
- If pods are restarting, check Prometheus metrics for CPU/Memory limits.

FORMAT REQUIREMENT:
Your response must strictly match this pattern:

Thought: <detailed explanation of what you know so far and what telemetry you should fetch next>
Action: <tool_name>(<json_arguments_dict>)

Wait for the system to execute the tool and provide the "Observation:". Repeat this cycle up to the iteration limit.
Once you have collected all necessary evidence and have a clear diagnosis, output your final conclusion in this EXACT format:

Thought: I now have enough information to diagnose the issue. Let me assemble the final Root Cause Analysis.
Final Answer: {
  "root_cause_summary": "One sentence primary cause",
  "detailed_analysis": "Detailed explanation of what went wrong, why it happened, and how the evidence supports this",
  "severity": "critical|high|medium|low|info",
  "affected_components": ["service-a", "pod-b"],
  "recommended_actions": [
    "1. Urgent fix",
    "2. Preventive measure"
  ],
  "metrics_evidence": ["Metric anomaly lines found"],
  "log_evidence": ["Specific error logs seen"],
  "trace_evidence": ["Trace IDs analyzed"],
  "confidence_score": 0.95,
  "additional_context": "Any caveats or observations"
}

Do NOT wrap the Final Answer JSON in backticks (e.g. ```json). Output raw, valid JSON immediately following 'Final Answer: '.
"""


class AgentWorkflow:
    """
    Orchestrates the dynamic ReAct troubleshooting workflow using
    telemetry collectors as tools and connecting to LLMs.
    """

    def __init__(self, provider: Optional[str] = None):
        """Initialize unified client and collectors."""
        self.llm = UnifiedLLMClient(provider=provider)
        
        # Initialize collectors lazily to avoid circular/unnecessary imports
        self._prometheus = None
        self._elasticsearch = None
        self._jaeger = None

        # Snapshots cached during run to populate final response
        self.metrics_snapshot = None
        self.log_snapshot = None
        self.trace_snapshot = None
        self.collection_errors: List[str] = []

    @property
    def prometheus(self):
        if not self._prometheus:
            from lambda_.collectors.prometheus_collector import PrometheusCollector
            self._prometheus = PrometheusCollector()
        return self._prometheus

    @property
    def elasticsearch(self):
        if not self._elasticsearch:
            from lambda_.collectors.elasticsearch_collector import ElasticsearchCollector
            self._elasticsearch = ElasticsearchCollector()
        return self._elasticsearch

    @property
    def jaeger(self):
        if not self._jaeger:
            from lambda_.collectors.jaeger_collector import JaegerCollector
            self._jaeger = JaegerCollector()
        return self._jaeger

    # ====================================================================
    # Tools / Actions exposed to the LLM
    # ====================================================================

    def get_prometheus_metrics(self, time_range_minutes: int = 30, namespace: Optional[str] = None) -> str:
        """Fetch metrics data and return a summary string."""
        logger.info(f"Tool Execute: get_prometheus_metrics(time_range_minutes={time_range_minutes}, namespace={namespace})")
        try:
            snapshot = self.prometheus.collect_all_metrics(
                lookback_minutes=int(time_range_minutes),
                namespace=namespace
            )
            self.metrics_snapshot = snapshot
            
            # Format high-level summary
            output = [
                f"Prometheus Metrics Summary (last {time_range_minutes}m):",
                snapshot.summary,
                f"  - High CPU Anomalies Detected: {snapshot.has_high_cpu}",
                f"  - High Memory Anomalies Detected: {snapshot.has_high_memory}",
                f"  - Pod Restarts Detected: {snapshot.has_pod_restarts}",
                f"  - High HTTP Error Rates: {snapshot.has_high_error_rate}"
            ]
            
            # Add specific anomalous series details
            if snapshot.cpu_metrics:
                output.append("\nCPU Details (Top pods):")
                for s in sorted(snapshot.cpu_metrics, key=lambda x: x.max_value or 0, reverse=True)[:3]:
                    pod = s.labels.get("pod", s.labels.get("instance", "?"))
                    output.append(f"  * Pod {pod}: avg={s.avg_value:.1f}%, max={s.max_value:.1f}%")
                    
            if snapshot.memory_metrics:
                output.append("\nMemory Details (Top pods):")
                for s in sorted(snapshot.memory_metrics, key=lambda x: x.max_value or 0, reverse=True)[:3]:
                    pod = s.labels.get("pod", "?")
                    output.append(f"  * Pod {pod}: avg={s.avg_value:.1f}%, max={s.max_value:.1f}%")
                    
            if snapshot.pod_status_metrics:
                output.append("\nPod Restarts Details:")
                for s in snapshot.pod_status_metrics[:3]:
                    pod = s.labels.get("pod", "?")
                    output.append(f"  * Pod {pod}: {s.latest_value:.0f} restart(s)")

            return "\n".join(output)
        except Exception as e:
            err_msg = f"Failed to get prometheus metrics: {e}"
            logger.error(err_msg)
            self.collection_errors.append(err_msg)
            return f"Error executing tool: {err_msg}"

    def get_elasticsearch_logs(
        self,
        time_range_minutes: int = 30,
        namespace: Optional[str] = None,
        service: Optional[str] = None
    ) -> str:
        """Fetch logs data and return summary string."""
        logger.info(f"Tool Execute: get_elasticsearch_logs(time_range_minutes={time_range_minutes}, namespace={namespace}, service={service})")
        try:
            snapshot = self.elasticsearch.collect_all_logs(
                lookback_minutes=int(time_range_minutes),
                namespace=namespace,
                service=service
            )
            self.log_snapshot = snapshot
            
            output = [
                f"Elasticsearch Logs Summary (last {time_range_minutes}m):",
                snapshot.summary,
                f"  - Total Logs Analyzed: {snapshot.total_logs_found}",
                f"  - OOM Errors Detected: {snapshot.has_oom_errors}",
                f"  - Crash Loops Detected: {snapshot.has_crash_loops}",
                f"  - Connection Errors: {snapshot.has_connection_errors}"
            ]
            
            if snapshot.top_errors:
                output.append("\nTop Error Patterns:")
                for i, err in enumerate(snapshot.top_errors[:5], 1):
                    output.append(f"  {i}. [{err['count']}x] {err['message'][:150]}")
                    
            if snapshot.error_logs:
                output.append("\nRecent Critical Logs:")
                for log in snapshot.error_logs[:5]:
                    output.append(f"  * [{log.timestamp.strftime('%H:%M:%S')}] [{log.pod_name or log.service}] {log.message[:200]}")
                    
            return "\n".join(output)
        except Exception as e:
            err_msg = f"Failed to get elasticsearch logs: {e}"
            logger.error(err_msg)
            self.collection_errors.append(err_msg)
            return f"Error executing tool: {err_msg}"

    def get_jaeger_traces(
        self,
        time_range_minutes: int = 30,
        namespace: Optional[str] = None,
        service: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> str:
        """Fetch distributed traces and return summary string."""
        logger.info(f"Tool Execute: get_jaeger_traces(time_range_minutes={time_range_minutes}, namespace={namespace}, service={service}, trace_id={trace_id})")
        try:
            snapshot = self.jaeger.collect_all_traces(
                lookback_minutes=int(time_range_minutes),
                namespace=namespace,
                service=service,
                trace_id=trace_id
            )
            self.trace_snapshot = snapshot
            
            output = [
                f"Jaeger Traces Summary (last {time_range_minutes}m):",
                snapshot.summary,
                f"  - Slow Traces Count: {len(snapshot.slow_traces)}",
                f"  - Error Traces Count: {len(snapshot.error_traces)}",
                f"  - Latency stats: P50={snapshot.p50_latency_ms or 0:.1f}ms, P95={snapshot.p95_latency_ms or 0:.1f}ms, P99={snapshot.p99_latency_ms or 0:.1f}ms"
            ]
            
            if snapshot.error_traces:
                output.append("\nError Traces:")
                for t in snapshot.error_traces[:3]:
                    output.append(f"  * Trace ID: {t.trace_id} | Root Service: {t.root_service} | Operation: {t.root_operation} | {t.error_span_count} error spans")
                    # Include some span errors
                    err_spans = [s for s in t.spans if s.is_error][:2]
                    for span in err_spans:
                        output.append(f"    - Failed Span: {span.service_name}::{span.operation_name} ({span.duration_ms:.1f}ms)")
                        
            return "\n".join(output)
        except Exception as e:
            err_msg = f"Failed to get jaeger traces: {e}"
            logger.error(err_msg)
            self.collection_errors.append(err_msg)
            return f"Error executing tool: {err_msg}"

    def get_cluster_status(self) -> str:
        """Quick EKS health check using Prometheus status metrics."""
        logger.info("Tool Execute: get_cluster_status()")
        try:
            snapshot = self.prometheus.collect_all_metrics(lookback_minutes=10)
            healthy = not any([
                snapshot.has_high_cpu,
                snapshot.has_high_memory,
                snapshot.has_pod_restarts,
                snapshot.has_high_error_rate
            ])
            status = "HEALTHY" if healthy else "DEGRADED"
            output = [
                f"EKS Cluster Overall Status: {status}",
                f"  - Metrics Status: CPU normal, RAM normal" if healthy else f"  - Metrics Issues: {snapshot.summary}",
                f"  - Monitored Namespaces: {config.eks.monitored_namespaces}"
            ]
            return "\n".join(output)
        except Exception as e:
            err_msg = f"Failed to get cluster status: {e}"
            logger.error(err_msg)
            self.collection_errors.append(err_msg)
            return f"Error executing tool: {err_msg}"

    # ====================================================================
    # ReAct Routing & Execution
    # ====================================================================

    def execute_action(self, action_name: str, args: dict) -> str:
        """Parse action name and safely dispatch to collector tools."""
        try:
            if action_name == "get_prometheus_metrics":
                return self.get_prometheus_metrics(
                    time_range_minutes=args.get("time_range_minutes", 30),
                    namespace=args.get("namespace")
                )
            elif action_name == "get_elasticsearch_logs":
                return self.get_elasticsearch_logs(
                    time_range_minutes=args.get("time_range_minutes", 30),
                    namespace=args.get("namespace"),
                    service=args.get("service")
                )
            elif action_name == "get_jaeger_traces":
                return self.get_jaeger_traces(
                    time_range_minutes=args.get("time_range_minutes", 30),
                    namespace=args.get("namespace"),
                    service=args.get("service"),
                    trace_id=args.get("trace_id")
                )
            elif action_name == "get_cluster_status":
                return self.get_cluster_status()
            else:
                return f"Error: Tool '{action_name}' is not recognized. Please use one of the listed tools."
        except Exception as e:
            return f"Error executing tool '{action_name}' with args {args}: {e}"

    async def run(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Executes the ReAct loop to diagnose the Root Cause of the request query.
        Incorporates Hindsight semantic memory recall, wall-clock budget limits,
        JSON schema retry validation, and autonomous runbook retention.
        """
        if not request.request_id:
            request.request_id = str(uuid.uuid4())

        logger.info(f"Starting ReAct Agent Workflow for query: '{request.query}'")
        start_time = time.time()

        # ---- Task 2: Hindsight Memory Recall Check ----
        # BEFORE the first log/metric analysis step, query Hindsight for semantically similar outages
        try:
            recalled_memories = await hindsight_memory.recall(request.query, k=3)
            high_confidence = [m for m in recalled_memories if m.get("success_rate", 0.0) >= 0.8]
            if high_confidence:
                best = high_confidence[0]
                logger.info("hindsight_recall_hit", extra={"match": best, "symptom": request.query})
                
                playbook_actions = best.get("playbook")
                if isinstance(playbook_actions, str):
                    try:
                        playbook_actions = json.loads(playbook_actions)
                    except Exception:
                        playbook_actions = [playbook_actions]
                if not isinstance(playbook_actions, list):
                    playbook_actions = [str(playbook_actions)]

                final_rca = RootCauseAnalysis(
                    analysis_id=str(uuid.uuid4()),
                    user_query=request.query,
                    analyzed_at=datetime.utcnow(),
                    severity=Severity.HIGH,
                    status=AnalysisStatus.COMPLETED,
                    root_cause_summary=f"Recalled diagnosis: {best.get('resolution', 'Known Kubernetes outage')}",
                    detailed_analysis=(
                        f"🧠 Hindsight Recall Hit: Matches previous outage (Incident ID: {best.get('incident_id', 'historical')}, "
                        f"historical success rate: {best.get('success_rate', 0.95):.0%}). Proposing validated playbook directly "
                        f"without redundant telemetry probe latency."
                    ),
                    recommended_actions=playbook_actions,
                    affected_components=[request.target_service] if request.target_service else [],
                    confidence_score=float(best.get("success_rate", 0.95)),
                    llm_model_used="hindsight-semantic-memory",
                    analysis_duration_seconds=round(time.time() - start_time, 2),
                    raw_llm_response=json.dumps(best)
                )

                return AnalysisResponse(
                    request_id=request.request_id,
                    rca=final_rca,
                    metrics_snapshot=None,
                    log_snapshot=None,
                    trace_snapshot=None,
                    collection_errors=[]
                )
        except Exception as e:
            logger.warning(f"Hindsight recall pre-check notice: {e}. Continuing with standard ReAct telemetry loop.")

        # Initialize loop parameters
        max_iterations = config.agent.max_iterations
        wall_clock_budget = float(os.getenv("REACT_MAX_SECONDS", 120))
        history: List[str] = []
        tool_parse_retries = 0
        
        # Seed the query into the context
        query_context = f"USER QUERY: {request.query}\n"
        if request.target_namespace:
            query_context += f"TARGET NAMESPACE: {request.target_namespace}\n"
        if request.target_service:
            query_context += f"TARGET SERVICE: {request.target_service}\n"
        if request.trace_id:
            query_context += f"TARGET TRACE ID: {request.trace_id}\n"

        current_prompt = query_context
        final_rca: Optional[RootCauseAnalysis] = None
        
        for iteration in range(max_iterations):
            # Check wall-clock budget before beginning iteration
            elapsed = time.time() - start_time
            if elapsed > wall_clock_budget:
                logger.warning(f"ReAct loop exceeded wall-clock budget of {wall_clock_budget}s (elapsed: {elapsed:.1f}s). Triggering fail-safe analyzer.")
                logger.info("react_fallback_activated")
                final_rca = self._run_direct_fallback(request, start_time)
                break

            logger.info(f"ReAct Loop: Iteration {iteration + 1}/{max_iterations} (elapsed: {elapsed:.1f}s)")
            
            # Construct complete prompt for this step
            full_prompt = (
                f"{current_prompt}\n"
                f"What is your next Thought and Action? (Or Final Answer if you have solved it)"
            )
            
            # Call LLM via multi-provider failover
            response = self.llm.invoke(
                prompt=full_prompt,
                system_prompt=REACT_SYSTEM_PROMPT,
                temperature=config.agent.temperature,
                max_tokens=config.agent.max_tokens
            )
            
            if not response:
                logger.error("All LLM providers failed or returned empty. Activating fail-safe analyzer.")
                logger.info("react_fallback_activated")
                final_rca = self._run_direct_fallback(request, start_time)
                break
                
            if config.agent.verbose:
                print(f"\n--- [AGENT ITERATION {iteration + 1}] ---")
                print(response)
                print("---------------------------------")
                
            history.append(response)
            
            # Look for Final Answer
            if "Final Answer:" in response:
                final_answer_text = response.split("Final Answer:", 1)[1].strip()
                final_rca = self._parse_final_answer(final_answer_text, request, start_time)
                break
                
            # Parse Action
            action_match = re.search(r"Action:\s*(\w+)\((.*?)\)", response, re.DOTALL)
            if action_match:
                tool_name = action_match.group(1).strip()
                args_str = action_match.group(2).strip()
                
                # Task 4: JSON parse & schema validation with max 3 retries
                parse_ok = False
                tool_args = {}
                
                if tool_name not in REGISTERED_TOOLS:
                    tool_parse_retries += 1
                    logger.warning(f"Unregistered tool called: '{tool_name}' (retry {tool_parse_retries}/3)")
                    if tool_parse_retries > 3:
                        logger.warning("Max tool retries exceeded. Activating fail-safe analyzer.")
                        logger.info("react_fallback_activated")
                        final_rca = self._run_direct_fallback(request, start_time)
                        break
                    current_prompt += f"\nObservation: Tool '{tool_name}' is not recognized. Re-emit ONLY one of: {list(REGISTERED_TOOLS)}.\n"
                    continue

                try:
                    tool_args = json.loads(args_str) if args_str else {}
                    if not isinstance(tool_args, dict):
                        raise ValueError("Tool arguments must be a JSON object dictionary.")
                    parse_ok = True
                except (json.JSONDecodeError, ValueError) as err:
                    # Attempt a regex/eval fallback for simple key-values
                    cleaned_args = {}
                    for item in re.finditer(r'"(\w+)":\s*"(.*?)"', args_str):
                        cleaned_args[item.group(1)] = item.group(2)
                    for item in re.finditer(r'"(\w+)":\s*(\d+)', args_str):
                        cleaned_args[item.group(1)] = int(item.group(2))
                    if cleaned_args:
                        tool_args = cleaned_args
                        parse_ok = True
                    else:
                        tool_parse_retries += 1
                        logger.warning(f"Invalid JSON in tool args: '{args_str}' ({err}) (retry {tool_parse_retries}/3)")
                        if tool_parse_retries > 3:
                            logger.warning("Max tool JSON parse retries exceeded (3). Falling back to fail-safe analyzer.")
                            logger.info("react_fallback_activated")
                            final_rca = self._run_direct_fallback(request, start_time)
                            break
                        observation = "Your last output was not valid JSON. Re-emit ONLY the JSON tool call."
                        current_prompt += f"\nObservation: {observation}\n"
                        continue
                    
                # Execute tool safely
                try:
                    observation = self.execute_action(tool_name, tool_args)
                except Exception as ex:
                    observation = f"Error executing tool {tool_name}: {ex}"

                current_prompt += f"\nThought and Action {iteration + 1}:\n{response}\nObservation:\n{observation}\n"
            else:
                tool_parse_retries += 1
                if tool_parse_retries > 3:
                    logger.warning("Max format retries exceeded. Falling back to fail-safe analyzer.")
                    logger.info("react_fallback_activated")
                    final_rca = self._run_direct_fallback(request, start_time)
                    break
                warning_obs = "Your last output was not valid JSON or standard ReAct format. Re-emit ONLY the JSON tool call."
                current_prompt += f"\nObservation: {warning_obs}\n"
                
        # If we failed to get a Final Answer or exited early, do fallback
        if not final_rca:
            logger.warning("ReAct loop completed without resolving. Falling back to direct single-turn analysis.")
            logger.info("react_fallback_activated")
            final_rca = self._run_direct_fallback(request, start_time)

        # Commit resolved incident to Hindsight memory
        if final_rca and final_rca.status == AnalysisStatus.COMPLETED:
            try:
                await hindsight_memory.retain(
                    incident_id=request.request_id,
                    symptoms=request.query,
                    root_cause=final_rca.root_cause_summary,
                    playbook=final_rca.recommended_actions,
                    human_approved=False,
                    outcome="success"
                )
            except Exception as e:
                logger.warning(f"Auto-retain notice: {e}")

        # Assemble and return the complete AnalysisResponse
        return AnalysisResponse(
            request_id=request.request_id,
            rca=final_rca,
            metrics_snapshot=self.metrics_snapshot,
            log_snapshot=self.log_snapshot,
            trace_snapshot=self.trace_snapshot,
            collection_errors=self.collection_errors
        )

    def _parse_final_answer(self, json_text: str, request: AnalysisRequest, start_time: float) -> RootCauseAnalysis:
        """Parse LLM JSON block into RootCauseAnalysis model."""
        analysis_id = str(uuid.uuid4())
        duration = time.time() - start_time
        
        # Clean potential markdown wrapping
        json_clean = json_text
        if json_text.startswith("```"):
            # strip off ```json and ```
            json_clean = re.sub(r"^```(?:json)?\n", "", json_text)
            json_clean = re.sub(r"\n```$", "", json_clean)
            
        try:
            parsed = json.loads(json_clean.strip())
            
            # Map severity
            severity_str = parsed.get("severity", "medium").lower()
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = Severity.MEDIUM
                
            return RootCauseAnalysis(
                analysis_id=analysis_id,
                user_query=request.query,
                analyzed_at=datetime.utcnow(),
                severity=severity,
                status=AnalysisStatus.COMPLETED,
                root_cause_summary=parsed.get("root_cause_summary", "RCA finished"),
                detailed_analysis=parsed.get("detailed_analysis", "Review the evidence details."),
                recommended_actions=parsed.get("recommended_actions", []),
                affected_components=parsed.get("affected_components", []),
                metrics_evidence=parsed.get("metrics_evidence", []),
                log_evidence=parsed.get("log_evidence", []),
                trace_evidence=parsed.get("trace_evidence", []),
                confidence_score=float(parsed.get("confidence_score", 0.8)),
                llm_model_used=f"{config.default_llm_provider}:{getattr(config, config.default_llm_provider).model_id}",
                analysis_duration_seconds=round(duration, 2),
                raw_llm_response=json_text
            )
        except Exception as e:
            logger.error(f"Failed to parse Final Answer JSON: {e}. Raw: {json_text}")
            
            # Graceful parsing fallback using text representation
            return RootCauseAnalysis(
                analysis_id=analysis_id,
                user_query=request.query,
                severity=Severity.MEDIUM,
                status=AnalysisStatus.COMPLETED,
                root_cause_summary="Agent resolved issue but failed to output valid JSON schema",
                detailed_analysis=json_text,
                recommended_actions=["Manually review raw agent steps for diagnostics"],
                confidence_score=0.4,
                llm_model_used=config.default_llm_provider,
                analysis_duration_seconds=round(duration, 2),
                raw_llm_response=json_text
            )

    def _run_direct_fallback(self, request: AnalysisRequest, start_time: float) -> RootCauseAnalysis:
        """
        Executes a rapid, single-turn analysis as a safety fallback using
        the project's standard RCAAnalyzer.
        """
        logger.info("Executing safety fallback to RCAAnalyzer...")
        try:
            from lambda_.ai.rca_analyzer import RCAAnalyzer
            analyzer = RCAAnalyzer()
            
            # Ensure snapshots are filled
            if not self.metrics_snapshot:
                self.metrics_snapshot = analyzer.prometheus.collect_all_metrics(lookback_minutes=30)
            if not self.log_snapshot:
                self.log_snapshot = analyzer.elasticsearch.collect_all_logs(lookback_minutes=30)
            if not self.trace_snapshot:
                self.trace_snapshot = analyzer.jaeger.collect_all_traces(lookback_minutes=30)
                
            response = analyzer.analyze(request)
            return response.rca
        except Exception as e:
            logger.error(f"RCA fallback failure: {e}")
            return RootCauseAnalysis(
                analysis_id=str(uuid.uuid4()),
                user_query=request.query,
                severity=Severity.HIGH,
                status=AnalysisStatus.FAILED,
                root_cause_summary="Troubleshooting session failed",
                detailed_analysis=f"The agent troubleshooting loop timed out or failed to resolve. Fallback error: {e}",
                recommended_actions=["Check AWS Bedrock permissions", "Check network telemetry connectivity"],
                confidence_score=0.0,
                analysis_duration_seconds=round(time.time() - start_time, 2)
            )
