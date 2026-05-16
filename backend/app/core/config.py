"""
Application Configuration
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "BuildFlow Secure AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    SECRET_KEY: str = Field(default="change-me-in-production-super-secret-key", env="SECRET_KEY")

    # ── Server ────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./buildflow.db", env="DATABASE_URL")
    SUPABASE_URL: Optional[str] = Field(default=None, env="SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = Field(default=None, env="SUPABASE_KEY")
    SUPABASE_SERVICE_KEY: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_KEY")

    # ── Redis ─────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")

    # ── AI Models ─────────────────────────────────────────
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash", env="GEMINI_MODEL")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20241022", env="ANTHROPIC_MODEL")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    PRIMARY_MODEL_PROVIDER: str = Field(default="gemini", env="PRIMARY_MODEL_PROVIDER")

    # ── JWT Auth ──────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(default="jwt-secret-change-in-prod", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # ── Rate Limiting ─────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    RATE_LIMIT_BURST: int = Field(default=10, env="RATE_LIMIT_BURST")
    AGENT_RATE_LIMIT_PER_MINUTE: int = Field(default=20, env="AGENT_RATE_LIMIT_PER_MINUTE")
    TOKEN_BUDGET_PER_REQUEST: int = Field(default=100000, env="TOKEN_BUDGET_PER_REQUEST")
    TOKEN_BUDGET_PER_HOUR: int = Field(default=500000, env="TOKEN_BUDGET_PER_HOUR")

    # ── DDoS Protection ───────────────────────────────────
    DDOS_THRESHOLD_PER_SECOND: int = Field(default=100, env="DDOS_THRESHOLD_PER_SECOND")
    DDOS_BAN_DURATION_SECONDS: int = Field(default=3600, env="DDOS_BAN_DURATION_SECONDS")
    DDOS_WHITELIST: List[str] = Field(default=["127.0.0.1", "::1"], env="DDOS_WHITELIST")

    # ── Security ──────────────────────────────────────────
    ENCRYPTION_KEY: str = Field(default="encryption-key-change-in-prod-32b", env="ENCRYPTION_KEY")
    TEE_EXECUTION_TIMEOUT: int = Field(default=300, env="TEE_EXECUTION_TIMEOUT")
    MAX_AGENT_RETRIES: int = Field(default=3, env="MAX_AGENT_RETRIES")
    AGENT_TIMEOUT_SECONDS: int = Field(default=120, env="AGENT_TIMEOUT_SECONDS")

    # ── File Upload ───────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, env="MAX_UPLOAD_SIZE_MB")
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["pdf", "docx", "txt", "md", "py", "js", "ts", "json", "yaml"],
        env="ALLOWED_FILE_TYPES"
    )

    # ── Code Generation ───────────────────────────────────
    GENERATED_PROJECTS_DIR: str = Field(default="./generated_projects", env="GENERATED_PROJECTS_DIR")

    # ── Observability ─────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    ENABLE_TRACING: bool = Field(default=True, env="ENABLE_TRACING")

    # ── WebSocket ─────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = Field(default=30, env="WS_HEARTBEAT_INTERVAL")
    WS_MAX_CONNECTIONS: int = Field(default=1000, env="WS_MAX_CONNECTIONS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# Singleton settings instance
settings = Settings()