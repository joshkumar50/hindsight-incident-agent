"""
=============================================================
shared/models.py - Pydantic Data Models
=============================================================
Purpose: Define strict data models for all data flowing between
         collectors, the AI engine, Lambda, and the Streamlit UI.
         Using Pydantic ensures type safety and clean serialization
         (important for passing data through Lambda JSON events).
=============================================================
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Enums - Define fixed categories for severity, status, etc.
# ============================================================

class Severity(str, Enum):
    """Severity levels for incidents and findings."""
    CRITICAL = "critical"   # Immediate action required (e.g., pod crash loop)
    HIGH = "high"           # Significant impact (e.g., high error rate)
    MEDIUM = "medium"       # Moderate impact (e.g., elevated latency)
    LOW = "low"             # Minor issues (e.g., warning-level log events)
    INFO = "info"           # Informational, no action needed


class AnalysisStatus(str, Enum):
    """Status of an RCA analysis run."""
    PENDING = "pending"         # Queued but not yet started
    IN_PROGRESS = "in_progress" # Currently collecting data
    COMPLETED = "completed"     # Analysis finished successfully
    FAILED = "failed"           # Analysis encountered an error
    NO_ISSUE = "no_issue"       # No problems found


# ============================================================
# Metrics Models (Prometheus)
# ============================================================

class MetricDataPoint(BaseModel):
    """A single time-series data point from Prometheus."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)


class MetricSeries(BaseModel):
    """A named metric series with multiple data points."""
    metric_name: str
    description: str = ""
    unit: str = ""
    # Key labels that identify this series (pod, namespace, container, etc.)
    labels: Dict[str, str] = Field(default_factory=dict)
    data_points: List[MetricDataPoint] = Field(default_factory=list)
    # Computed summary stats for the LLM context window (avoids sending raw arrays)
    avg_value: Optional[float] = None
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    latest_value: Optional[float] = None


class MetricsSnapshot(BaseModel):
    """Complete snapshot of Prometheus metrics for a given time window."""
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    lookback_minutes: int = 30
    # CPU / Memory / Network / Disk metrics grouped by category
    cpu_metrics: List[MetricSeries] = Field(default_factory=list)
    memory_metrics: List[MetricSeries] = Field(default_factory=list)
    pod_status_metrics: List[MetricSeries] = Field(default_factory=list)
    http_error_metrics: List[MetricSeries] = Field(default_factory=list)
    custom_metrics: List[MetricSeries] = Field(default_factory=list)
    # High-level flags for the LLM to quickly triage
    has_high_cpu: bool = False
    has_high_memory: bool = False
    has_pod_restarts: bool = False
    has_high_error_rate: bool = False
    # Human-readable summary for the LLM prompt
    summary: str = ""


# ============================================================
# Log Models (EFK Stack / Elasticsearch)
# ============================================================

class LogEntry(BaseModel):
    """A single log entry retrieved from Elasticsearch."""
    timestamp: datetime
    level: str = "INFO"     # DEBUG, INFO, WARN, ERROR, FATAL
    message: str
    pod_name: str = ""
    namespace: str = ""
    container: str = ""
    service: str = ""
    # Raw fields from Elasticsearch (for additional metadata)
    raw_fields: Dict[str, Any] = Field(default_factory=dict)


class LogSnapshot(BaseModel):
    """Aggregated log data from Elasticsearch / EFK stack."""
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    lookback_minutes: int = 30
    total_logs_found: int = 0
    error_logs: List[LogEntry] = Field(default_factory=list)
    warning_logs: List[LogEntry] = Field(default_factory=list)
    # Top N most frequent error messages (deduplicated)
    top_errors: List[Dict[str, Any]] = Field(default_factory=list)
    # Affected services and pods extracted from logs
    affected_services: List[str] = Field(default_factory=list)
    affected_pods: List[str] = Field(default_factory=list)
    # High-level flags
    has_oom_errors: bool = False          # Out-of-memory kills
    has_crash_loops: bool = False         # CrashLoopBackOff events
    has_connection_errors: bool = False   # Network / DB connection failures
    # Concise summary for LLM prompt
    summary: str = ""


# ============================================================
# Trace Models (Jaeger)
# ============================================================

class TraceSpan(BaseModel):
    """A single span within a distributed trace."""
    span_id: str
    trace_id: str
    operation_name: str
    service_name: str
    start_time: datetime
    duration_ms: float       # Duration in milliseconds
    is_error: bool = False
    tags: Dict[str, Any] = Field(default_factory=dict)
    logs: List[Dict[str, Any]] = Field(default_factory=list)  # Span-level logs


