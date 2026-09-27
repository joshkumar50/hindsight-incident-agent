"""
=============================================================
lambda/ai/rca_analyzer.py
=============================================================
Purpose: Core AI Root Cause Analysis engine.

This module ties together:
  1. All three telemetry collectors (Prometheus, ES, Jaeger)
  2. The Bedrock LLM client
  3. A structured prompt engineering strategy
  4. Response parsing to extract structured RCA output

The RCA process:
  1. User asks: "Why is the checkout service returning 500 errors?"
  2. Collectors gather metrics, logs, traces from the last 30 minutes
  3. All data is summarized into a structured context string
  4. Context + user query → Bedrock LLM → Structured RCA response
  5. Response is parsed into a RootCauseAnalysis model
  6. Returned to Lambda → Streamlit UI

PROMPT ENGINEERING:
  The system prompt defines the AI's role as an SRE/DevOps expert.
  The user prompt includes:
    - The user's question
    - Metrics anomalies detected
    - Error log patterns
    - Trace error analysis
  The LLM is asked to return JSON for easy parsing.
=============================================================
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import config
from shared.models import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    LogSnapshot,
    MetricsSnapshot,
    RootCauseAnalysis,
    Severity,
    TraceSnapshot,
)
from lambda_.ai.bedrock_client import BedrockLLMClient
from lambda_.collectors.prometheus_collector import PrometheusCollector
from lambda_.collectors.elasticsearch_collector import ElasticsearchCollector
from lambda_.collectors.jaeger_collector import JaegerCollector

# ---- Logging Setup ----
logger = logging.getLogger(__name__)


# ============================================================
# System Prompt - Defines the LLM's role and response format
# ============================================================

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) and DevOps specialist 
with deep knowledge of:
- Kubernetes (EKS) cluster operations and troubleshooting
- Prometheus metrics interpretation and anomaly detection
- Distributed tracing analysis with Jaeger
- Log analysis from EFK (Elasticsearch, Fluentd, Kibana) stack
- AWS infrastructure and services
- Root cause analysis methodology (e.g., "5 Whys", fishbone diagrams)
- Service mesh, microservices, and cloud-native architectures

Your task is to analyze telemetry data (metrics, logs, traces) from a production 
Kubernetes environment and identify the root cause of issues.

CRITICAL INSTRUCTIONS:
1. Always respond with valid JSON matching the schema below
2. Be specific and actionable - no generic advice
3. Reference actual data from the telemetry (pod names, error messages, trace IDs)
4. Order recommended_actions by priority (most urgent first)
5. Set confidence_score between 0.0 and 1.0 based on evidence quality
6. If there is insufficient evidence to determine a root cause, say so clearly

RESPONSE JSON SCHEMA:
{
  "root_cause_summary": "One sentence describing the primary root cause",
  "detailed_analysis": "Multi-paragraph detailed explanation of what went wrong, why it happened, and how the metrics/logs/traces support this conclusion",
  "severity": "critical|high|medium|low|info",
  "affected_components": ["list", "of", "affected", "services", "or", "pods"],
  "recommended_actions": [
    "1. Specific action to take immediately",
    "2. Next action after that",
    "3. Long-term prevention measure"
  ],
  "metrics_evidence": ["Specific metric anomalies that support the diagnosis"],
  "log_evidence": ["Specific log messages that confirm the issue"],
  "trace_evidence": ["Trace IDs or operation names showing the failure path"],
  "confidence_score": 0.85,
  "additional_context": "Any caveats, alternative hypotheses, or follow-up questions"
}"""


