"""
Base Agent - Foundation for all BuildFlow agents

FIXES APPLIED:
  - Fixed result_data.pop("_tokens_used") mutating the output dict before storage.
    Now uses .get() and creates a clean copy to extract the metadata key.
  - Agent 'completed' WebSocket event now includes output_preview (first 500 chars)
    so the frontend can show real reasoning snippets immediately.
  - Added detailed per-agent logging: attempt number, elapsed time, LLM provider used.
  - ValueError from complete_json() (JSON parse failure) now propagates correctly
    through the retry loop instead of being silently swallowed.
"""
import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import AgentLogger
from app.core.sandbox import sandbox_manager

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent execution states."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    FAILED_OVER = "failed_over"
    CANCELLED = "cancelled"


class AgentResult:
    """Standardized agent execution result."""

    def __init__(
        self,
        agent_name: str,
        status: AgentStatus,
        data: Optional[Dict] = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        tokens_used: int = 0,
        metadata: Optional[Dict] = None,
    ):
        self.agent_name = agent_name
        self.status = status
        self.data = data or {}
        self.error = error
        self.execution_time = execution_time
        self.tokens_used = tokens_used
        self.metadata = metadata or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict:
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @property
    def success(self) -> bool:
        return self.status == AgentStatus.COMPLETED


