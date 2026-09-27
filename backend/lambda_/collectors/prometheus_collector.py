"""
=============================================================
lambda/collectors/prometheus_collector.py
=============================================================
Purpose: Collect metrics from Prometheus (deployed in EKS)
         to feed into the AI root cause analysis engine.

Prometheus is used here as the metrics backend for:
  - Pod CPU / Memory utilization
  - HTTP request error rates (4xx/5xx)
  - Pod restart counts (crash loops)
  - Node resource utilization
  - Custom application metrics

This collector uses Prometheus's HTTP Query API (v1) to
run PromQL queries and return structured MetricSeries objects.
=============================================================
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import shared config and data models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import config
from shared.models import MetricDataPoint, MetricSeries, MetricsSnapshot

# ---- Logging Setup ----
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================
# PrometheusCollector Class
# ============================================================

class PrometheusCollector:
    """
    Collects metrics from Prometheus via its HTTP API (PromQL).
    
    This class provides high-level methods that run curated PromQL
    queries for EKS observability and return structured data suitable
    for the AI/LLM context window.
    """

    def __init__(self, prometheus_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize the Prometheus collector.
        
        Args:
            prometheus_url: Override the URL from config (useful for testing)
            timeout: HTTP request timeout in seconds
        """
        # Use provided URL or fall back to the config singleton
        self.base_url = (prometheus_url or config.prometheus.url).rstrip("/")
        self.timeout = timeout

        # Configure HTTP session with retry logic
        # Retries are important because Prometheus may be temporarily overloaded
        self.session = self._create_session()

        logger.info(f"PrometheusCollector initialized with URL: {self.base_url}")

    def _create_session(self) -> requests.Session:
        """
        Create a requests.Session with automatic retry on transient failures.
        Retries on connection errors, 500, 502, 503, 504 responses.
        """
        session = requests.Session()
        # Retry up to 3 times with exponential backoff (0.3s, 0.6s, 1.2s)
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _query_range(
        self,
        promql: str,
        start: datetime,
        end: datetime,
        step: str = "60s",
    ) -> List[Dict[str, Any]]:
        """
        Execute a PromQL range query against Prometheus.
        
        Args:
            promql: The PromQL expression to evaluate
            start: Start of the time range
            end: End of the time range (usually now)
            step: Resolution step (e.g., "60s" = one data point per minute)
        
        Returns:
            List of result series from Prometheus (raw JSON)
        
        Raises:
            requests.RequestException: On HTTP/network failures
        """
        # Prometheus range query API endpoint
        url = f"{self.base_url}/api/v1/query_range"

        params = {
            "query": promql,
            "start": start.timestamp(),   # Unix timestamp
            "end": end.timestamp(),        # Unix timestamp
            "step": step,
        }

        logger.debug(f"Prometheus query: {promql[:100]}...")

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()  # Raise on 4xx/5xx

            data = response.json()

            # Prometheus returns {"status": "success", "data": {"result": [...]}}
            if data.get("status") != "success":
                logger.warning(f"Prometheus query returned non-success: {data}")
                return []

            return data.get("data", {}).get("result", [])

        except requests.RequestException as e:
            logger.error(f"Prometheus query failed: {e}")
            return []

    def _query_instant(self, promql: str) -> List[Dict[str, Any]]:
        """
        Execute a PromQL instant query (current value only).
        
        Args:
            promql: The PromQL expression to evaluate at current time
        
        Returns:
            List of result vectors from Prometheus
        """
        url = f"{self.base_url}/api/v1/query"
        params = {"query": promql}

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success":
                return []
            return data.get("data", {}).get("result", [])
        except requests.RequestException as e:
            logger.error(f"Prometheus instant query failed: {e}")
            return []

    def _parse_range_result(
        self,
        raw_results: List[Dict],
        metric_name: str,
        description: str = "",
        unit: str = "",
    ) -> List[MetricSeries]:
        """
        Convert raw Prometheus JSON result into structured MetricSeries objects.
        
        Prometheus range_query returns:
          [
            {
              "metric": {"__name__": "...", "pod": "...", "namespace": "..."},
              "values": [[timestamp, "value"], ...]
            },
            ...
          ]
        
        This method converts each result into a MetricSeries with
        computed statistics (avg, max, min, latest) for LLM summarization.
        """
        series_list = []

        for result in raw_results:
            # Extract label dictionary (pod name, namespace, container, etc.)
            labels = result.get("metric", {})
            raw_values = result.get("values", [])

            # Convert raw [timestamp, value_str] pairs to MetricDataPoint objects
            data_points = []
            for ts, val_str in raw_values:
                try:
                    data_points.append(
                        MetricDataPoint(
                            timestamp=datetime.utcfromtimestamp(float(ts)),
                            value=float(val_str),
                            labels=labels,
                        )
                    )
                except (ValueError, TypeError):
                    # Skip NaN or malformed values from Prometheus
                    continue

            if not data_points:
                continue

            # Compute summary statistics so the LLM gets a compact representation
            values = [dp.value for dp in data_points]
            avg_val = sum(values) / len(values)
            max_val = max(values)
            min_val = min(values)
            latest_val = values[-1]  # Most recent data point

            series_list.append(
                MetricSeries(
                    metric_name=metric_name,
                    description=description,
                    unit=unit,
                    labels=labels,
                    data_points=data_points,
                    avg_value=round(avg_val, 4),
                    max_value=round(max_val, 4),
                    min_value=round(min_val, 4),
                    latest_value=round(latest_val, 4),
                )
            )

        return series_list

    # ============================================================
    # High-Level Metric Collection Methods
    # ============================================================

    def collect_cpu_metrics(
        self, start: datetime, end: datetime, namespace: Optional[str] = None
    ) -> List[MetricSeries]:
        """
        Collect CPU utilization metrics per pod.
        
        Uses irate() for responsive detection of CPU spikes.
        Filtered by namespace if provided.
        
        PromQL:
          irate(container_cpu_usage_seconds_total[5m])
          by (pod, namespace, container)
        """
        # Build namespace filter clause for PromQL
        ns_filter = f', namespace="{namespace}"' if namespace else ""

        # irate gives instant rate - better for detecting sudden spikes
        # We multiply by 100 to express as percentage
        promql = (
            f'100 * irate(container_cpu_usage_seconds_total'
            f'{{container!=""{ns_filter}}}[5m])'
        )

        raw_results = self._query_range(promql, start, end)
        series = self._parse_range_result(
            raw_results,
            metric_name="cpu_usage_percent",
            description="Container CPU usage percentage",
            unit="%",
        )
        logger.info(f"Collected {len(series)} CPU metric series")
        return series

    def collect_memory_metrics(
        self, start: datetime, end: datetime, namespace: Optional[str] = None
    ) -> List[MetricSeries]:
        """
        Collect memory utilization metrics per pod.
        
        Uses container_memory_working_set_bytes which is the most
        accurate representation of memory that cannot be reclaimed
        (excludes cache pages). Expressed as % of limit.
        
        PromQL:
          container_memory_working_set_bytes / container_spec_memory_limit_bytes * 100
        """
        ns_filter = f', namespace="{namespace}"' if namespace else ""

        # Memory usage as percentage of configured limit
        # This is what triggers OOM kills when it reaches 100%
        promql = (
            f'100 * container_memory_working_set_bytes'
            f'{{container!=""{ns_filter}}} / '
            f'container_spec_memory_limit_bytes'
            f'{{container!=""{ns_filter}}} > 0'
        )

        raw_results = self._query_range(promql, start, end)
        series = self._parse_range_result(
            raw_results,
            metric_name="memory_usage_percent",
            description="Container memory usage as % of configured limit",
            unit="%",
        )
        logger.info(f"Collected {len(series)} memory metric series")
        return series

    def collect_pod_restart_metrics(
        self, start: datetime, end: datetime, namespace: Optional[str] = None
    ) -> List[MetricSeries]:
        """
        Detect pod restart counts (indicating CrashLoopBackOff or OOM kills).
        
        kube_pod_container_status_restarts_total is a counter that
        increases each time a container restarts. We use increase()
        to get the count of restarts in the lookback window.
        
        PromQL:
          increase(kube_pod_container_status_restarts_total[30m]) > 0
        """
        ns_filter = f', namespace="{namespace}"' if namespace else ""

        promql = (
            f'increase(kube_pod_container_status_restarts_total'
            f'{{{ns_filter.lstrip(", ")}}}[30m]) > 0'
            if ns_filter
            else 'increase(kube_pod_container_status_restarts_total[30m]) > 0'
        )

        raw_results = self._query_range(promql, start, end)
        series = self._parse_range_result(
            raw_results,
            metric_name="pod_restart_count",
            description="Number of pod restarts in the lookback window",
            unit="restarts",
        )
        logger.info(f"Collected {len(series)} pod restart metric series")
        return series

    def collect_http_error_metrics(
        self, start: datetime, end: datetime, namespace: Optional[str] = None
    ) -> List[MetricSeries]:
        """
        Collect HTTP error rate metrics from Prometheus.
        
        This relies on the standard http_requests_total metric that
        most Prometheus client libraries expose. We compute the ratio
        of 5xx responses to total requests.
        
        If using Istio or NGINX, the metric names may differ:
          - Istio: istio_requests_total{response_code=~"5.."}
          - NGINX: nginx_http_requests_total{status=~"5.."}
        
        PromQL:
          rate(http_requests_total{status=~"5.."}[5m]) /
          rate(http_requests_total[5m]) * 100
        """
        ns_filter = f', namespace="{namespace}"' if namespace else ""

        # Error rate as percentage of total requests
        promql = (
            f'100 * sum by (service, namespace) ('
            f'  rate(http_requests_total'
            f'  {{status=~"5.."{ns_filter}}}[5m])'
            f') / sum by (service, namespace) ('
            f'  rate(http_requests_total{{{ns_filter.lstrip(", ")}}}[5m])'
            f') > 0'
            if ns_filter
            else (
                '100 * sum by (service) ('
                '  rate(http_requests_total{status=~"5.."}[5m])'
                ') / sum by (service) ('
                '  rate(http_requests_total[5m])'
                ') > 0'
            )
        )

        raw_results = self._query_range(promql, start, end)
        series = self._parse_range_result(
            raw_results,
            metric_name="http_error_rate_percent",
            description="HTTP 5xx error rate as % of total requests",
            unit="%",
        )
        logger.info(f"Collected {len(series)} HTTP error metric series")
        return series

    def collect_node_metrics(self, start: datetime, end: datetime) -> List[MetricSeries]:
        """
        Collect EKS node-level metrics (node pressure, disk, network).
        
        This catches infrastructure-level issues that affect all pods:
          - Node CPU saturation
          - Node memory pressure
          - Node disk pressure
        """
        # Node CPU utilization (all cores, as percentage)
        promql_cpu = (
            '100 - (avg by (instance, node) ('
            '  irate(node_cpu_seconds_total{mode="idle"}[5m])'
            ') * 100)'
        )

        # Node memory available as % of total (lower = worse)
        promql_mem = (
            '100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)'
        )

        cpu_series = self._parse_range_result(
            self._query_range(promql_cpu, start, end),
            metric_name="node_cpu_usage_percent",
            description="Node-level CPU utilization",
            unit="%",
        )

        mem_series = self._parse_range_result(
            self._query_range(promql_mem, start, end),
            metric_name="node_memory_usage_percent",
            description="Node-level memory utilization",
            unit="%",
        )

        return cpu_series + mem_series

    def collect_all_metrics(
        self,
        lookback_minutes: int = 30,
        namespace: Optional[str] = None,
    ) -> MetricsSnapshot:
        """
        Main entry point: collect all relevant metrics and return a
        complete MetricsSnapshot ready for the AI analysis engine.
        
        Args:
            lookback_minutes: How many minutes back to query
            namespace: Optional EKS namespace filter
        
        Returns:
            MetricsSnapshot with all metrics and computed health flags
        """
        # Define the time window for all queries
        end = datetime.utcnow()
        start = end - timedelta(minutes=lookback_minutes)

        logger.info(
            f"Collecting all Prometheus metrics "
            f"[{start.isoformat()} -> {end.isoformat()}] "
            f"namespace={namespace or 'all'}"
        )

        # ---- Collect each metric category ----
        cpu_metrics = self.collect_cpu_metrics(start, end, namespace)
        memory_metrics = self.collect_memory_metrics(start, end, namespace)
        pod_metrics = self.collect_pod_restart_metrics(start, end, namespace)
        http_metrics = self.collect_http_error_metrics(start, end, namespace)
        node_metrics = self.collect_node_metrics(start, end)

        # ---- Compute health flags for quick AI triage ----

        # Flag if any pod has avg CPU > 80%
        has_high_cpu = any(
            (s.avg_value or 0) > 80.0 for s in cpu_metrics + node_metrics
        )

        # Flag if any container has memory usage > 85% of its limit
        has_high_memory = any(
            (s.avg_value or 0) > 85.0 for s in memory_metrics
        )

        # Flag if any pod had restarts in the lookback window
        has_pod_restarts = len(pod_metrics) > 0

        # Flag if any service has error rate > 5%
        has_high_error_rate = any(
            (s.avg_value or 0) > 5.0 for s in http_metrics
        )

        # ---- Build human-readable summary for the LLM prompt ----
        summary_parts = []
        if has_high_cpu:
            # Find worst offender
            max_cpu_series = max(cpu_metrics + node_metrics, key=lambda s: s.max_value or 0)
            summary_parts.append(
                f"HIGH CPU detected: {max_cpu_series.labels.get('pod', max_cpu_series.labels.get('instance', 'unknown'))} "
                f"at {max_cpu_series.max_value:.1f}% max"
            )
        if has_high_memory:
            max_mem_series = max(memory_metrics, key=lambda s: s.max_value or 0)
            summary_parts.append(
                f"HIGH MEMORY detected: {max_mem_series.labels.get('pod', 'unknown')} "
                f"at {max_mem_series.max_value:.1f}% of limit"
            )
        if has_pod_restarts:
            restarted_pods = [s.labels.get("pod", "unknown") for s in pod_metrics]
            summary_parts.append(
                f"POD RESTARTS detected: {', '.join(restarted_pods[:5])}"
            )
        if has_high_error_rate:
            summary_parts.append(
                f"HIGH HTTP ERROR RATE detected in {len(http_metrics)} service(s)"
            )
        if not summary_parts:
            summary_parts.append("No critical metric anomalies detected in the lookback window.")

        snapshot = MetricsSnapshot(
            lookback_minutes=lookback_minutes,
            cpu_metrics=cpu_metrics,
            memory_metrics=memory_metrics,
            pod_status_metrics=pod_metrics,
            http_error_metrics=http_metrics,
            custom_metrics=node_metrics,
            has_high_cpu=has_high_cpu,
            has_high_memory=has_high_memory,
            has_pod_restarts=has_pod_restarts,
            has_high_error_rate=has_high_error_rate,
            summary="\n".join(summary_parts),
        )

        logger.info(f"Metrics snapshot built: {snapshot.summary}")
        return snapshot


# ============================================================
# Standalone testing (run this file directly to test)
# ============================================================
if __name__ == "__main__":
    import json

    # Test with a local Prometheus (e.g., port-forwarded via kubectl)
    collector = PrometheusCollector(prometheus_url="http://localhost:9090")
    snapshot = collector.collect_all_metrics(lookback_minutes=30)

    print("\n========== METRICS SUMMARY ==========")
    print(snapshot.summary)
    print(f"\nCPU Series: {len(snapshot.cpu_metrics)}")
    print(f"Memory Series: {len(snapshot.memory_metrics)}")
    print(f"Pod Restart Series: {len(snapshot.pod_status_metrics)}")
    print(f"HTTP Error Series: {len(snapshot.http_error_metrics)}")