class RCAAnalyzer:
    """
    Root Cause Analysis engine that orchestrates data collection
    and AI-powered analysis using AWS Bedrock.
    
    This is the central class of the Lambda function.
    Usage:
        analyzer = RCAAnalyzer()
        response = analyzer.analyze(request)
    """

    def __init__(self):
        """Initialize all collectors and the Bedrock LLM client."""

        # ---- Initialize telemetry collectors ----
        # Each collector talks to one observability backend
        self.prometheus = PrometheusCollector()
        self.elasticsearch = ElasticsearchCollector()
        self.jaeger = JaegerCollector()

        # ---- Initialize the Bedrock LLM client ----
        self.llm = BedrockLLMClient()

        logger.info("RCAAnalyzer initialized with all collectors and LLM client")

    def _collect_telemetry(
        self, request: AnalysisRequest
    ) -> Tuple[MetricsSnapshot, LogSnapshot, TraceSnapshot, List[str]]:
        """
        Collect telemetry from all three observability backends in parallel.
        
        In Lambda, we run these sequentially due to the single-threaded
        environment, but they could be parallelized with concurrent.futures
        if needed for performance.
        
        Args:
            request: The analysis request containing scope and time window
        
        Returns:
            Tuple of (MetricsSnapshot, LogSnapshot, TraceSnapshot, errors_list)
        """
        lookback = request.lookback_minutes or config.lambda_cfg.lookback_minutes
        namespace = request.target_namespace
        service = request.target_service
        errors = []

        # ---- Collect Prometheus Metrics ----
        logger.info("Step 1/3: Collecting Prometheus metrics...")
        try:
            metrics_snapshot = self.prometheus.collect_all_metrics(
                lookback_minutes=lookback,
                namespace=namespace,
            )
        except Exception as e:
            # Don't fail the whole analysis if one collector fails
            logger.error(f"Prometheus collection failed: {e}")
            errors.append(f"Prometheus collection error: {str(e)}")
            metrics_snapshot = MetricsSnapshot(
                lookback_minutes=lookback,
                summary="Prometheus data unavailable",
            )

        # ---- Collect Elasticsearch Logs ----
        logger.info("Step 2/3: Collecting Elasticsearch logs...")
        try:
            log_snapshot = self.elasticsearch.collect_all_logs(
                lookback_minutes=lookback,
                namespace=namespace,
                service=service,
            )
        except Exception as e:
            logger.error(f"Elasticsearch collection failed: {e}")
            errors.append(f"Elasticsearch collection error: {str(e)}")
            log_snapshot = LogSnapshot(
                lookback_minutes=lookback,
                summary="Elasticsearch data unavailable",
            )

        # ---- Collect Jaeger Traces ----
        logger.info("Step 3/3: Collecting Jaeger traces...")
        try:
            trace_snapshot = self.jaeger.collect_all_traces(
                lookback_minutes=lookback,
                namespace=namespace,
                service=service,
                trace_id=request.trace_id,
            )
        except Exception as e:
            logger.error(f"Jaeger collection failed: {e}")
            errors.append(f"Jaeger collection error: {str(e)}")
            trace_snapshot = TraceSnapshot(
                lookback_minutes=lookback,
                summary="Jaeger data unavailable",
            )

        return metrics_snapshot, log_snapshot, trace_snapshot, errors

    def _build_analysis_prompt(
        self,
        request: AnalysisRequest,
        metrics: MetricsSnapshot,
        logs: LogSnapshot,
        traces: TraceSnapshot,
    ) -> str:
        """
        Build the LLM analysis prompt from the collected telemetry.
        
        This is the most critical function in the RCA pipeline.
        The quality of the RCA depends heavily on how well we
        present the telemetry data to the LLM.
        
        Structure:
          1. User's question
          2. Analysis scope and time window
          3. Metrics summary with anomalies highlighted
          4. Log summary with top errors and key messages
          5. Trace summary with error paths and latency data
          6. Request for structured JSON response
        """
        lookback = request.lookback_minutes or config.lambda_cfg.lookback_minutes

        # ---- Section 1: User Question ----
        prompt_parts = [
            f"USER QUESTION: {request.query}",
            f"\nANALYSIS SCOPE:",
            f"  - Time window: Last {lookback} minutes",
        ]

        if request.target_namespace:
            prompt_parts.append(f"  - Namespace: {request.target_namespace}")
        if request.target_service:
            prompt_parts.append(f"  - Service: {request.target_service}")
        if request.trace_id:
            prompt_parts.append(f"  - Specific Trace ID: {request.trace_id}")

        # ---- Section 2: Metrics Data ----
        prompt_parts.append("\n" + "=" * 60)
        prompt_parts.append("PROMETHEUS METRICS ANALYSIS:")
        prompt_parts.append("=" * 60)
        prompt_parts.append(metrics.summary)

        # Add specific metric anomalies with pod names
        if metrics.has_high_cpu:
            prompt_parts.append("\nCPU ANOMALIES:")
            # Show top 5 worst CPU offenders
            sorted_cpu = sorted(
                metrics.cpu_metrics,
                key=lambda s: s.max_value or 0,
                reverse=True,
            )[:5]
            for series in sorted_cpu:
                pod = series.labels.get("pod", series.labels.get("instance", "?"))
                ns = series.labels.get("namespace", "")
                prompt_parts.append(
                    f"  - Pod {pod} (ns:{ns}): avg={series.avg_value:.1f}%, "
                    f"max={series.max_value:.1f}%"
                )

        if metrics.has_high_memory:
            prompt_parts.append("\nMEMORY ANOMALIES:")
            sorted_mem = sorted(
                metrics.memory_metrics,
                key=lambda s: s.max_value or 0,
                reverse=True,
            )[:5]
            for series in sorted_mem:
                pod = series.labels.get("pod", "?")
                prompt_parts.append(
                    f"  - Pod {pod}: avg={series.avg_value:.1f}%, "
                    f"max={series.max_value:.1f}% of memory limit"
                )

        if metrics.has_pod_restarts:
            prompt_parts.append("\nPOD RESTARTS:")
            for series in metrics.pod_status_metrics[:5]:
                pod = series.labels.get("pod", "?")
                restarts = series.latest_value or 0
                prompt_parts.append(
                    f"  - Pod {pod}: {restarts:.0f} restart(s) in window"
                )

        if metrics.has_high_error_rate:
            prompt_parts.append("\nHTTP ERROR RATES:")
            sorted_err = sorted(
                metrics.http_error_metrics,
                key=lambda s: s.avg_value or 0,
                reverse=True,
            )[:5]
            for series in sorted_err:
                svc = series.labels.get("service", "?")
                prompt_parts.append(
                    f"  - Service {svc}: avg={series.avg_value:.1f}% 5xx error rate"
                )

        # ---- Section 3: Log Data ----
        prompt_parts.append("\n" + "=" * 60)
        prompt_parts.append("EFK STACK LOG ANALYSIS:")
        prompt_parts.append("=" * 60)
        prompt_parts.append(logs.summary)

        # Include top error patterns
        if logs.top_errors:
            prompt_parts.append("\nTOP ERROR PATTERNS (by frequency):")
            for i, err in enumerate(logs.top_errors[:5], 1):
                prompt_parts.append(
                    f"  {i}. [{err['count']}x] {err['message'][:200]}"
                )
                if err.get("services"):
                    prompt_parts.append(
                        f"     Services: {', '.join(err['services'])}"
                    )

        # Include recent critical error samples
        if logs.error_logs:
            prompt_parts.append("\nRECENT ERROR LOG SAMPLES:")
            for log_entry in logs.error_logs[:10]:  # Top 10 most recent errors
                prompt_parts.append(
                    f"  [{log_entry.timestamp.strftime('%H:%M:%S')}] "
                    f"[{log_entry.pod_name or log_entry.service}] "
                    f"{log_entry.message[:300]}"
                )

        # ---- Section 4: Trace Data ----
        prompt_parts.append("\n" + "=" * 60)
        prompt_parts.append("JAEGER DISTRIBUTED TRACE ANALYSIS:")
        prompt_parts.append("=" * 60)
        prompt_parts.append(traces.summary)

        # Include error trace details
        if traces.error_traces:
            prompt_parts.append("\nERROR TRACE DETAILS:")
            for trace in traces.error_traces[:5]:
                prompt_parts.append(
                    f"\n  Trace ID: {trace.trace_id}"
                    f"\n  Root Operation: {trace.root_operation}"
                    f"\n  Root Service: {trace.root_service}"
                    f"\n  Total Duration: {trace.total_duration_ms:.0f}ms"
                    f"\n  Spans: {trace.span_count} total, {trace.error_span_count} with errors"
                    f"\n  Services Involved: {' → '.join(trace.services_involved)}"
                )
                # Show error spans
                error_spans = [s for s in trace.spans if s.is_error][:3]
                for span in error_spans:
                    prompt_parts.append(
                        f"\n  ERROR SPAN:"
                        f"\n    Service: {span.service_name}"
                        f"\n    Operation: {span.operation_name}"
                        f"\n    Duration: {span.duration_ms:.0f}ms"
                        f"\n    Error Tags: {json.dumps({k: v for k, v in span.tags.items() if 'error' in k.lower() or 'status' in k.lower()})}"
                    )

        # ---- Section 5: Request for JSON Response ----
        prompt_parts.append("\n" + "=" * 60)
        prompt_parts.append(
            "Based on the telemetry data above, perform a root cause analysis "
            "for the user's question. Provide your response as valid JSON "
            "matching the schema in your system instructions."
        )

        return "\n".join(prompt_parts)

    def _parse_llm_response(
        self,
        raw_response: str,
        request: AnalysisRequest,
        start_time: float,
    ) -> RootCauseAnalysis:
        """
        Parse the LLM's JSON response into a RootCauseAnalysis model.
        
        The LLM may not always return perfect JSON, so we handle:
          - JSON embedded in markdown code blocks (```json ... ```)
          - Extra text before/after the JSON
          - Missing optional fields
          - Malformed JSON (falls back to text extraction)
        
        Args:
            raw_response: Raw text from the LLM
            request: The original analysis request
            start_time: Unix timestamp when analysis started (for duration calc)
        
        Returns:
            A populated RootCauseAnalysis model
        """
        analysis_id = str(uuid.uuid4())
        duration = time.time() - start_time

        # ---- Step 1: Extract JSON from the response ----
        json_str = raw_response

        # Handle markdown code blocks: ```json\n{...}\n```
        if "```json" in raw_response:
            try:
                start = raw_response.index("```json") + 7
                end = raw_response.index("```", start)
                json_str = raw_response[start:end].strip()
            except ValueError:
                pass
        elif "```" in raw_response:
            try:
                start = raw_response.index("```") + 3
                end = raw_response.index("```", start)
                json_str = raw_response[start:end].strip()
            except ValueError:
                pass
        else:
            # Try to find JSON object boundaries in the text
            start_brace = raw_response.find("{")
            end_brace = raw_response.rfind("}")
            if start_brace != -1 and end_brace != -1:
                json_str = raw_response[start_brace : end_brace + 1]

        # ---- Step 2: Parse the JSON ----
        try:
            parsed = json.loads(json_str)

            # Map severity string to enum
            severity_str = parsed.get("severity", "medium").lower()
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = Severity.MEDIUM

            return RootCauseAnalysis(
                analysis_id=analysis_id,
                user_query=request.query,
                severity=severity,
                status=AnalysisStatus.COMPLETED,
                root_cause_summary=parsed.get("root_cause_summary", ""),
                detailed_analysis=parsed.get("detailed_analysis", ""),
                recommended_actions=parsed.get("recommended_actions", []),
                affected_components=parsed.get("affected_components", []),
                metrics_evidence=parsed.get("metrics_evidence", []),
                log_evidence=parsed.get("log_evidence", []),
                trace_evidence=parsed.get("trace_evidence", []),
                confidence_score=float(parsed.get("confidence_score", 0.5)),
                llm_model_used=config.aws.bedrock_model_id,
                analysis_duration_seconds=round(duration, 2),
                raw_llm_response=raw_response,
            )

        except (json.JSONDecodeError, KeyError) as e:
            # ---- Fallback: LLM didn't return valid JSON ----
            logger.warning(f"Failed to parse LLM JSON response: {e}")
            logger.warning(f"Raw response: {raw_response[:500]}")

            # Use the raw text as the detailed analysis
            return RootCauseAnalysis(
                analysis_id=analysis_id,
                user_query=request.query,
                severity=Severity.MEDIUM,
                status=AnalysisStatus.COMPLETED,
                root_cause_summary="Analysis complete (see detailed analysis)",
                detailed_analysis=raw_response,
                recommended_actions=[
                    "Review the detailed analysis above for specific recommendations"
                ],
                confidence_score=0.3,  # Lower confidence due to parse failure
                llm_model_used=config.aws.bedrock_model_id,
                analysis_duration_seconds=round(duration, 2),
                raw_llm_response=raw_response,
            )

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Main entry point: perform a complete RCA for the given request.
        
        This is the function called by the Lambda handler.
        
        Process:
          1. Collect telemetry from all three backends
          2. Build structured prompt from telemetry data
          3. Invoke Bedrock LLM for analysis
          4. Parse response into RootCauseAnalysis model
          5. Return complete AnalysisResponse
        
        Args:
            request: AnalysisRequest from the user
        
        Returns:
            AnalysisResponse with RCA and raw telemetry data
        """
        # Assign request ID if not provided
        if not request.request_id:
            request.request_id = str(uuid.uuid4())

        logger.info(
            f"Starting RCA for request {request.request_id}: '{request.query}'"
        )

        start_time = time.time()

        # ---- Phase 1: Collect all telemetry ----
        logger.info("=== Phase 1: Telemetry Collection ===")
        metrics_snapshot, log_snapshot, trace_snapshot, collection_errors = (
            self._collect_telemetry(request)
        )

        # ---- Phase 2: Check if there's actually anything to analyze ----
        # If no anomalies were detected, we can still run analysis
        # but we'll note that in the response
        has_any_issues = (
            metrics_snapshot.has_high_cpu
            or metrics_snapshot.has_high_memory
            or metrics_snapshot.has_pod_restarts
            or metrics_snapshot.has_high_error_rate
            or log_snapshot.total_logs_found > 0
            or trace_snapshot.has_error_traces
            or trace_snapshot.has_high_latency
        )

        logger.info(
            f"Telemetry collected. Has issues: {has_any_issues}. "
            f"Collection errors: {len(collection_errors)}"
        )

        # ---- Phase 3: Build the LLM prompt ----
        logger.info("=== Phase 2: Building LLM Prompt ===")
        prompt = self._build_analysis_prompt(
            request=request,
            metrics=metrics_snapshot,
            logs=log_snapshot,
            traces=trace_snapshot,
        )
        logger.debug(f"Prompt length: {len(prompt)} characters")

        # ---- Phase 4: Invoke Bedrock LLM ----
        logger.info("=== Phase 3: Invoking AWS Bedrock LLM ===")
        raw_response = self.llm.invoke(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=0.1,  # Low temperature for factual, deterministic RCA
        )

        # ---- Phase 5: Parse and structure the LLM response ----
        logger.info("=== Phase 4: Parsing LLM Response ===")
        if raw_response:
            rca = self._parse_llm_response(raw_response, request, start_time)
        else:
            # LLM invocation failed completely
            rca = RootCauseAnalysis(
                analysis_id=str(uuid.uuid4()),
                user_query=request.query,
                severity=Severity.MEDIUM,
                status=AnalysisStatus.FAILED,
                root_cause_summary="Analysis failed: Unable to invoke AI model",
                detailed_analysis=(
                    "The AWS Bedrock LLM could not be invoked. "
                    "This may be due to IAM permission issues, throttling, "
                    "or network connectivity problems. "
                    f"Collection errors: {'; '.join(collection_errors)}"
                ),
                recommended_actions=[
                    "Check IAM role has bedrock:InvokeModel permission",
                    "Verify the model ID is valid and accessible in your region",
                    "Check AWS Bedrock quotas and request limits",
                ],
                confidence_score=0.0,
                llm_model_used=config.aws.bedrock_model_id,
                analysis_duration_seconds=round(time.time() - start_time, 2),
            )

        logger.info(
            f"RCA complete: {rca.root_cause_summary[:100]}... "
            f"[{rca.analysis_duration_seconds}s, severity={rca.severity}]"
        )

        # ---- Phase 6: Automated Remediation & Notifications ----
        logger.info("=== Phase 6: Triggering Remediation/Notifications ===")
        try:
            from lambda_.integrations.remediation import RemediationWorkflow
            remediation = RemediationWorkflow()
            integration_results = remediation.execute(rca)
            logger.info(f"Integration results: {integration_results}")
        except Exception as e:
            logger.error(f"Failed to execute remediation workflow: {e}")

        # ---- Return full response with telemetry data ----
        return AnalysisResponse(
            request_id=request.request_id,
            rca=rca,
            metrics_snapshot=metrics_snapshot,
            log_snapshot=log_snapshot,
            trace_snapshot=trace_snapshot,
            collection_errors=collection_errors,
        )


# ============================================================
# Standalone testing
# ============================================================
if __name__ == "__main__":
    from shared.models import AnalysisRequest

    analyzer = RCAAnalyzer()
    req = AnalysisRequest(
        query="Why is the checkout service returning 500 errors?",
        target_service="checkout",
        target_namespace="production",
        lookback_minutes=30,
    )

    print("Running RCA analysis...")
    response = analyzer.analyze(req)

    print("\n========== ROOT CAUSE ANALYSIS ==========")
    print(f"Summary: {response.rca.root_cause_summary}")
    print(f"Severity: {response.rca.severity}")
    print(f"Confidence: {response.rca.confidence_score}")
    print(f"\nDetailed Analysis:\n{response.rca.detailed_analysis}")
    print(f"\nRecommended Actions:")
    for action in response.rca.recommended_actions:
        print(f"  {action}")
