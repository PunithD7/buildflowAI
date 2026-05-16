"""
Workflows endpoints - Trigger and monitor multi-agent workflows

FIXES APPLIED:
  - Replaced background_tasks.add_task() with asyncio.create_task() so the
    workflow coroutine runs in the same event loop as WebSocket handlers.
  - Added 2-second startup delay before orchestrator execution begins. This
    closes the race window: POST response → frontend navigation → WebSocket connect
    all happen before the orchestrator starts emitting events.
  - Enhanced error logging in _run_workflow_background.
  - Added /workflows/{id}/debug endpoint for inspecting live execution state.
"""
import asyncio
import logging
import time
import uuid
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel

from app.agents.orchestrator import orchestrator, WorkflowStatus

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory workflow store
_workflows_db: Dict[str, Dict] = {}

# Startup delay in seconds — gives the frontend time to connect via WebSocket
# before the orchestrator starts emitting events. Closes the POST→WS race window.
_WS_CONNECT_GRACE_SECONDS = 2.0


class StartWorkflowRequest(BaseModel):
    project_id: str
    user_input: str
    user_id: Optional[str] = "anonymous"
    agents_to_run: Optional[list] = None  # None = all agents


class WorkflowResponse(BaseModel):
    workflow_id: str
    project_id: str
    status: str
    user_input: str
    created_at: float
    message: str


@router.post("", response_model=WorkflowResponse, status_code=202)
async def start_workflow(request: StartWorkflowRequest):
    """
    Start a new multi-agent workflow execution.
    Returns immediately with workflow_id; execution begins after a short grace
    period to allow the frontend WebSocket to connect before events are emitted.

    FIX: Using asyncio.create_task() instead of BackgroundTasks.add_task() so
    the workflow coroutine runs in the same event loop as the WebSocket manager.
    """
    workflow_id = str(uuid.uuid4())

    workflow = {
        "workflow_id": workflow_id,
        "project_id": request.project_id,
        "user_input": request.user_input,
        "user_id": request.user_id,
        "status": WorkflowStatus.PENDING.value,
        "created_at": time.time(),
        "outputs": None,
        "error": None,
    }
    _workflows_db[workflow_id] = workflow

    logger.info(
        f"[Workflows] New workflow created | id={workflow_id} "
        f"user={request.user_id} project={request.project_id} "
        f"input_preview={request.user_input[:80]!r}"
    )

    # FIX: Schedule as asyncio task in the current event loop.
    # This runs concurrently with WebSocket handlers unlike BackgroundTasks
    # which runs after the response is fully sent.
    asyncio.create_task(
        _run_workflow_background(
            workflow_id=workflow_id,
            user_input=request.user_input,
            user_id=request.user_id,
            project_id=request.project_id,
        ),
        name=f"workflow-{workflow_id[:8]}",
    )

    logger.info(
        f"[Workflows] Workflow task scheduled | id={workflow_id} "
        f"grace_period={_WS_CONNECT_GRACE_SECONDS}s"
    )

    return WorkflowResponse(
        workflow_id=workflow_id,
        project_id=request.project_id,
        status=WorkflowStatus.PENDING.value,
        user_input=request.user_input,
        created_at=time.time(),
        message=(
            f"Workflow started. Connect to WebSocket /ws/{workflow_id} for real-time updates. "
            f"Execution begins in {_WS_CONNECT_GRACE_SECONDS}s."
        ),
    )


