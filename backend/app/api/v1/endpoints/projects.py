"""
Projects endpoints
"""
import time
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory store (replace with Supabase)
_projects_db: dict = {}


class CreateProjectRequest(BaseModel):
    name: str
    description: str
    type: Optional[str] = "general"  # startup, saas, hackathon, college, repo_analysis


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    type: str
    status: str
    created_at: float
    workflow_count: int = 0


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(request: CreateProjectRequest):
    """Create a new project workspace."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": request.name,
        "description": request.description,
        "type": request.type,
        "status": "active",
        "created_at": time.time(),
        "workflow_count": 0,
        "workflows": [],
    }
    _projects_db[project_id] = project
    return ProjectResponse(**{k: v for k, v in project.items() if k != "workflows"})


@router.get("", response_model=List[ProjectResponse])
async def list_projects():
    """List all projects."""
    projects = []
    for p in _projects_db.values():
        projects.append(ProjectResponse(**{k: v for k, v in p.items() if k != "workflows"}))
    return sorted(projects, key=lambda x: x.created_at, reverse=True)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project by ID."""
    project = _projects_db.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**{k: v for k, v in project.items() if k != "workflows"})


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    del _projects_db[project_id]
    return {"message": "Project deleted"}


def get_projects_db():
    return _projects_db
