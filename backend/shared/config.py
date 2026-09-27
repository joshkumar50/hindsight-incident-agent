"""
=============================================================
shared/config.py - Centralized Configuration Manager
=============================================================
Purpose: Load and validate all environment variables used
         across Lambda, collectors, and Streamlit UI.
         All modules import from this single source of truth.
=============================================================
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

# Load .env file if present (for local development)
# In Lambda, environment variables are set via the console or Terraform
load_dotenv()

# Load YAML configuration if present
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_CONFIG_PATH = os.path.join(ROOT_DIR, "config", "config.yaml")
yaml_data = {}
if os.path.exists(YAML_CONFIG_PATH):
    try:
        import yaml
        with open(YAML_CONFIG_PATH, "r") as f:
            yaml_data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to load config.yaml: {e}")


@dataclass
class AWSConfig:
    """AWS-specific configuration including Bedrock LLM settings."""
    region: str = field(default_factory=lambda: yaml_data.get("bedrock", {}).get("aws_region") or os.getenv("AWS_REGION", "us-east-1"))
    account_id: str = field(default_factory=lambda: os.getenv("AWS_ACCOUNT_ID", ""))
    bedrock_model_id: str = field(
        default_factory=lambda: yaml_data.get("bedrock", {}).get("model_id") or os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Default to Claude 3.5 Sonnet
        )
    )
    bedrock_agent_id: str = field(
        default_factory=lambda: yaml_data.get("bedrock", {}).get("agent_id") or os.getenv("BEDROCK_AGENT_ID", "")
    )
    bedrock_agent_alias_id: str = field(
        default_factory=lambda: yaml_data.get("bedrock", {}).get("agent_alias_id") or os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
    )
    sns_alert_topic_arn: str = field(
        default_factory=lambda: os.getenv("SNS_ALERT_TOPIC_ARN", "")
    )
    aws_access_key_id: str = field(
        default_factory=lambda: yaml_data.get("bedrock", {}).get("aws_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID", "")
    )
    aws_secret_access_key: str = field(
        default_factory=lambda: yaml_data.get("bedrock", {}).get("aws_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY", "")
    )
    aws_session_token: str = field(
        default_factory=lambda: yaml_data.get("bedrock", {}).get("aws_session_token") or os.getenv("AWS_SESSION_TOKEN", "")
    )


@dataclass
class PrometheusConfig:
    """Prometheus metrics collection configuration."""
    # Use external URL for Streamlit (outside cluster), internal for Lambda (inside cluster)
    url: str = field(
        default_factory=lambda: os.getenv(
            "PROMETHEUS_EXTERNAL_URL",
            os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        )
    )
    # Timeout in seconds for Prometheus API calls
    timeout: int = 30
    # Maximum number of data points to retrieve
    max_samples: int = 11000


@dataclass
class ElasticsearchConfig:
    """Elasticsearch (EFK stack) configuration for log retrieval."""
    url: str = field(
        default_factory=lambda: os.getenv(
            "ELASTICSEARCH_EXTERNAL_URL",
            os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        )
    )
    username: str = field(
        default_factory=lambda: os.getenv("ELASTICSEARCH_USERNAME", "elastic")
    )
    password: str = field(
        default_factory=lambda: os.getenv("ELASTICSEARCH_PASSWORD", "")
    )
    # Index patterns for different log types
    log_index: str = field(
        default_factory=lambda: os.getenv("ELASTICSEARCH_LOG_INDEX", "fluentd-*")
    )
    system_index: str = field(
        default_factory=lambda: os.getenv("ELASTICSEARCH_SYSTEM_INDEX", "kubernetes-*")
    )
    # Maximum log entries to retrieve per query
    max_results: int = 500
    timeout: int = 30


@dataclass
class JaegerConfig:
    """Jaeger distributed tracing configuration."""
    url: str = field(
        default_factory=lambda: os.getenv(
            "JAEGER_EXTERNAL_URL",
            os.getenv("JAEGER_URL", "http://localhost:16686")
        )
    )
    # Jaeger Query API endpoint (v3 REST API)
    api_base: str = "/api"
    # Maximum number of traces to retrieve
    max_traces: int = 100
    timeout: int = 30


@dataclass
class LambdaConfig:
    """AWS Lambda execution configuration."""
    function_name: str = field(
        default_factory=lambda: os.getenv("LAMBDA_FUNCTION_NAME", "ai-rca-analyzer")
    )
    role_arn: str = field(
        default_factory=lambda: os.getenv("LAMBDA_ROLE_ARN", "")
    )
    # How many minutes back to look for issues
    lookback_minutes: int = field(
        default_factory=lambda: int(os.getenv("LAMBDA_LOOKBACK_MINUTES", "30"))
    )
    max_log_entries: int = field(
        default_factory=lambda: int(os.getenv("LAMBDA_MAX_LOG_ENTRIES", "500"))
    )


@dataclass
class EKSConfig:
    """EKS cluster configuration for scoping queries."""
    cluster_name: str = field(
        default_factory=lambda: os.getenv("EKS_CLUSTER_NAME", "")
    )
    region: str = field(
        default_factory=lambda: os.getenv("EKS_REGION", "us-east-1")
    )
    # Namespaces to monitor (e.g., ["default", "production"])
    monitored_namespaces: List[str] = field(
        default_factory=lambda: os.getenv(
            "MONITORED_NAMESPACES", "default,production"
        ).split(",")
    )
    app_label_selector: str = field(
        default_factory=lambda: os.getenv("APP_LABEL_SELECTOR", "app")
    )


@dataclass
class IntegrationsConfig:
    """External integrations configuration for notifications and remediation."""
    slack_webhook_url: str = field(
        default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", "")
    )
    jira_webhook_url: str = field(
        default_factory=lambda: os.getenv("JIRA_WEBHOOK_URL", "")
    )
    remediation_webhook_url: str = field(
        default_factory=lambda: os.getenv("REMEDIATION_WEBHOOK_URL", "")
    )


@dataclass
class OpenAIConfig:
    """OpenAI API connection configuration."""
    api_key: str = field(default_factory=lambda: yaml_data.get("openai", {}).get("api_key") or os.getenv("OPENAI_API_KEY", ""))
    model_id: str = field(default_factory=lambda: yaml_data.get("openai", {}).get("model_id") or os.getenv("OPENAI_MODEL_ID", "gpt-4o"))
    api_base: str = field(default_factory=lambda: yaml_data.get("openai", {}).get("api_base") or os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))


@dataclass
class AnthropicConfig:
    """Anthropic direct API connection configuration."""
    api_key: str = field(default_factory=lambda: yaml_data.get("anthropic", {}).get("api_key") or os.getenv("ANTHROPIC_API_KEY", ""))
    model_id: str = field(default_factory=lambda: yaml_data.get("anthropic", {}).get("model_id") or os.getenv("ANTHROPIC_MODEL_ID", "claude-3-5-sonnet-20241022"))


@dataclass
class AgentConfig:
    """Agent workflow and behavior configuration."""
    max_iterations: int = field(default_factory=lambda: int(yaml_data.get("agent", {}).get("max_iterations") or os.getenv("AGENT_MAX_ITERATIONS", "8")))
    temperature: float = field(default_factory=lambda: float(yaml_data.get("agent", {}).get("temperature") or os.getenv("AGENT_TEMPERATURE", "0.1")))
    max_tokens: int = field(default_factory=lambda: int(yaml_data.get("agent", {}).get("max_tokens") or os.getenv("AGENT_MAX_TOKENS", "4096")))
    verbose: bool = field(default_factory=lambda: yaml_data.get("agent", {}).get("verbose") if yaml_data.get("agent", {}).get("verbose") is not None else os.getenv("AGENT_VERBOSE", "True").lower() == "true")
    fallback_to_direct_invocation: bool = field(default_factory=lambda: yaml_data.get("agent", {}).get("fallback_to_direct_invocation") if yaml_data.get("agent", {}).get("fallback_to_direct_invocation") is not None else os.getenv("AGENT_FALLBACK", "True").lower() == "true")


@dataclass
class HindsightConfig:
    """Hindsight memory connection parameters."""
    api_key: str = field(default_factory=lambda: yaml_data.get("hindsight", {}).get("api_key") or os.getenv("HINDSIGHT_API_KEY", ""))


@dataclass
class AppConfig:
    """Top-level application configuration aggregating all sub-configs."""
    default_llm_provider: str = field(default_factory=lambda: yaml_data.get("default_llm_provider") or os.getenv("DEFAULT_LLM_PROVIDER", "bedrock"))
    aws: AWSConfig = field(default_factory=AWSConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    hindsight: HindsightConfig = field(default_factory=HindsightConfig)
    prometheus: PrometheusConfig = field(default_factory=PrometheusConfig)
    elasticsearch: ElasticsearchConfig = field(default_factory=ElasticsearchConfig)
    jaeger: JaegerConfig = field(default_factory=JaegerConfig)
    lambda_cfg: LambdaConfig = field(default_factory=LambdaConfig)
    eks: EKSConfig = field(default_factory=EKSConfig)
    integrations: IntegrationsConfig = field(default_factory=IntegrationsConfig)


# ============================================================
# Singleton config instance - import this across the project
# ============================================================
# Usage:  from shared.config import config
#         url = config.prometheus.url
config = AppConfig()


def reload_config():
    """Re-load configuration from environment variables."""
    global config, yaml_data
    # Re-trigger .env loading in case it changed on disk
    load_dotenv(override=True)
    yaml_data = {}
    if os.path.exists(YAML_CONFIG_PATH):
        try:
            import yaml
            with open(YAML_CONFIG_PATH, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load config.yaml: {e}")
    config = AppConfig()
    return config
