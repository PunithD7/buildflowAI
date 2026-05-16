"""
Supabase Persistence Service

Uses httpx to call Supabase REST API directly (no SDK dependency beyond what's
already installed). All writes are fire-and-forget via asyncio.create_task() so
they never block agent execution or WebSocket delivery.

Tables required (run migrations/001_create_tables.sql in Supabase SQL editor):
  - workflows
  - agent_outputs
  - generated_files
  - project_artifacts
  - execution_history
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Async Supabase REST client for workflow + artifact persistence."""

    def __init__(self):
        # Strip trailing slash for clean URL construction
        raw_url = (settings.SUPABASE_URL or "").rstrip("/")
        # Supabase URL may already include /rest/v1; normalize it
        if raw_url.endswith("/rest/v1"):
            self._base = raw_url
        else:
            self._base = raw_url + "/rest/v1"

        self._key = settings.SUPABASE_SERVICE_KEY or ""
        self._enabled = bool(self._base and self._key and raw_url.startswith("http"))

        if self._enabled:
            logger.info(f"[Supabase] ✅ Persistence enabled | base={self._base[:50]}...")
        else:
            logger.warning("[Supabase] ⚠️  No Supabase credentials — persistence disabled")

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge-duplicates",
        }

    async def _upsert(self, table: str, data: Dict) -> bool:
        """Upsert a single row. Returns True on success."""
        if not self._enabled:
            return False
        url = f"{self._base}/{table}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self._headers(), json=data)
                if resp.status_code in (200, 201):
                    return True
                logger.warning(
                    f"[Supabase] Upsert {table} failed | "
                    f"status={resp.status_code} body={resp.text[:200]}"
                )
                return False
        except Exception as e:
            logger.warning(f"[Supabase] Upsert {table} error: {e}")
            return False

    async def _insert_many(self, table: str, rows: List[Dict]) -> int:
        """Insert multiple rows. Returns count inserted."""
        if not self._enabled or not rows:
            return 0
        url = f"{self._base}/{table}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=self._headers(), json=rows)
                if resp.status_code in (200, 201):
                    return len(rows)
                logger.warning(
                    f"[Supabase] Insert {table} failed | "
                    f"status={resp.status_code} body={resp.text[:200]}"
                )
                return 0
        except Exception as e:
            logger.warning(f"[Supabase] Insert {table} error: {e}")
            return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Public API — all methods are safe to fire-and-forget
    # ─────────────────────────────────────────────────────────────────────────

    async def persist_workflow(
        self,
        workflow_id: str,
        user_id: str,
        project_id: str,
        user_input: str,
        status: str,
        outputs: Dict[str, Any],
        agent_results: Dict[str, Any],
        generated_files: List[Dict] = None,
    ) -> None:
        """
        Persist a complete workflow to Supabase.
        Writes to: workflows, agent_outputs, generated_files, execution_history.
        Safe to call as asyncio.create_task() — never raises.
        """
        try:
            logger.info(f"[Supabase] Persisting workflow {workflow_id[:8]}...")
            now = time.time()

            # 1. Upsert workflow row
            await self._upsert("workflows", {
                "workflow_id": workflow_id,
                "user_id": user_id,
                "project_id": project_id,
                "user_input": user_input[:500],
                "status": status,
                "created_at": now,
                "updated_at": now,
                "output_summary": {
                    k: str(v)[:200] for k, v in (outputs or {}).items()
                },
            })

            # 2. Insert agent outputs
            output_rows = []
            for agent_name, result in (agent_results or {}).items():
                if hasattr(result, "data") and result.data:
                    output_rows.append({
                        "workflow_id": workflow_id,
                        "agent_name": agent_name,
                        "output_key": agent_name.lower().replace(" ", "_"),
                        "status": result.status.value if hasattr(result.status, "value") else str(result.status),
                        "data_preview": json.dumps(result.data, default=str)[:2000],
                        "execution_time": getattr(result, "execution_time", 0),
                        "created_at": now,
                    })
            if output_rows:
                inserted = await self._insert_many("agent_outputs", output_rows)
                logger.info(f"[Supabase] Inserted {inserted} agent_outputs")

            # 3. Insert generated file metadata (not content — just metadata)
            if generated_files:
                file_rows = []
                for f in generated_files:
                    path = f.get("path", "")
                    content = f.get("content", "")
                    ext = path.rsplit(".", 1)[-1] if "." in path else "txt"
                    file_rows.append({
                        "workflow_id": workflow_id,
                        "file_path": path,
                        "language": ext,
                        "size_bytes": len(content.encode("utf-8")),
                        "created_at": now,
                    })
                if file_rows:
                    inserted = await self._insert_many("generated_files", file_rows)
                    logger.info(f"[Supabase] Inserted {inserted} generated_files metadata")

            # 4. Execution history entry
            await self._upsert("execution_history", {
                "workflow_id": workflow_id,
                "user_id": user_id,
                "event": "workflow_completed",
                "status": status,
                "agents_run": len(agent_results or {}),
                "files_generated": len(generated_files or []),
                "timestamp": now,
            })

            logger.info(f"[Supabase] ✅ Workflow {workflow_id[:8]} persisted successfully")

        except Exception as e:
            logger.error(f"[Supabase] ❌ Failed to persist workflow {workflow_id}: {e}")

    async def save_artifact(self, workflow_id: str, artifact_type: str, path: str) -> bool:
        """Record a project artifact (e.g., zip download path)."""
        return await self._upsert("project_artifacts", {
            "workflow_id": workflow_id,
            "artifact_type": artifact_type,
            "artifact_path": path,
            "created_at": time.time(),
        })

    async def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Fetch a workflow record from Supabase."""
        if not self._enabled:
            return None
        url = f"{self._base}/workflows?workflow_id=eq.{workflow_id}&limit=1"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    rows = resp.json()
                    return rows[0] if rows else None
        except Exception as e:
            logger.warning(f"[Supabase] get_workflow error: {e}")
        return None


# Singleton
supabase_service = SupabaseService()
