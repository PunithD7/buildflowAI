"""
Logging Configuration - Structured JSON logging
"""
import logging
import sys
from typing import Any, Dict

import structlog
from app.core.config import settings


def setup_logging():
    """Configure structured logging for the application."""
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure standard library logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
    )
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger = logging.getLogger("buildflow")
    logger.info(f"🔧 Logging configured: level={settings.LOG_LEVEL}, format={settings.LOG_FORMAT}")


class AgentLogger:
    """Specialized logger for agent events."""
    
    def __init__(self, agent_name: str, workflow_id: str = None, task_id: str = None):
        self.agent_name = agent_name
        self.workflow_id = workflow_id
        self.task_id = task_id
        self._logger = logging.getLogger(f"agent.{agent_name.lower().replace(' ', '_')}")
    
    def _build_context(self, **kwargs) -> Dict[str, Any]:
        ctx = {
            "agent": self.agent_name,
            "workflow_id": self.workflow_id,
            "task_id": self.task_id,
        }
        ctx.update(kwargs)
        return ctx
    
    def info(self, message: str, **kwargs):
        self._logger.info(f"[{self.agent_name}] {message}", extra=self._build_context(**kwargs))
    
    def warning(self, message: str, **kwargs):
        self._logger.warning(f"[{self.agent_name}] ⚠️  {message}", extra=self._build_context(**kwargs))
    
    def error(self, message: str, **kwargs):
        self._logger.error(f"[{self.agent_name}] ❌ {message}", extra=self._build_context(**kwargs))
    
    def success(self, message: str, **kwargs):
        self._logger.info(f"[{self.agent_name}] ✅ {message}", extra=self._build_context(**kwargs))
    
    def retry(self, attempt: int, max_attempts: int, reason: str, **kwargs):
        self._logger.warning(
            f"[{self.agent_name}] 🔄 Retry {attempt}/{max_attempts}: {reason}",
            extra=self._build_context(attempt=attempt, max_attempts=max_attempts, **kwargs)
        )
    
    def failover(self, backup_agent: str, **kwargs):
        self._logger.warning(
            f"[{self.agent_name}] 🆘 Failover → {backup_agent}",
            extra=self._build_context(backup_agent=backup_agent, **kwargs)
        )
