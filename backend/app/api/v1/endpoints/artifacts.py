"""
Artifacts API — File browsing, content viewing, and ZIP download
for generated projects.

Endpoints:
  GET /artifacts/{workflow_id}/files            — file tree
  GET /artifacts/{workflow_id}/files/{path}     — file content
  GET /artifacts/{workflow_id}/download         — stream ZIP
  GET /artifacts/{workflow_id}/metadata         — stats + info
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path as FPath
from fastapi.responses import Response, StreamingResponse

from app.services.file_writer import file_writer_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{workflow_id}/files")
async def list_generated_files(workflow_id: str):
    """List all generated files for a workflow as a file tree."""
    if not file_writer_service.project_exists(workflow_id):
        raise HTTPException(
            status_code=404,
            detail=f"No generated project found for workflow {workflow_id}"
        )
    tree = await file_writer_service.get_file_tree(workflow_id)
    return {
        "workflow_id": workflow_id,
        "file_count": sum(1 for f in tree if f["type"] == "file"),
        "directory_count": sum(1 for f in tree if f["type"] == "directory"),
        "tree": tree,
    }


@router.get("/{workflow_id}/files/{file_path:path}")
async def get_file_content(workflow_id: str, file_path: str):
    """Get the content of a specific generated file."""
    if not file_writer_service.project_exists(workflow_id):
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file_writer_service.get_file_content(workflow_id, file_path)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_path}' not found in project {workflow_id}"
        )

    # Detect language from extension for syntax highlighting hint
    ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "txt"
    from app.services.file_writer import _ext_to_language
    language = _ext_to_language(ext)

    return {
        "workflow_id": workflow_id,
        "path": file_path,
        "content": content,
        "language": language,
        "size": len(content.encode("utf-8")),
    }


@router.get("/{workflow_id}/download")
async def download_project_zip(workflow_id: str):
    """
    Stream the entire generated project as a ZIP file.
    Returns a downloadable ZIP with all generated files.
    """
    if not file_writer_service.project_exists(workflow_id):
        raise HTTPException(status_code=404, detail="No generated project found")

    logger.info(f"[Artifacts] ZIP download requested | workflow={workflow_id[:8]}")

    zip_data = await file_writer_service.create_zip_archive(workflow_id)
    if not zip_data:
        raise HTTPException(status_code=500, detail="Failed to create ZIP archive")

    filename = f"buildflow-project-{workflow_id[:8]}.zip"

    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_data)),
        },
    )


@router.get("/{workflow_id}/metadata")
async def get_artifact_metadata(workflow_id: str):
    """
    Get metadata about a generated project:
    - file count, total size, download URL, Supabase reference.
    """
    if not file_writer_service.project_exists(workflow_id):
        return {
            "workflow_id": workflow_id,
            "exists": False,
            "file_count": 0,
            "message": "Project not yet generated",
        }

    tree = await file_writer_service.get_file_tree(workflow_id)
    files_only = [f for f in tree if f["type"] == "file"]
    total_size = sum(f.get("size", 0) for f in files_only)

    # Language breakdown
    lang_counts: dict = {}
    for f in files_only:
        lang = f.get("language", "text")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    return {
        "workflow_id": workflow_id,
        "exists": True,
        "file_count": len(files_only),
        "total_size_bytes": total_size,
        "total_size_kb": round(total_size / 1024, 1),
        "languages": lang_counts,
        "download_url": f"/api/v1/artifacts/{workflow_id}/download",
        "files_url": f"/api/v1/artifacts/{workflow_id}/files",
    }
