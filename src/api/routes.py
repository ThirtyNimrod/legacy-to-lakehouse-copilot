from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.api.runner import runner_manager
from src.config import settings

router = APIRouter()


class StartRunRequest(BaseModel):
    tables: Optional[List[str]] = None
    target: str = "LOCAL · DUCKDB"
    provider: str = "ollama"


class ResumeThreadRequest(BaseModel):
    action: str  # "approve" | "changes" | "abort"
    feedback: Optional[str] = None
    column_overrides: Optional[Dict[str, str]] = None


@router.get("/health")
def get_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "target_environment": "LOCAL · DUCKDB",
        "model_name": settings.llm.model_name,
        "provider": settings.llm.provider,
    }


@router.post("/runs")
async def start_run(req: StartRunRequest) -> Dict[str, Any]:
    run_id = await runner_manager.start_new_run(
        tables=req.tables,
        target_env=req.target,
        provider=req.provider,
    )
    return {"run_id": run_id, "status": "STARTED"}


@router.get("/runs/{run_id}")
def get_run_board(run_id: str) -> Dict[str, Any]:
    return runner_manager.get_board(run_id)


@router.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str):
    """Server-Sent Events endpoint streaming live graph node execution and logs."""
    return EventSourceResponse(runner_manager.event_generator(run_id))


@router.get("/threads/{thread_id}/state")
def get_thread_state(thread_id: str) -> Dict[str, Any]:
    """Returns full review snapshot for Table Review page."""
    try:
        return runner_manager.get_thread_state(thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threads/{thread_id}/resume")
async def resume_thread(thread_id: str, req: ResumeThreadRequest) -> Dict[str, Any]:
    """Resumes paused LangGraph thread with approve/changes/abort action."""
    try:
        updated_state = await runner_manager.resume_thread(
            thread_id=thread_id,
            action=req.action,
            feedback=req.feedback,
            column_overrides=req.column_overrides,
        )
        return {"status": "SUCCESS", "state": updated_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fixtures/{fixture_name}")
def get_fixture(fixture_name: str) -> Dict[str, Any]:
    """Serves static test fixtures (passed, mid_repair, failed_closed)."""
    return runner_manager.get_thread_state(f"fixture_{fixture_name}")