async def _run_workflow_background(
    workflow_id: str,
    user_input: str,
    user_id: str,
    project_id: str,
):
    """
    Background coroutine to execute the workflow.

    FIX: Added startup grace period before calling orchestrator.execute_workflow().
    This gives the frontend time to navigate to the WorkflowExecution page and
    establish a WebSocket connection before the first events are emitted.
    Without this delay, workflow_started, stage_started, and the first agent's
    started event are all emitted before any client has connected, causing them
    to be dropped (even with the replay buffer, the WS might not be open yet).
    """
    logger.info(
        f"[Workflows] Background task started | id={workflow_id} "
        f"grace_period={_WS_CONNECT_GRACE_SECONDS}s"
    )

    # Update to pending so UI can show the workflow exists
    _workflows_db[workflow_id]["status"] = WorkflowStatus.PENDING.value

    try:
        # Grace period: allow frontend to navigate and open WebSocket
        logger.info(
            f"[Workflows] ⏳ Waiting {_WS_CONNECT_GRACE_SECONDS}s for WebSocket connection "
            f"| id={workflow_id}"
        )
        await asyncio.sleep(_WS_CONNECT_GRACE_SECONDS)

        # Update to running
        _workflows_db[workflow_id]["status"] = WorkflowStatus.RUNNING.value
        logger.info(f"[Workflows] 🚀 Launching orchestrator | id={workflow_id}")

        result = await orchestrator.execute_workflow(
            workflow_id=workflow_id,
            user_input=user_input,
            user_id=user_id,
            project_id=project_id,
        )

        final_status = result.get("status", WorkflowStatus.FAILED.value)
        _workflows_db[workflow_id].update({
            "status": final_status,
            "outputs": result.get("outputs"),
            "error": result.get("error"),
            "completed_at": time.time(),
        })

        logger.info(
            f"[Workflows] ✅ Workflow finished | id={workflow_id} status={final_status}"
        )

    except asyncio.CancelledError:
        logger.warning(f"[Workflows] Workflow task cancelled | id={workflow_id}")
        _workflows_db[workflow_id]["status"] = WorkflowStatus.CANCELLED.value

    except Exception as e:
        logger.error(
            f"[Workflows] ❌ Workflow background task crashed | id={workflow_id}: {e}",
            exc_info=True,
        )
        _workflows_db[workflow_id].update({
            "status": WorkflowStatus.FAILED.value,
            "error": str(e),
            "completed_at": time.time(),
        })


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow status and outputs."""
    workflow = _workflows_db.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Merge with orchestrator status for real-time data
    orchestrator_status = orchestrator.get_workflow_status(workflow_id) or {}

    return {
        **workflow,
        "agents_completed": orchestrator_status.get("agents_completed", 0),
        "agents_failed": orchestrator_status.get("agents_failed", 0),
        "total_agents": orchestrator_status.get("total_agents", 13),
        "stages_completed": orchestrator_status.get("stages_completed", 0),
        "duration": orchestrator_status.get("duration"),
    }


@router.get("/{workflow_id}/outputs")
async def get_workflow_outputs(workflow_id: str):
    """Get structured outputs from a completed workflow."""
    workflow = _workflows_db.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow["status"] not in [WorkflowStatus.COMPLETED.value, WorkflowStatus.PARTIALLY_COMPLETED.value]:
        return {"status": workflow["status"], "outputs": None, "message": "Workflow not yet complete"}

    return {"status": workflow["status"], "outputs": workflow.get("outputs")}


@router.get("/{workflow_id}/debug")
async def debug_workflow(workflow_id: str):
    """Debug endpoint: inspect live orchestrator + WebSocket state for a workflow."""
    from app.core.websocket_manager import ws_manager

    workflow = _workflows_db.get(workflow_id)
    orchestrator_status = orchestrator.get_workflow_status(workflow_id)

    ws_room_size = len(ws_manager._rooms.get(workflow_id, set()))
    buffer_size = len(ws_manager._replay_buffers.get(workflow_id, []))

    return {
        "workflow_id": workflow_id,
        "db_entry": workflow,
        "orchestrator_status": orchestrator_status,
        "websocket": {
            "clients_in_room": ws_room_size,
            "replay_buffer_events": buffer_size,
            "total_connections": ws_manager.connection_count,
        },
        "llm_providers": {
            "available": __import__("app.agents.llm_client", fromlist=["llm_router"]).llm_router.available_providers,
            "real_providers": __import__("app.agents.llm_client", fromlist=["llm_router"]).llm_router.real_providers,
        },
    }


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """Cancel an active workflow."""
    if workflow_id not in _workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    cancelled = orchestrator.cancel_workflow(workflow_id)
    if cancelled:
        _workflows_db[workflow_id]["status"] = WorkflowStatus.CANCELLED.value
        logger.info(f"[Workflows] Workflow cancelled | id={workflow_id}")
        return {"message": "Workflow cancelled", "workflow_id": workflow_id}

    return {"message": "Workflow not active or already completed", "workflow_id": workflow_id}


@router.get("")
async def list_workflows(project_id: Optional[str] = None):
    """List all workflows, optionally filtered by project."""
    workflows = list(_workflows_db.values())
    if project_id:
        workflows = [w for w in workflows if w["project_id"] == project_id]
    return sorted(workflows, key=lambda x: x["created_at"], reverse=True)