class AgentContext:
    """Execution context passed between agents."""

    def __init__(self, workflow_id: str, user_id: str, project_id: str):
        self.workflow_id = workflow_id
        self.user_id = user_id
        self.project_id = project_id
        self.user_input: str = ""
        self.results: Dict[str, AgentResult] = {}
        self.shared_memory: Dict[str, Any] = {}
        self.execution_start = time.time()
        self.logs: List[Dict] = []

    def add_result(self, agent_name: str, result: AgentResult):
        """Store agent result in context."""
        self.results[agent_name] = result

    def get_result(self, agent_name: str) -> Optional[AgentResult]:
        """Retrieve a previous agent's result."""
        return self.results.get(agent_name)

    def log(self, level: str, message: str, agent: str = None):
        """Add to execution log."""
        self.logs.append({
            "level": level,
            "message": message,
            "agent": agent,
            "timestamp": time.time(),
        })

    def get_previous_outputs(self) -> Dict[str, Any]:
        """Aggregate all successful agent outputs for prompt context."""
        outputs = {}
        for name, result in self.results.items():
            if result.success:
                outputs[name] = result.data
        return outputs

    def to_dict(self) -> Dict:
        return {
            "workflow_id": self.workflow_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "user_input": self.user_input,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "shared_memory": self.shared_memory,
            "execution_start": self.execution_start,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all BuildFlow agents.
    Implements retry logic, failover, timeout, and observability.
    """

    name: str = "Base Agent"
    description: str = "Abstract agent"
    max_retries: int = 3
    timeout_seconds: int = 120
    can_fail_over: bool = True

    def __init__(self):
        self.agent_logger = AgentLogger(self.name)
        self._execution_count = 0
        self._failure_count = 0

    @abstractmethod
    async def _execute(self, context: AgentContext) -> Dict[str, Any]:
        """Core agent execution logic. Must be implemented by subclasses."""
        pass

    async def run_sandboxed(self, task_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task within a secure sandbox."""
        sandbox = await sandbox_manager.create_sandbox()
        try:
            result = await sandbox.execute_task(self.name, task_code, context)
            return result
        finally:
            await sandbox.terminate()

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute agent with retry, timeout, and failover protection.
        This is the primary entry point — never override this.
        """
        start_time = time.time()
        self._execution_count += 1

        self.agent_logger.info(
            f"Starting execution | workflow={context.workflow_id[:8]} "
            f"attempt=1/{self.max_retries} timeout={self.timeout_seconds}s"
        )

        # Notify via WebSocket: agent starting
        await self._emit_event(context, "started", {"description": self.description})

        # Log to workflow terminal
        await self._emit_log(
            context,
            "info",
            f"[{self.name}] ⚡ Starting — {self.description}",
        )

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            attempt_start = time.time()
            try:
                if attempt > 1:
                    wait_time = min(2 ** attempt, 30)
                    self.agent_logger.retry(attempt, self.max_retries, str(last_error))
                    await self._emit_event(context, "retrying", {
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "reason": str(last_error),
                        "wait_seconds": wait_time,
                    })
                    await self._emit_log(
                        context, "warning",
                        f"[{self.name}] 🔄 Retry {attempt}/{self.max_retries} "
                        f"(waiting {wait_time}s): {str(last_error)[:120]}"
                    )
                    await asyncio.sleep(wait_time)

                logger.info(
                    f"[{self.name}] Calling _execute() | "
                    f"attempt={attempt} workflow={context.workflow_id[:8]}"
                )

                # Execute with timeout
                result_data = await asyncio.wait_for(
                    self._execute(context),
                    timeout=self.timeout_seconds,
                )

                # FIX: Extract _tokens_used without mutating result_data
                # Use .get() and then create cleaned dict only if the key exists
                tokens_used = 0
                if isinstance(result_data, dict) and "_tokens_used" in result_data:
                    tokens_used = result_data.get("_tokens_used", 0)
                    result_data = {k: v for k, v in result_data.items() if k != "_tokens_used"}

                execution_time = time.time() - start_time
                attempt_time = time.time() - attempt_start

                # Build output preview for the WebSocket event
                output_preview = ""
                if isinstance(result_data, dict):
                    import json as _json
                    try:
                        output_preview = _json.dumps(result_data, indent=None)[:500]
                    except Exception:
                        output_preview = str(result_data)[:500]

                result = AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.COMPLETED,
                    data=result_data,
                    execution_time=execution_time,
                    tokens_used=tokens_used,
                    metadata={
                        "attempt": attempt,
                        "attempt_time": round(attempt_time, 2),
                    },
                )

                self.agent_logger.success(
                    f"Completed in {execution_time:.2f}s | "
                    f"attempt={attempt} tokens={tokens_used} "
                    f"output_keys={list(result_data.keys()) if isinstance(result_data, dict) else 'N/A'}"
                )

                await self._emit_event(context, "completed", {
                    "execution_time": round(execution_time, 2),
                    "attempt": attempt,
                    "tokens_used": tokens_used,
                    "output_preview": output_preview,
                    "output_keys": list(result_data.keys()) if isinstance(result_data, dict) else [],
                    "data": result_data,  # FULL DATA for live UI updates
                })

                await self._emit_log(
                    context, "success",
                    f"[{self.name}] ✅ Completed in {execution_time:.2f}s "
                    f"(attempt {attempt}/{self.max_retries}, {tokens_used} tokens)"
                )

                context.add_result(self.name, result)
                return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.timeout_seconds}s"
                self._failure_count += 1
                elapsed = time.time() - attempt_start
                self.agent_logger.error(
                    f"Attempt {attempt} timed out after {elapsed:.1f}s"
                )
                await self._emit_log(
                    context, "error",
                    f"[{self.name}] ⏱️  Attempt {attempt}/{self.max_retries} timed out "
                    f"after {elapsed:.1f}s"
                )

            except Exception as e:
                last_error = str(e)
                self._failure_count += 1
                elapsed = time.time() - attempt_start
                self.agent_logger.error(
                    f"Attempt {attempt} failed after {elapsed:.1f}s: {e}"
                )
                logger.error(
                    f"[{self.name}] Attempt {attempt}/{self.max_retries} exception "
                    f"after {elapsed:.1f}s: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                await self._emit_log(
                    context, "error",
                    f"[{self.name}] ❌ Attempt {attempt}/{self.max_retries} failed: {str(e)[:150]}"
                )

        # All retries exhausted
        execution_time = time.time() - start_time
        result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.FAILED,
            error=str(last_error),
            execution_time=execution_time,
        )

        self.agent_logger.error(
            f"All {self.max_retries} attempts failed in {execution_time:.2f}s. "
            f"Last error: {last_error}"
        )

        await self._emit_event(context, "failed", {
            "error": str(last_error),
            "attempts": self.max_retries,
            "execution_time": round(execution_time, 2),
        })

        await self._emit_log(
            context, "error",
            f"[{self.name}] 💥 All {self.max_retries} attempts failed. "
            f"Last error: {str(last_error)[:150]}"
        )

        context.add_result(self.name, result)
        return result

    async def _emit_event(self, context: AgentContext, event_type: str, payload: Dict = None):
        """Emit agent event via WebSocket."""
        try:
            from app.core.websocket_manager import ws_manager
            await ws_manager.send_agent_event(
                workflow_id=context.workflow_id,
                agent_name=self.name,
                event_type=event_type,
                payload=payload or {},
            )
        except Exception as e:
            logger.debug(f"[{self.name}] _emit_event silenced: {e}")

    async def _emit_log(self, context: AgentContext, level: str, message: str):
        """Emit log entry to workflow terminal."""
        try:
            from app.core.websocket_manager import ws_manager
            await ws_manager.send_log_entry(
                workflow_id=context.workflow_id,
                level=level,
                message=message,
                source=self.name,
            )
        except Exception as e:
            logger.debug(f"[{self.name}] _emit_log silenced: {e}")

    @property
    def stats(self) -> Dict:
        return {
            "name": self.name,
            "executions": self._execution_count,
            "failures": self._failure_count,
            "success_rate": (
                (self._execution_count - self._failure_count) / self._execution_count
                if self._execution_count > 0 else 0
            ),
        }
