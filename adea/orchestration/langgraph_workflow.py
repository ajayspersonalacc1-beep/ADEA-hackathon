"""LangGraph workflow controller for the ADEA orchestration layer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

if TYPE_CHECKING:
    try:
        from langgraph.graph import CompiledGraph
    except ImportError:
        CompiledGraph = Any

from adea.agents.diagnosis_agent import DiagnosisAgent
from adea.agents.monitoring_agent import MonitoringAgent
from adea.agents.optimization_agent import OptimizationAgent
from adea.agents.pipeline_generator_agent import PipelineGeneratorAgent
from adea.agents.repair_agent import RepairAgent
from adea.agents.schema_discovery_agent import SchemaDiscoveryAgent
from adea.llm.groq_client import reset_llm_budget
from adea.orchestration.state import PipelineState
from adea.pipelines.executor import PipelineExecutor
from adea.utils.helpers import format_stage_log


def build_workflow(
    database_path: str = ":memory:",
    retry_limit: int = 2,
) -> CompiledGraph:
    """Build and compile the ADEA LangGraph workflow."""

    pipeline_generator = PipelineGeneratorAgent()
    pipeline_executor = PipelineExecutor(database_path=database_path)
    monitoring = MonitoringAgent()
    diagnosis = DiagnosisAgent()
    repair = RepairAgent()
    optimization = OptimizationAgent()
    schema_discovery = SchemaDiscoveryAgent(database_path=database_path)

    graph = StateGraph(PipelineState)

    graph.add_node("pipeline_generator", pipeline_generator.run)
    graph.add_node("pipeline_executor", pipeline_executor.run)
    graph.add_node("monitoring", monitoring.run)
    graph.add_node("diagnosis", diagnosis.run)
    graph.add_node("repair", _build_repair_node(repair, retry_limit))
    graph.add_node("optimization", optimization.run)
    graph.add_node("schema_discovery", schema_discovery.run)

    graph.add_edge(START, "pipeline_generator")
    graph.add_edge("pipeline_generator", "pipeline_executor")
    graph.add_edge("pipeline_executor", "monitoring")

    graph.add_conditional_edges(
        "monitoring",
        _route_after_monitoring,
        {
            "schema_discovery": "schema_discovery",
            "optimization": "optimization",
            "end": END,
        },
    )
    graph.add_edge("schema_discovery", "diagnosis")
    graph.add_edge("diagnosis", "repair")
    graph.add_edge("optimization", END)
    graph.add_conditional_edges(
        "repair",
        _build_repair_router(retry_limit),
        {
            "pipeline_executor": "pipeline_executor",
            "end": END,
        },
    )

    return graph.compile()


def run_workflow(
    initial_state: PipelineState,
    database_path: str = ":memory:",
    retry_limit: int = 2,
) -> PipelineState:
    """Execute the compiled workflow for the provided initial state."""

    reset_llm_budget()
    resolved_database_path, is_temporary_database = _resolve_database_path(
        initial_state,
        database_path,
    )
    try:
        graph = build_workflow(
            database_path=resolved_database_path,
            retry_limit=retry_limit,
        )
        result = graph.invoke(initial_state)
        if isinstance(result, PipelineState):
            return result

        if isinstance(result, dict):
            return PipelineState(**result)

        raise TypeError(f"Unexpected workflow result type: {type(result)!r}")
    finally:
        _cleanup_temporary_database(resolved_database_path, is_temporary_database)


def _build_repair_node(
    repair_agent: RepairAgent,
    retry_limit: int,
) -> Callable[[PipelineState], PipelineState]:
    """Wrap the repair agent to maintain retry metadata in pipeline state."""

    def repair_node(state: PipelineState) -> PipelineState:
        current_retry_count = state.retry_count
        state.append_log(
            format_stage_log("WORKFLOW", f"Repair cycle {current_retry_count + 1}")
        )
        state.append_log(
            format_stage_log(
                "WORKFLOW",
                f"Workflow evaluating repair attempt {current_retry_count + 1} of {retry_limit}.",
            )
        )
        return repair_agent.run(state)

    return repair_node


def _route_after_monitoring(state: PipelineState) -> str:
    """Route the workflow after monitoring based on pipeline status."""

    if state.pipeline_status == "anomaly_detected":
        return "schema_discovery"

    if state.pipeline_status == "success":
        return "optimization"

    if state.pipeline_status == "failed":
        return "schema_discovery"

    return "end"


def _build_repair_router(retry_limit: int) -> Callable[[PipelineState], str]:
    """Build a repair router that respects the configured retry limit."""

    def route_after_repair(state: PipelineState) -> str:
        """Route the workflow after repair, respecting retry and recovery state."""

        if state.pipeline_status == "unrecoverable":
            return "end"

        if state.pipeline_status != "repaired":
            return "end"

        retry_count = state.retry_count
        if retry_count >= retry_limit:
            state.append_log(
                format_stage_log(
                    "WORKFLOW",
                    "Workflow reached the maximum repair retry limit.",
                )
            )
            return "end"

        state.append_log(
            format_stage_log(
                "WORKFLOW",
                f"Retrying pipeline execution (attempt {retry_count + 1}/{retry_limit}).",
            )
        )
        state.append_log(
            format_stage_log(
                "WORKFLOW",
                "Workflow routing repaired pipeline back to executor for retry.",
            )
        )
        state.retry_count += 1
        return "pipeline_executor"

    return route_after_repair


def _resolve_database_path(
    initial_state: PipelineState,
    database_path: str,
) -> tuple[str, bool]:
    """Return a workflow-scoped DuckDB path that persists across nodes."""

    if database_path != ":memory:":
        return database_path, False

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_pipeline_id = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in initial_state.pipeline_id
    ).strip("_") or "pipeline"

    return str(output_dir / f"{safe_pipeline_id}_{uuid4().hex}.duckdb"), True


def _cleanup_temporary_database(database_path: str, is_temporary_database: bool) -> None:
    """Delete the workflow-scoped DuckDB file after the run completes."""

    if not is_temporary_database:
        return

    try:
        Path(database_path).unlink(missing_ok=True)
    except OSError:
        return
