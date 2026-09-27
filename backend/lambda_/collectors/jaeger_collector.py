"""
=============================================================
lambda/collectors/jaeger_collector.py
=============================================================
Purpose: Collect distributed traces from Jaeger for AI root
         cause analysis.

Jaeger is used for distributed tracing across EKS microservices.
When a request travels through multiple services, Jaeger records
each "hop" as a span, and all spans with the same trace ID
form a complete trace tree.

This collector uses Jaeger's HTTP Query API (v3) to:
  - Find error traces (spans with error=true tags)
  - Find slow traces (above P95 latency threshold)
  - Retrieve full trace details including span logs
  - Identify which services have problematic spans

Jaeger Query API docs: https://www.jaegertracing.io/docs/1.50/apis/
=============================================================
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import config
from shared.models import Trace, TraceSnapshot, TraceSpan

# ---- Logging Setup ----
logger = logging.getLogger(__name__)


class JaegerCollector:
    """
    Collects distributed traces from Jaeger's HTTP Query API.
    
    The Jaeger Query API provides REST endpoints for:
      GET /api/services          - List all instrumented services
      GET /api/traces            - Search for traces with filters
      GET /api/traces/{trace_id} - Get a specific trace by ID
    
    All timestamps in Jaeger's API are in microseconds (µs).
    """

    def __init__(
        self,
        jaeger_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the Jaeger collector.
        
        Args:
            jaeger_url: Override Jaeger URL (falls back to config)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = (jaeger_url or config.jaeger.url).rstrip("/")
        self.api_url = f"{self.base_url}{config.jaeger.api_base}"
        self.timeout = timeout
        self.max_traces = config.jaeger.max_traces

        # HTTP session with retry logic
        self.session = self._create_session()
        logger.info(f"JaegerCollector initialized: {self.base_url}")

    def _create_session(self) -> requests.Session:
        """Create HTTP session with automatic retry on transient failures."""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """
        Make a GET request to the Jaeger Query API.
        
        Args:
            endpoint: API path (e.g., "/traces", "/services")
            params: Query parameters dict
        
        Returns:
            Parsed JSON response or None on failure
        """
        url = f"{self.api_url}{endpoint}"
        try:
            response = self.session.get(
                url, params=params or {}, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Jaeger API request failed [{url}]: {e}")
            return None

    def get_services(self) -> List[str]:
        """
        List all services currently registered in Jaeger.
        
        Returns a list of service names that are sending traces.
        Used to enumerate services for targeted analysis.
        """
        data = self._get("/services")
        if not data:
            return []
        # Jaeger returns {"data": ["service-a", "service-b", ...]}
        services = data.get("data", [])
        # Filter out the Jaeger UI itself
        services = [s for s in services if s != "jaeger-query"]
        logger.info(f"Found {len(services)} services in Jaeger: {services}")
        return services

    def _parse_span(self, span_data: Dict, process_map: Dict) -> TraceSpan:
        """
        Convert a raw Jaeger span JSON object into a TraceSpan model.
        
        Jaeger span format:
        {
          "traceID": "abc123",
          "spanID": "def456",
          "operationName": "HTTP GET /api/users",
          "startTime": 1705318200000000,  # microseconds since epoch
          "duration": 150000,              # microseconds
          "processID": "p1",
          "tags": [{"key": "error", "type": "bool", "value": true}, ...],
          "logs": [{"timestamp": ..., "fields": [...]}]
        }
        """
        # ---- Extract basic fields ----
        trace_id = span_data.get("traceID", "")
        span_id = span_data.get("spanID", "")
        operation = span_data.get("operationName", "")

        # ---- Convert timestamps (Jaeger uses microseconds) ----
        start_us = span_data.get("startTime", 0)
        start_time = datetime.utcfromtimestamp(start_us / 1_000_000)

        # Duration in microseconds → milliseconds
        duration_us = span_data.get("duration", 0)
        duration_ms = duration_us / 1000.0

        # ---- Extract tags as a flat dict ----
        # Jaeger stores tags as [{key, type, value}, ...] arrays
        tags: Dict[str, Any] = {}
        is_error = False
        for tag in span_data.get("tags", []):
            key = tag.get("key", "")
            value = tag.get("value")
            tags[key] = value
            # Standard OpenTelemetry error tag
            if key == "error" and value is True:
                is_error = True
            # HTTP status code >= 500 indicates server error
            if key == "http.status_code" and isinstance(value, int) and value >= 500:
                is_error = True

        # ---- Extract span-level logs ----
        span_logs = []
        for log_event in span_data.get("logs", []):
            log_ts = log_event.get("timestamp", 0)
            fields = {
                f["key"]: f["value"]
                for f in log_event.get("fields", [])
            }
            span_logs.append({"timestamp": log_ts, "fields": fields})

        # ---- Get service name from process map ----
        process_id = span_data.get("processID", "")
        service_name = process_map.get(process_id, {}).get("serviceName", "unknown")

        return TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation,
            service_name=service_name,
            start_time=start_time,
            duration_ms=duration_ms,
            is_error=is_error,
            tags=tags,
            logs=span_logs,
        )

    def _parse_trace(self, trace_data: Dict) -> Optional[Trace]:
        """
        Convert a raw Jaeger trace JSON into a structured Trace model.
        
        Jaeger returns traces in this format:
        {
          "traceID": "abc123",
          "spans": [...],
          "processes": {"p1": {"serviceName": "api-server", "tags": [...]}}
        }
        """
        try:
            trace_id = trace_data.get("traceID", "")
            spans_data = trace_data.get("spans", [])

            # Build process map: processID → {serviceName, tags}
            # This maps each span's processID to its service name
            processes = trace_data.get("processes", {})
            process_map = {
                pid: proc for pid, proc in processes.items()
            }

            # ---- Parse all spans ----
            spans: List[TraceSpan] = []
            for span_data in spans_data:
                span = self._parse_span(span_data, process_map)
                spans.append(span)

            if not spans:
                return None

            # ---- Compute trace-level stats ----
            # Root span: the span with no parent (the entry point)
            root_span = spans[0]  # Usually first span is root
            # Sort by start time to find actual root
            spans.sort(key=lambda s: s.start_time)
            root_span = spans[0]

            error_spans = [s for s in spans if s.is_error]
            services_involved = list(
                set(s.service_name for s in spans if s.service_name != "unknown")
            )

            # Total duration = end of last span - start of first span
            if len(spans) > 1:
                last_end = max(
                    s.start_time.timestamp() * 1000 + s.duration_ms
                    for s in spans
                )
                first_start = spans[0].start_time.timestamp() * 1000
                total_duration_ms = last_end - first_start
            else:
                total_duration_ms = spans[0].duration_ms

            return Trace(
                trace_id=trace_id,
                root_operation=root_span.operation_name,
                root_service=root_span.service_name,
                total_duration_ms=total_duration_ms,
                span_count=len(spans),
                error_span_count=len(error_spans),
                spans=spans,
                services_involved=services_involved,
                has_errors=len(error_spans) > 0,
            )

        except Exception as e:
            logger.warning(f"Failed to parse trace: {e}")
            return None

    def search_traces(
        self,
        service: str,
        start: datetime,
        end: datetime,
        has_error: bool = False,
        min_duration_ms: Optional[float] = None,
        max_results: int = 50,
    ) -> List[Trace]:
        """
        Search for traces in Jaeger matching given criteria.
        
        Args:
            service: Service name to search traces for
            start: Start of the time window
            end: End of the time window
            has_error: If True, only return traces with errors
            min_duration_ms: Only return traces slower than this
            max_results: Maximum number of traces to return
        
        Returns:
            List of parsed Trace objects
        """
        # Jaeger API uses microseconds for time parameters
        params: Dict[str, Any] = {
            "service": service,
            "start": int(start.timestamp() * 1_000_000),  # → microseconds
            "end": int(end.timestamp() * 1_000_000),
            "limit": max_results,
        }

        # Filter by error tag if requested
        if has_error:
            params["tags"] = '{"error":"true"}'

        # Filter by minimum duration (convert ms → µs)
        if min_duration_ms:
            params["minDuration"] = f"{int(min_duration_ms * 1000)}us"

        data = self._get("/traces", params=params)
        if not data:
            return []

        # Jaeger returns {"data": [trace_obj, ...], "total": N, ...}
        traces_data = data.get("data", [])
        traces = []
        for trace_data in traces_data:
            trace = self._parse_trace(trace_data)
            if trace:
                traces.append(trace)

        logger.info(
            f"Found {len(traces)} traces for service={service} error={has_error}"
        )
        return traces

    def get_trace_by_id(self, trace_id: str) -> Optional[Trace]:
        """
        Retrieve a specific trace by its ID.
        
        Useful when the user provides a specific trace ID in their query
        (e.g., "what happened in trace abc123?").
        
        Args:
            trace_id: The Jaeger trace ID (16 or 32 hex characters)
        
        Returns:
            Parsed Trace object or None if not found
        """
        data = self._get(f"/traces/{trace_id}")
        if not data:
            return None
        traces_data = data.get("data", [])
        if not traces_data:
            return None
        return self._parse_trace(traces_data[0])

    def compute_latency_percentiles(
        self, traces: List[Trace]
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Compute P50, P95, P99 latency from a list of traces.
        
        Returns:
            Tuple of (p50_ms, p95_ms, p99_ms)
        """
        if not traces:
            return None, None, None

        durations = sorted(t.total_duration_ms for t in traces)
        n = len(durations)

        def percentile(data: List[float], p: float) -> float:
            """Linear interpolation percentile."""
            idx = (p / 100) * (len(data) - 1)
            lower = int(idx)
            upper = min(lower + 1, len(data) - 1)
            fraction = idx - lower
            return data[lower] + fraction * (data[upper] - data[lower])

        p50 = percentile(durations, 50)
        p95 = percentile(durations, 95)
        p99 = percentile(durations, 99)

        return round(p50, 2), round(p95, 2), round(p99, 2)

    def collect_all_traces(
        self,
        lookback_minutes: int = 30,
        namespace: Optional[str] = None,
        service: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> TraceSnapshot:
        """
        Main entry point: collect all relevant traces and return
        a complete TraceSnapshot for the AI analysis engine.
        
        Strategy:
          1. If a specific trace_id is given, fetch that trace.
          2. Otherwise, get the list of services from Jaeger.
          3. For each service, search for error traces.
          4. Also search for slow traces (above P95 threshold).
          5. Compute latency percentiles.
          6. Build health flags and summary.
        
        Args:
            lookback_minutes: How far back to look
            namespace: EKS namespace (used to filter service names if known)
            service: Specific service to focus on
            trace_id: Specific trace ID to fetch
        
        Returns:
            TraceSnapshot with error/slow traces, latency stats, and flags
        """
        end = datetime.utcnow()
        start = end - timedelta(minutes=lookback_minutes)

        logger.info(
            f"Collecting traces [{start.isoformat()} -> {end.isoformat()}] "
            f"service={service or 'all'} trace_id={trace_id or 'none'}"
        )

        # ---- Case 1: Specific trace ID requested ----
        if trace_id:
            trace = self.get_trace_by_id(trace_id)
            if trace:
                snapshot = TraceSnapshot(
                    lookback_minutes=lookback_minutes,
                    total_traces_found=1,
                    error_traces=[trace] if trace.has_errors else [],
                    slow_traces=[],
                    affected_services=trace.services_involved,
                    has_error_traces=trace.has_errors,
                    summary=f"Retrieved specific trace {trace_id}: "
                            f"{trace.root_operation} "
                            f"({trace.total_duration_ms:.0f}ms, "
                            f"{'ERROR' if trace.has_errors else 'OK'})",
                )
                return snapshot

        # ---- Case 2: Discover all services ----
        if service:
            # Focus on a specific service
            services_to_query = [service]
        else:
            # Query all services known to Jaeger
            services_to_query = self.get_services()
            if not services_to_query:
                logger.warning("No services found in Jaeger")
                return TraceSnapshot(
                    lookback_minutes=lookback_minutes,
                    summary="No services found in Jaeger. Is tracing enabled?",
                )

        # ---- Collect error and slow traces per service ----
        all_error_traces: List[Trace] = []
        all_traces_for_latency: List[Trace] = []

        for svc in services_to_query[:10]:  # Limit to 10 services to avoid timeout
            # Fetch error traces for this service
            error_traces = self.search_traces(
                service=svc,
                start=start,
                end=end,
                has_error=True,
                max_results=20,
            )
            all_error_traces.extend(error_traces)

            # Fetch all traces (for latency computation)
            all_traces = self.search_traces(
                service=svc,
                start=start,
                end=end,
                has_error=False,
                max_results=50,
            )
            all_traces_for_latency.extend(all_traces)

        # ---- Compute latency percentiles ----
        p50, p95, p99 = self.compute_latency_percentiles(all_traces_for_latency)

        # ---- Find slow traces (above P95 threshold) ----
        slow_traces = []
        if p95:
            slow_traces = [
                t for t in all_traces_for_latency
                if t.total_duration_ms > p95
                and not t.has_errors  # Error traces already captured separately
            ]

        # ---- Extract affected services from error traces ----
        affected_services = list(
            set(
                svc
                for trace in all_error_traces
                for svc in trace.services_involved
            )
        )

        # ---- Health flags ----
        has_error_traces = len(all_error_traces) > 0
        has_high_latency = p95 is not None and p95 > 2000  # 2 second P95 threshold

        # ---- Build summary for the LLM ----
        summary_parts = []
        summary_parts.append(
            f"Collected traces from {len(services_to_query)} service(s) "
            f"over the last {lookback_minutes} minutes."
        )
        if p50 and p95 and p99:
            summary_parts.append(
                f"Latency percentiles: P50={p50:.0f}ms, P95={p95:.0f}ms, P99={p99:.0f}ms"
            )
        if all_error_traces:
            summary_parts.append(
                f"⚠️ {len(all_error_traces)} ERROR traces found across: "
                f"{', '.join(affected_services[:5])}"
            )
            # Highlight the most common error operation
            ops = [t.root_operation for t in all_error_traces]
            if ops:
                most_common = max(set(ops), key=ops.count)
                summary_parts.append(
                    f"   Most common error operation: '{most_common}' "
                    f"({ops.count(most_common)} times)"
                )
        if slow_traces:
            summary_parts.append(
                f"⚠️ {len(slow_traces)} slow traces found (above {p95:.0f}ms P95)"
            )
        if not all_error_traces and not slow_traces:
            summary_parts.append("No error or anomalously slow traces detected.")

        snapshot = TraceSnapshot(
            lookback_minutes=lookback_minutes,
            total_traces_found=len(all_traces_for_latency) + len(all_error_traces),
            error_traces=all_error_traces[:20],   # Cap for LLM context
            slow_traces=slow_traces[:10],
            affected_services=affected_services,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            has_high_latency=has_high_latency,
            has_error_traces=has_error_traces,
            summary="\n".join(summary_parts),
        )

        logger.info(f"Trace snapshot built: {snapshot.summary[:200]}")
        return snapshot


# ============================================================
# Standalone testing
# ============================================================
if __name__ == "__main__":
    collector = JaegerCollector(jaeger_url="http://localhost:16686")
    services = collector.get_services()
    print(f"Services in Jaeger: {services}")
    snapshot = collector.collect_all_traces(lookback_minutes=30)
    print("\n========== TRACES SUMMARY ==========")
    print(snapshot.summary)
