"""Monitoring agent for simple anomaly classification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adea.agents.base_agent import BaseAgent
from adea.utils.helpers import format_stage_log

if TYPE_CHECKING:
    from adea.orchestration.state import PipelineState


class MonitoringAgent(BaseAgent):
    """Analyze execution state and classify simple anomalies."""

    def run(self, state: PipelineState) -> PipelineState:
        """Inspect pipeline execution results and update anomaly state."""

        if state.pipeline_status == "success":
            state.append_log(
                format_stage_log("MONITOR", "No anomalies detected")
            )
            return state

        if state.pipeline_status == "failed":
            state.append_log(
                format_stage_log(
                    "MONITOR",
                    "Monitoring analyzing execution results...",
                )
            )
            anomaly_type = self._classify_anomaly(
                error_type=state.error_type,
                execution_logs=state.execution_logs,
            )
            state.diagnosis["anomaly_type"] = anomaly_type
            state.update_status("anomaly_detected")
            state.append_log(
                format_stage_log(
                    "MONITOR",
                    f"Monitoring classified anomaly as '{anomaly_type}'.",
                )
            )
            state.append_log(
                format_stage_log("MONITOR", self._build_anomaly_message(anomaly_type))
            )
            return state

        state.append_log(
            format_stage_log(
                "MONITOR",
                f"Monitoring skipped anomaly classification for status '{state.pipeline_status}'.",
            )
        )
        return state

    def _classify_anomaly(self, error_type: str, execution_logs: list[str]) -> str:
        """Classify the anomaly using the recorded error type and logs."""

        error_text = error_type.lower()
        log_text = self._latest_failure_context(execution_logs).lower()
        combined_text = f"{error_text} {log_text}".strip()

        if "column" in combined_text and (
            "not found" in combined_text
            or "does not exist" in combined_text
            or "unknown" in combined_text
            or "invalid" in combined_text
            or "binder" in combined_text
        ):
            return "runtime_error"

        if "already exists" in combined_text or "table exists" in combined_text:
            return "table_exists"

        if "table" in combined_text and (
            "not found" in combined_text
            or "does not exist" in combined_text
            or "missing" in combined_text
            or "catalog" in combined_text
        ):
            return "missing_table"

        if "syntax" in combined_text or "parser" in combined_text:
            return "syntax_error"

        return "unknown_runtime_error"

    def _latest_failure_context(self, execution_logs: list[str]) -> str:
        """Return the most recent failure-oriented log entry for classification."""

        for log in reversed(execution_logs):
            lowered_log = log.lower()
            if "pipeline execution failed" in lowered_log:
                return log

        if execution_logs:
            return execution_logs[-1]

        return ""

    def _build_anomaly_message(self, anomaly_type: str) -> str:
        """Return a human-readable monitoring summary for the anomaly."""

        if anomaly_type == "missing_table":
            return "Monitoring detected a missing table anomaly."

        if anomaly_type == "syntax_error":
            return "Monitoring detected a SQL syntax anomaly."

        if anomaly_type == "table_exists":
            return "Monitoring detected a table already exists anomaly."

        return "Monitoring detected an unknown runtime execution anomaly."
