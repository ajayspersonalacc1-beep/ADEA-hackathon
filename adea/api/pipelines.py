"""Pipeline API routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from adea.orchestration.langgraph_workflow import run_workflow
from adea.orchestration.state import PipelineState
from adea.utils.agent_status import build_agent_execution_status
from adea.utils.helpers import format_stage_log


router = APIRouter()
public_router = APIRouter(prefix="/api")

PIPELINE_STORE: dict[str, PipelineState] = {}


class CreatePipelineRequest(BaseModel):
    """Request payload for pipeline creation."""

    pipeline_id: str
    user_prompt: str


class CreatePipelineResponse(BaseModel):
    """Response payload for pipeline creation."""

    pipeline_id: str
    status: str


class PipelineStatusResponse(BaseModel):
    """Response payload for pipeline status lookup."""

    pipeline_id: str
    user_prompt: str
    status: str
    pipeline_plan: dict
    diagnosis: dict
    repair_action: dict
    optimization: dict
    logs: list[str]
    started_at: float | None
    finished_at: float | None


class PipelineSummaryResponse(BaseModel):
    """Response payload for listing stored pipeline summaries."""

    pipeline_id: str
    user_prompt: str
    status: str
    started_at: float | None
    finished_at: float | None
    diagnosis: dict
    repair_action: dict
    optimization: dict


class PipelineListResponse(BaseModel):
    """Response payload for listing stored pipelines."""

    pipelines: list[PipelineSummaryResponse]


class AgentExecutionItem(BaseModel):
    """Response payload for one agent execution item."""

    name: str
    status: str
    execution_time: str | None = None


class AgentExecutionStatusResponse(BaseModel):
    """Response payload for live pipeline execution status."""

    pipeline_id: str
    status: str
    progress: int
    agents: list[AgentExecutionItem]


def _run_pipeline_in_background(initial_state: PipelineState) -> None:
    """Execute a pipeline workflow in the background and persist the final state."""

    final_state = run_workflow(initial_state)
    PIPELINE_STORE[final_state.pipeline_id] = final_state


@router.post(
    "/create",
    response_model=CreatePipelineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pipeline(request: CreatePipelineRequest) -> CreatePipelineResponse:
    """Create a pipeline state, run the workflow, and store the result."""

    if request.pipeline_id in PIPELINE_STORE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pipeline '{request.pipeline_id}' already exists.",
        )

    initial_state = PipelineState(
        pipeline_id=request.pipeline_id,
        user_prompt=request.user_prompt,
    )
    final_state = run_workflow(initial_state)
    PIPELINE_STORE[final_state.pipeline_id] = final_state

    return CreatePipelineResponse(
        pipeline_id=final_state.pipeline_id,
        status=final_state.pipeline_status,
    )


@router.get(
    "/status/{pipeline_id}",
    response_model=PipelineStatusResponse,
)
def get_pipeline_status(pipeline_id: str) -> PipelineStatusResponse:
    """Return the latest in-memory pipeline status details."""

    state = PIPELINE_STORE.get(pipeline_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{pipeline_id}' not found.",
        )

    return PipelineStatusResponse(
        pipeline_id=state.pipeline_id,
        user_prompt=state.user_prompt,
        status=state.pipeline_status,
        pipeline_plan=state.pipeline_plan,
        diagnosis=state.diagnosis,
        repair_action=state.repair_action,
        optimization=state.optimization,
        logs=state.execution_logs,
        started_at=state.started_at,
        finished_at=state.finished_at,
    )


@router.get(
    "/list",
    response_model=PipelineListResponse,
)
def list_pipelines() -> PipelineListResponse:
    """Return the currently stored pipeline identifiers."""

    summaries = [
        PipelineSummaryResponse(
            pipeline_id=state.pipeline_id,
            user_prompt=state.user_prompt,
            status=state.pipeline_status,
            started_at=state.started_at,
            finished_at=state.finished_at,
            diagnosis=state.diagnosis,
            repair_action=state.repair_action,
            optimization=state.optimization,
        )
        for state in sorted(
            PIPELINE_STORE.values(),
            key=lambda item: item.pipeline_id.lower(),
        )
    ]
    return PipelineListResponse(pipelines=summaries)


@public_router.post(
    "/run_pipeline",
    response_model=CreatePipelineResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_pipeline_alias(
    request: CreatePipelineRequest,
    background_tasks: BackgroundTasks,
) -> CreatePipelineResponse:
    """Start a pipeline workflow asynchronously for frontend clients."""

    if request.pipeline_id in PIPELINE_STORE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pipeline '{request.pipeline_id}' already exists.",
        )

    initial_state = PipelineState(
        pipeline_id=request.pipeline_id,
        user_prompt=request.user_prompt,
    )
    initial_state.update_status("running")
    initial_state.append_log(
        format_stage_log("WORKFLOW", "Pipeline queued for background execution.")
    )
    PIPELINE_STORE[initial_state.pipeline_id] = initial_state
    background_tasks.add_task(_run_pipeline_in_background, initial_state)

    return CreatePipelineResponse(
        pipeline_id=initial_state.pipeline_id,
        status=initial_state.pipeline_status,
    )


@public_router.get(
    "/pipeline_status/{pipeline_id}",
    response_model=AgentExecutionStatusResponse,
)
def get_pipeline_execution_status(pipeline_id: str) -> AgentExecutionStatusResponse:
    """Return the live agent execution status for one pipeline."""

    state = PIPELINE_STORE.get(pipeline_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{pipeline_id}' not found.",
        )

    payload = build_agent_execution_status(state)
    return AgentExecutionStatusResponse(**payload)