class Trace(BaseModel):
    """A complete distributed trace containing multiple spans."""
    trace_id: str
    root_operation: str = ""    # Entry point operation (e.g., HTTP GET /api/users)
    root_service: str = ""      # Entry point service
    total_duration_ms: float = 0.0
    span_count: int = 0
    error_span_count: int = 0
    spans: List[TraceSpan] = Field(default_factory=list)
    # Computed: services involved in this trace
    services_involved: List[str] = Field(default_factory=list)
    has_errors: bool = False


class TraceSnapshot(BaseModel):
    """Aggregated trace data from Jaeger."""
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    lookback_minutes: int = 30
    total_traces_found: int = 0
    error_traces: List[Trace] = Field(default_factory=list)
    slow_traces: List[Trace] = Field(default_factory=list)    # Above p95 latency
    # Affected services derived from error traces
    affected_services: List[str] = Field(default_factory=list)
    # P50/P95/P99 latency across all traces
    p50_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None
    # Flags
    has_high_latency: bool = False
    has_error_traces: bool = False
    # Concise summary for LLM prompt
    summary: str = ""


# ============================================================
# RCA Models - The final AI-generated analysis
# ============================================================

class RootCauseAnalysis(BaseModel):
    """
    The complete root cause analysis generated by the AI agent.
    This is the primary output returned to the user.
    """
    # Unique identifier for this analysis run
    analysis_id: str
    # The original user question that triggered the analysis
    user_query: str
    # When this analysis was performed
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    # Overall severity of the issue found
    severity: Severity = Severity.INFO
    # Status of this analysis
    status: AnalysisStatus = AnalysisStatus.COMPLETED

    # ---- AI-Generated Content ----
    # One-line summary of the root cause
    root_cause_summary: str = ""
    # Detailed explanation of what went wrong and why
    detailed_analysis: str = ""
    # Step-by-step remediation steps
    recommended_actions: List[str] = Field(default_factory=list)
    # Affected components identified by the AI
    affected_components: List[str] = Field(default_factory=list)

    # ---- Evidence ----
    # Which metrics triggered the analysis
    metrics_evidence: List[str] = Field(default_factory=list)
    # Key log lines that indicate the issue
    log_evidence: List[str] = Field(default_factory=list)
    # Trace IDs that show the problematic request paths
    trace_evidence: List[str] = Field(default_factory=list)

    # ---- Confidence & Metadata ----
    # AI confidence in the analysis (0.0 - 1.0)
    confidence_score: float = 0.0
    # The LLM model used for analysis
    llm_model_used: str = ""
    # Time taken to complete the full analysis (seconds)
    analysis_duration_seconds: float = 0.0
    # Raw LLM response (for debugging)
    raw_llm_response: str = ""


class AnalysisRequest(BaseModel):
    """
    A user's request for root cause analysis.
    This is the event payload sent to Lambda.
    """
    # The user's natural language question
    query: str
    # Optional: focus the analysis on a specific service/namespace
    target_service: Optional[str] = None
    target_namespace: Optional[str] = None
    # How many minutes back to look (defaults to Lambda config)
    lookback_minutes: Optional[int] = None
    # Optional: specific trace ID if the user knows it
    trace_id: Optional[str] = None
    # Request source (streamlit, api, etc.)
    source: str = "streamlit"
    # Unique request ID for deduplication
    request_id: str = ""


class AnalysisResponse(BaseModel):
    """
    Complete response from the Lambda RCA function.
    Contains the analysis plus raw telemetry data for the UI.
    """
    request_id: str
    rca: RootCauseAnalysis
    # Raw collected telemetry (for display in Streamlit tabs)
    metrics_snapshot: Optional[MetricsSnapshot] = None
    log_snapshot: Optional[LogSnapshot] = None
    trace_snapshot: Optional[TraceSnapshot] = None
    # Any errors that occurred during data collection
    collection_errors: List[str] = Field(default_factory=list)


# ============================================================
# Human Feedback & Platform Exception Models
# ============================================================

class FeedbackRequest(BaseModel):
    """
    Operator feedback on AI-generated runbooks / recommendations.
    Used for Reinforcement Learning and Memory Evolution.
    """
    incident_id: str
    suggestion_id: Optional[str] = None
    verdict: str  # "accept" | "reject" | "modify"
    corrected_playbook: Optional[str] = None
    user: str = "operator"


class HindsightIncidentAgentException(Exception):
    """
    Standard exception for platform service errors across the Hindsight platform.
    Ensures structured, traceable error responses instead of bare HTTPExceptions.
    """
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

