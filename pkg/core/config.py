from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """
    Centralized configuration management for all Hindsight Incident Agent — Autonomous SRE Platform services.
    Validates environment variables on startup. Fails fast if secrets are missing.
    """

    service_name: str = Field(..., description="Name of the microservice")
    environment: str = Field(default="production", description="Deployment environment")

    # Redis configuration
    redis_host: str = Field(default="redis-master.incident-agent-system.svc.cluster.local")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: Optional[str] = Field(default=None)

    # PostgreSQL configuration
    postgres_host: str = Field(default="postgres-db.incident-agent-system.svc.cluster.local")
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_user: str = Field(default="hindsight_agent")
    # No default for passwords in production! Fails if missing in ENV.
    postgres_password: str = Field(...)
    postgres_db: str = Field(default="incident_agent_db")

    # OpenTelemetry configuration
    otel_exporter_otlp_endpoint: str = Field(
        default="http://otel-collector.incident-agent-observability.svc.cluster.local:4317"
    )

    # Security configuration
    # No default! Forces the cluster to mount the Secret.
    jwt_secret: str = Field(...)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def get_config() -> AppConfig:
    """Returns a globally validated configuration object."""
    return AppConfig()
