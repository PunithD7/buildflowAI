"""
File Writer Service

Writes generated project files to the filesystem under:
  /app/generated_projects/{workflow_id}/

Provides:
  - write_project_files()  — write files from agent manifest
  - create_zip_archive()   — create downloadable ZIP
  - get_file_tree()        — recursive directory listing
  - get_file_content()     — read a specific file safely
"""
import asyncio
import io
import logging
import os
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileWriterService:
    """Writes LLM-generated project files to a structured filesystem layout."""

    def __init__(self):
        self._base_dir = Path(settings.GENERATED_PROJECTS_DIR).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[FileWriter] Base directory: {self._base_dir}")

    def _project_dir(self, workflow_id: str) -> Path:
        """Return the project root directory for a workflow."""
        # Sanitize workflow_id to prevent path traversal
        safe_id = "".join(c for c in workflow_id if c.isalnum() or c in "-_")
        return self._base_dir / safe_id

    def _safe_path(self, project_dir: Path, relative_path: str) -> Optional[Path]:
        """Resolve a relative path safely — reject anything escaping project_dir."""
        try:
            resolved = (project_dir / relative_path).resolve()
            resolved.relative_to(project_dir)  # raises ValueError if outside
            return resolved
        except (ValueError, Exception):
            logger.warning(f"[FileWriter] Rejected unsafe path: {relative_path!r}")
            return None

    async def write_project_files(
        self, workflow_id: str, files: List[Dict[str, str]]
    ) -> List[str]:
        """
        Write a list of {path, content} dicts to disk.
        Returns a list of written relative paths.
        """
        project_dir = self._project_dir(workflow_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        written: List[str] = []
        errors: int = 0

        # Write a manifest file first
        manifest_lines = [
            f"# BuildFlow Generated Project",
            f"# workflow_id: {workflow_id}",
            f"# generated_at: {time.strftime('%Y-%m-%d %Human:%M:%S UTC', time.gmtime())}",
            f"# total_files: {len(files)}",
            "",
        ] + [f.get("path", "?") for f in files]

        manifest_path = project_dir / ".buildflow_manifest.txt"
        manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")

        for file_info in files:
            rel_path = (file_info.get("path") or "").strip().lstrip("/")
            content = file_info.get("content", "")

            if not rel_path:
                continue

            target = self._safe_path(project_dir, rel_path)
            if not target:
                errors += 1
                continue

            try:
                # Run in thread pool to avoid blocking the event loop
                await asyncio.to_thread(self._write_file, target, content)
                written.append(rel_path)
                logger.debug(f"[FileWriter] ✅ {rel_path} ({len(content)} bytes)")
            except Exception as e:
                errors += 1
                logger.error(f"[FileWriter] ❌ Failed to write {rel_path}: {e}")

        logger.info(
            f"[FileWriter] Project {workflow_id[:8]} | "
            f"written={len(written)} errors={errors} total={len(files)}"
        )
        return written

    def _write_file(self, target: Path, content: str) -> None:
        """Synchronous file write — call via asyncio.to_thread()."""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    async def create_zip_archive(self, workflow_id: str) -> Optional[bytes]:
        """
        Create an in-memory ZIP of the entire generated project.
        Returns bytes or None if project doesn't exist.
        """
        project_dir = self._project_dir(workflow_id)
        if not project_dir.exists():
            return None

        def _zip() -> bytes:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in sorted(project_dir.rglob("*")):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(project_dir)
                        zf.write(file_path, arcname=str(arc_name))
            return buf.getvalue()

        data = await asyncio.to_thread(_zip)
        logger.info(f"[FileWriter] ZIP created | workflow={workflow_id[:8]} size={len(data):,}B")
        return data

    async def get_file_tree(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Return a recursive file tree for a project.
        Each entry: {path, type, size, language}
        """
        project_dir = self._project_dir(workflow_id)
        if not project_dir.exists():
            return []

        def _tree() -> List[Dict]:
            entries = []
            for p in sorted(project_dir.rglob("*")):
                if p.name.startswith(".") and p.name != ".env.example":
                    continue
                rel = str(p.relative_to(project_dir))
                if p.is_file():
                    ext = p.suffix.lstrip(".")
                    entries.append({
                        "path": rel,
                        "type": "file",
                        "size": p.stat().st_size,
                        "language": _ext_to_language(ext),
                    })
                else:
                    entries.append({"path": rel, "type": "directory"})
            return entries

        return await asyncio.to_thread(_tree)

    async def get_file_content(self, workflow_id: str, relative_path: str) -> Optional[str]:
        """Read a specific file. Returns None if not found or unsafe path."""
        project_dir = self._project_dir(workflow_id)
        target = self._safe_path(project_dir, relative_path)
        if not target or not target.is_file():
            return None
        # Limit file size to 500 KB to prevent memory issues
        if target.stat().st_size > 500_000:
            return f"[File too large to display: {target.stat().st_size:,} bytes]"
        return await asyncio.to_thread(target.read_text, "utf-8")

    def project_exists(self, workflow_id: str) -> bool:
        """Check if a generated project exists for this workflow."""
        return self._project_dir(workflow_id).exists()

    def file_count(self, workflow_id: str) -> int:
        """Return the number of generated files for a workflow."""
        project_dir = self._project_dir(workflow_id)
        if not project_dir.exists():
            return 0
        return sum(1 for p in project_dir.rglob("*") if p.is_file())


def _ext_to_language(ext: str) -> str:
    """Map file extension to language label."""
    return {
        "tsx": "typescript", "ts": "typescript", "jsx": "javascript",
        "js": "javascript", "py": "python", "json": "json",
        "yaml": "yaml", "yml": "yaml", "md": "markdown",
        "html": "html", "css": "css", "env": "bash",
        "dockerfile": "dockerfile", "toml": "toml", "txt": "text",
        "sh": "bash", "gitignore": "bash",
    }.get(ext.lower(), "text")


# Singleton
file_writer_service = FileWriterService()
