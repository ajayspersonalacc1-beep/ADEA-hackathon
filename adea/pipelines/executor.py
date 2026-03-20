"""Pipeline execution engine for sequential DuckDB-based pipeline steps."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Protocol

import duckdb
from adea.pipelines.builder import PipelineBuilder
from adea.utils.helpers import format_stage_log

if TYPE_CHECKING:
    from adea.orchestration.state import PipelineState


logger = logging.getLogger(__name__)


class SupportsPipelineState(Protocol):
    """Protocol describing the state surface the executor needs."""

    pipeline_plan: dict[str, Any]
    error_type: str
    started_at: float | None
    finished_at: float | None

    def update_status(self, new_status: str) -> Any:
        ...

    def append_log(self, message: str) -> Any:
        ...

    def record_failure(self, error_type: str) -> Any:
        ...


class PipelineExecutor:
    """Execute pipeline plan steps sequentially using DuckDB."""

    def __init__(self, database_path: str = ":memory:") -> None:
        self.database_path = database_path
        self.builder = PipelineBuilder()

    def run(self, state: PipelineState) -> PipelineState:
        """Execute the pipeline plan and return the updated state."""

        runtime_state: SupportsPipelineState = state
        total_steps = 0
        current_step = 0
        execution_started_at = time.perf_counter()

        runtime_state.started_at = time.time()
        runtime_state.finished_at = None
        runtime_state.update_status("running")
        runtime_state.error_type = ""
        runtime_state.append_log(format_stage_log("EXECUTOR", "Pipeline execution started."))

        connection = duckdb.connect(database=self.database_path)

        try:
            ordered_plan = self.builder.order_plan(runtime_state.pipeline_plan)
            runtime_state.pipeline_plan = ordered_plan
            steps = self._extract_steps(ordered_plan)
            total_steps = len(steps)
            runtime_state.append_log(
                format_stage_log(
                    "EXECUTOR",
                    f"Loaded pipeline plan with {total_steps} step(s).",
                )
            )

            for current_step, step in enumerate(steps, start=1):
                self._execute_step(
                    connection=connection,
                    state=runtime_state,
                    step=step,
                    step_number=current_step,
                    total_steps=total_steps,
                )

            total_duration = time.perf_counter() - execution_started_at
            runtime_state.update_status("success")
            runtime_state.append_log(
                format_stage_log(
                    "EXECUTOR",
                    f"Pipeline execution completed successfully in {total_duration:.4f}s.",
                )
            )
        except Exception as exc:
            total_duration = time.perf_counter() - execution_started_at
            runtime_state.update_status("failed")
            runtime_state.record_failure(type(exc).__name__)
            logger.debug("Pipeline execution failed", exc_info=True)
            runtime_state.append_log(
                format_stage_log(
                    "EXECUTOR",
                    "Pipeline execution failed"
                    f" at step {current_step or 1}/{max(total_steps, 1)}"
                    f" after {total_duration:.4f}s: {exc}",
                )
            )
        finally:
            runtime_state.finished_at = time.time()
            connection.close()

        return state

    def _extract_steps(self, pipeline_plan: dict[str, Any]) -> list[dict[str, Any]]:
        """Return the list of steps from the pipeline plan."""

        steps = pipeline_plan.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError("Pipeline plan must define 'steps' as a list.")

        return steps

    def _execute_step(
        self,
        connection: duckdb.DuckDBPyConnection,
        state: SupportsPipelineState,
        step: dict[str, Any],
        step_number: int,
        total_steps: int,
    ) -> None:
        """Execute a single pipeline step and append runtime metrics to logs."""

        if not isinstance(step, dict):
            raise ValueError(f"Step {step_number} must be a dictionary.")

        step_type = step.get("type")
        if step_type != "sql":
            raise ValueError(f"Unsupported step type at step {step_number}: {step_type!r}")

        query = step.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Step {step_number} must include a non-empty SQL query.")

        state.append_log(
            format_stage_log(
                "EXECUTOR",
                f"Executing step {step_number}/{total_steps}: sql",
            )
        )
        state.append_log(format_stage_log("EXECUTOR", f"SQL Query: {query[:120]}"))

        step_started_at = time.perf_counter()
        result = connection.execute(query)
        row_count = self._count_rows(result)
        step_duration = time.perf_counter() - step_started_at

        state.append_log(
            format_stage_log(
                "EXECUTOR",
                f"Step {step_number}/{total_steps} finished in {step_duration:.4f}s"
                f" with {row_count} row(s).",
            )
        )

    def _count_rows(self, result: duckdb.DuckDBPyConnection) -> int:
        """Return the number of rows produced by the executed statement."""

        try:
            row_count = result.rowcount
        except Exception:
            return 0

        if row_count is None or row_count < 0:
            return 0

        return row_count
