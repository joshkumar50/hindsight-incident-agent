"""
=============================================================
lambda/collectors/elasticsearch_collector.py
=============================================================
Purpose: Collect application and EKS logs from Elasticsearch
         (the 'E' in EFK stack) for AI root cause analysis.

EFK Stack Flow:
  Applications / K8s → Fluentd (collector) → Elasticsearch (storage)
                                                      ↓
                                              This collector reads from here

Log patterns this collector targets:
  - ERROR / FATAL level application logs
  - CrashLoopBackOff Kubernetes events
  - OOMKilled container events
  - Connection timeout / refused errors
  - Stack traces and exception messages

Uses the Elasticsearch Python client (elasticsearch-py v8).
=============================================================
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch, ConnectionError as ESConnectionError
from elasticsearch.exceptions import NotFoundError, RequestError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import config
from shared.models import LogEntry, LogSnapshot

# ---- Logging Setup ----
logger = logging.getLogger(__name__)


# ============================================================
# Keyword patterns for quick log triage
# ============================================================

# These patterns are used to flag specific types of issues
# in the log summary for the LLM
OOM_PATTERNS = [
    "OOMKilled", "OutOfMemory", "out of memory", "Cannot allocate memory",
    "java.lang.OutOfMemoryError", "MemoryError"
]

CRASH_LOOP_PATTERNS = [
    "CrashLoopBackOff", "BackOff", "crash loop", "container crashed",
    "Readiness probe failed", "Liveness probe failed"
]

CONNECTION_ERROR_PATTERNS = [
    "Connection refused", "connection timeout", "Connection reset",
    "ECONNREFUSED", "ETIMEDOUT", "dial tcp", "no such host",
    "database connection", "redis connection", "kafka connection"
]


class ElasticsearchCollector:
    """
    Collects logs from Elasticsearch (EFK stack) for the AI RCA engine.
    
    Fluentd in EKS is configured to forward all pod logs to Elasticsearch
    with the index pattern: fluentd-YYYY.MM.DD
    Each document contains fields like:
      - @timestamp: ISO8601 timestamp
      - log: raw log message
      - kubernetes.pod_name
      - kubernetes.namespace_name
      - kubernetes.container_name
      - kubernetes.labels.app
    """

    def __init__(
        self,
        es_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the Elasticsearch collector.
        
        Args:
            es_url: Override Elasticsearch URL (falls back to config)
            username: Basic auth username
            password: Basic auth password
            timeout: Request timeout in seconds
        """
        url = es_url or config.elasticsearch.url
        user = username or config.elasticsearch.username
        pwd = password or config.elasticsearch.password

        # Build connection kwargs
        conn_kwargs: Dict[str, Any] = {
            "hosts": [url],
            "request_timeout": timeout,
            "retry_on_timeout": True,
            "max_retries": 3,
        }

        # Add authentication only if credentials are provided
        if user and pwd:
            conn_kwargs["basic_auth"] = (user, pwd)

        # Initialize the Elasticsearch client
        # ES8 client uses verified TLS by default; disable for internal clusters
        conn_kwargs["verify_certs"] = False
        conn_kwargs["ssl_show_warn"] = False

        self.client = Elasticsearch(**conn_kwargs)
        self.log_index = config.elasticsearch.log_index        # e.g., "fluentd-*"
        self.system_index = config.elasticsearch.system_index  # e.g., "kubernetes-*"
        self.max_results = config.elasticsearch.max_results

        logger.info(f"ElasticsearchCollector initialized: {url}")

    def _check_connection(self) -> bool:
        """
        Ping Elasticsearch to verify connectivity before queries.
        Returns True if reachable, False otherwise.
        """
        try:
            return self.client.ping()
        except ESConnectionError as e:
            logger.error(f"Cannot connect to Elasticsearch: {e}")
            return False

    def _build_time_range_filter(
        self, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        """
        Build an Elasticsearch range filter for the @timestamp field.
        
        Elasticsearch Query DSL uses ISO8601 format for time ranges.
        The 'gte' and 'lte' operators are used (>= and <=).
        """
        return {
            "range": {
                "@timestamp": {
                    "gte": start.isoformat() + "Z",   # UTC time, Z suffix
                    "lte": end.isoformat() + "Z",
                    "format": "strict_date_optional_time",
                }
            }
        }

    def _build_level_filter(self, levels: List[str]) -> Dict[str, Any]:
        """
        Build a terms filter for log severity levels.
        
        Fluentd typically extracts log level into a 'level' or 'severity'
        field. We check both field names for compatibility.
        
        Args:
            levels: e.g., ["ERROR", "FATAL", "error", "fatal"]
        """
        # Normalize to both uppercase and lowercase for broad compatibility
        normalized = list(set([lvl.upper() for lvl in levels] + [lvl.lower() for lvl in levels]))
        return {
            "bool": {
                "should": [
                    {"terms": {"level": normalized}},
                    {"terms": {"severity": normalized}},
                    {"terms": {"log.level": normalized}},  # ECS format
                ],
                "minimum_should_match": 1,
            }
        }

    def _parse_hit_to_log_entry(self, hit: Dict[str, Any]) -> Optional[LogEntry]:
        """
        Convert a raw Elasticsearch document (_source) into a LogEntry.
        
        Handles the Fluentd-to-ES document format which stores
        Kubernetes metadata under the 'kubernetes' field.
        
        Expected document structure:
        {
          "@timestamp": "2024-01-15T10:30:00.000Z",
          "log": "ERROR: Connection refused to database",
          "level": "error",
          "kubernetes": {
            "pod_name": "api-server-abc123",
            "namespace_name": "production",
            "container_name": "api-server",
            "labels": {"app": "api-server"}
          }
        }
        """
        try:
            source = hit.get("_source", {})

            # ---- Extract timestamp ----
            ts_str = source.get("@timestamp", "")
            try:
                # Handle both 'Z' suffix and '+00:00' timezone formats
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                ts = ts.replace(tzinfo=None)  # Strip timezone for consistency
            except (ValueError, AttributeError):
                ts = datetime.utcnow()

            # ---- Extract log message ----
            # Fluentd can put the message in 'log', 'message', or 'msg' fields
            message = (
                source.get("log")
                or source.get("message")
                or source.get("msg")
                or str(source)
            )

            # ---- Extract log level ----
            level = (
                source.get("level")
                or source.get("severity")
                or source.get("log", {}).get("level", "INFO")
                if isinstance(source.get("log"), dict)
                else "INFO"
            ).upper()

            # ---- Extract Kubernetes metadata ----
            k8s = source.get("kubernetes", {})
            pod_name = k8s.get("pod_name", source.get("pod", ""))
            namespace = k8s.get("namespace_name", source.get("namespace", ""))
            container = k8s.get("container_name", source.get("container", ""))
            # Try to get service name from k8s labels
            labels = k8s.get("labels", {})
            service = labels.get("app", labels.get("app.kubernetes.io/name", ""))

            return LogEntry(
                timestamp=ts,
                level=level,
                message=str(message)[:2000],  # Truncate very long messages
                pod_name=pod_name,
                namespace=namespace,
                container=container,
                service=service,
                raw_fields=source,
            )

        except Exception as e:
            logger.warning(f"Failed to parse log hit: {e}")
            return None

    def _contains_pattern(self, message: str, patterns: List[str]) -> bool:
        """Check if a log message contains any of the given patterns (case-insensitive)."""
        msg_lower = message.lower()
        return any(p.lower() in msg_lower for p in patterns)

    def query_error_logs(
        self,
        start: datetime,
        end: datetime,
        namespace: Optional[str] = None,
        service: Optional[str] = None,
        max_results: int = 200,
    ) -> List[LogEntry]:
        """
        Query Elasticsearch for ERROR and FATAL level logs.
        
        Args:
            start: Start of time window
            end: End of time window
            namespace: Filter to specific K8s namespace
            service: Filter to specific service (app label)
            max_results: Maximum number of log entries to return
        
        Returns:
            List of LogEntry objects sorted by timestamp (newest first)
        """
        if not self._check_connection():
            logger.error("Elasticsearch is not reachable, skipping log collection")
            return []

        # Build the Elasticsearch query using Query DSL
        must_clauses = [
            # Time range filter
            self._build_time_range_filter(start, end),
            # Only ERROR and FATAL logs
            self._build_level_filter(["ERROR", "FATAL", "CRITICAL"]),
        ]

        # ---- Optional namespace filter ----
        if namespace:
            must_clauses.append(
                {
                    "bool": {
                        "should": [
                            {"term": {"kubernetes.namespace_name": namespace}},
                            {"term": {"namespace": namespace}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )

        # ---- Optional service/app filter ----
        if service:
            must_clauses.append(
                {
                    "bool": {
                        "should": [
                            {"term": {"kubernetes.labels.app": service}},
                            {"term": {"service": service}},
                            {"match": {"kubernetes.pod_name": service}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )

        # Full query body
        query = {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{"@timestamp": {"order": "desc"}}],  # Newest first
            "size": max_results,
            # Request specific fields to minimize response payload
            "_source": [
                "@timestamp", "log", "message", "msg",
                "level", "severity",
                "kubernetes.pod_name", "kubernetes.namespace_name",
                "kubernetes.container_name", "kubernetes.labels",
            ],
        }

        try:
            response = self.client.search(
                index=self.log_index,
                body=query,
            )
            hits = response["hits"]["hits"]
            logger.info(
                f"Elasticsearch returned {len(hits)} error logs "
                f"(total: {response['hits']['total']['value']})"
            )

            # Parse each hit into a LogEntry
            entries = []
            for hit in hits:
                entry = self._parse_hit_to_log_entry(hit)
                if entry:
                    entries.append(entry)

            return entries

        except (RequestError, NotFoundError) as e:
            logger.error(f"Elasticsearch query failed: {e}")
            return []

    def query_warning_logs(
        self,
        start: datetime,
        end: datetime,
        namespace: Optional[str] = None,
        service: Optional[str] = None,
        max_results: int = 100,
    ) -> List[LogEntry]:
        """
        Query Elasticsearch for WARNING level logs.
        Warnings often precede errors and provide useful context for RCA.
        """
        if not self._check_connection():
            return []

        must_clauses = [
            self._build_time_range_filter(start, end),
            self._build_level_filter(["WARN", "WARNING"]),
        ]

        if namespace:
            must_clauses.append({"term": {"kubernetes.namespace_name": namespace}})
        if service:
            must_clauses.append({"term": {"kubernetes.labels.app": service}})

        query = {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{"@timestamp": {"order": "desc"}}],
            "size": max_results,
        }

        try:
            response = self.client.search(index=self.log_index, body=query)
            hits = response["hits"]["hits"]
            entries = [self._parse_hit_to_log_entry(h) for h in hits]
            return [e for e in entries if e is not None]
        except Exception as e:
            logger.error(f"Warning log query failed: {e}")
            return []

    def get_top_errors(
        self,
        start: datetime,
        end: datetime,
        namespace: Optional[str] = None,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Use Elasticsearch aggregations to find the most frequent error patterns.
        
        This helps the LLM quickly identify the most impactful issues
        instead of reading hundreds of individual log lines.
        
        Uses 'significant_text' aggregation which automatically deduplicates
        similar error messages (e.g., same exception from different pods).
        
        Returns a list like:
          [{"message": "Connection refused", "count": 142, "services": ["api"]}, ...]
        """
        if not self._check_connection():
            return []

        must_clauses = [
            self._build_time_range_filter(start, end),
            self._build_level_filter(["ERROR", "FATAL"]),
        ]

        if namespace:
            must_clauses.append({"term": {"kubernetes.namespace_name": namespace}})

        # Use 'terms' aggregation on the message field to get top N unique errors
        # Note: 'log' field must have 'keyword' sub-field in the mapping for aggregation
        query = {
            "query": {"bool": {"must": must_clauses}},
            "size": 0,  # No actual hits needed, only aggregation results
            "aggs": {
                "top_errors": {
                    "terms": {
                        "field": "log.keyword",  # .keyword = not analyzed, exact match
                        "size": top_n,
                    },
                    "aggs": {
                        # For each top error, find which services produced it
                        "by_service": {
                            "terms": {
                                "field": "kubernetes.labels.app.keyword",
                                "size": 5,
                            }
                        }
                    },
                }
            },
        }

        try:
            response = self.client.search(index=self.log_index, body=query)
            buckets = (
                response.get("aggregations", {})
                .get("top_errors", {})
                .get("buckets", [])
            )

            top_errors = []
            for bucket in buckets:
                # Truncate very long error messages for readability
                msg = str(bucket.get("key", ""))[:500]
                count = bucket.get("doc_count", 0)
                services = [
                    b["key"]
                    for b in bucket.get("by_service", {}).get("buckets", [])
                ]
                top_errors.append(
                    {"message": msg, "count": count, "services": services}
                )

            logger.info(f"Found {len(top_errors)} top error patterns")
            return top_errors

        except Exception as e:
            logger.error(f"Top errors aggregation failed: {e}")
            return []

    def collect_all_logs(
        self,
        lookback_minutes: int = 30,
        namespace: Optional[str] = None,
        service: Optional[str] = None,
    ) -> LogSnapshot:
        """
        Main entry point: collect all relevant logs and return a
        complete LogSnapshot for the AI analysis engine.
        
        Args:
            lookback_minutes: How far back to look for logs
            namespace: Optional K8s namespace filter
            service: Optional service/app filter
        
        Returns:
            LogSnapshot with error logs, warnings, top errors, and health flags
        """
        # Define the time window
        end = datetime.utcnow()
        start = end - timedelta(minutes=lookback_minutes)

        logger.info(
            f"Collecting logs [{start.isoformat()} -> {end.isoformat()}] "
            f"ns={namespace or 'all'} service={service or 'all'}"
        )

        # ---- Collect error and warning logs ----
        error_logs = self.query_error_logs(start, end, namespace, service, max_results=300)
        warning_logs = self.query_warning_logs(start, end, namespace, service, max_results=100)

        # ---- Get top error patterns via aggregation ----
        top_errors = self.get_top_errors(start, end, namespace, top_n=10)

        # ---- Extract affected services and pods from error logs ----
        affected_services = list(
            set(e.service for e in error_logs if e.service)
        )
        affected_pods = list(
            set(e.pod_name for e in error_logs if e.pod_name)
        )

        # ---- Detect specific issue patterns ----
        all_messages = " ".join(e.message for e in error_logs + warning_logs)

        has_oom_errors = self._contains_pattern(all_messages, OOM_PATTERNS)
        has_crash_loops = self._contains_pattern(all_messages, CRASH_LOOP_PATTERNS)
        has_connection_errors = self._contains_pattern(
            all_messages, CONNECTION_ERROR_PATTERNS
        )

        # ---- Build human-readable summary for the LLM ----
        summary_parts = []
        summary_parts.append(
            f"Found {len(error_logs)} ERROR logs and {len(warning_logs)} "
            f"WARNING logs in the last {lookback_minutes} minutes."
        )
        if affected_services:
            summary_parts.append(
                f"Affected services: {', '.join(affected_services[:10])}"
            )
        if has_oom_errors:
            summary_parts.append("⚠️ OOM (Out of Memory) errors detected in logs.")
        if has_crash_loops:
            summary_parts.append("⚠️ Pod CrashLoopBackOff events detected in logs.")
        if has_connection_errors:
            summary_parts.append(
                "⚠️ Connection errors detected (database, redis, or network issues)."
            )
        if top_errors:
            summary_parts.append(
                f"\nTop error pattern: '{top_errors[0]['message'][:200]}' "
                f"({top_errors[0]['count']} occurrences)"
            )

        snapshot = LogSnapshot(
            lookback_minutes=lookback_minutes,
            total_logs_found=len(error_logs) + len(warning_logs),
            error_logs=error_logs[:100],    # Cap at 100 for LLM context
            warning_logs=warning_logs[:50],
            top_errors=top_errors,
            affected_services=affected_services,
            affected_pods=affected_pods[:20],
            has_oom_errors=has_oom_errors,
            has_crash_loops=has_crash_loops,
            has_connection_errors=has_connection_errors,
            summary="\n".join(summary_parts),
        )

        logger.info(f"Log snapshot built: {snapshot.summary[:200]}")
        return snapshot


# ============================================================
# Standalone testing
# ============================================================
if __name__ == "__main__":
    collector = ElasticsearchCollector(es_url="http://localhost:9200")
    snapshot = collector.collect_all_logs(lookback_minutes=30)
    print("\n========== LOGS SUMMARY ==========")
    print(snapshot.summary)
    print(f"\nTotal errors: {len(snapshot.error_logs)}")
    print(f"Top errors: {len(snapshot.top_errors)}")
