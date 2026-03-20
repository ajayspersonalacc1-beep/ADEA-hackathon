"""Diagnosis agent for deterministic root-cause analysis."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from adea.agents.base_agent import BaseAgent
from adea.llm.groq_client import LLM_BUDGET_MESSAGE, generate_json
from adea.memory.failure_memory import FailureMemory
from adea.utils.helpers import format_stage_log

if TYPE_CHECKING:
    from adea.orchestration.state import PipelineState


class DiagnosisAgent(BaseAgent):
    """Analyze monitoring signals and determine a root cause."""

    MIN_CONFIDENCE = 0.10

    def run(self, state: PipelineState) -> PipelineState:
        """Diagnose the pipeline failure and update the shared state."""

        if state.pipeline_status != "anomaly_detected":
            state.append_log(
                format_stage_log(
                    "DIAGNOSIS",
                    f"Diagnosis skipped because pipeline status is '{state.pipeline_status}'.",
                )
            )
            return state

        state.append_log(
            format_stage_log("DIAGNOSIS", "Diagnosis started root-cause analysis.")
        )
        state.append_log(
            format_stage_log("DIAGNOSIS", "Diagnosis analyzing anomaly signals...")
        )
        anomaly_type = str(state.diagnosis.get("anomaly_type", ""))

        llm_result = self._llm_root_cause(
            state=state,
            error_type=state.error_type,
            execution_logs=state.execution_logs,
            schema=dict(state.diagnosis.get("schema", {})),
        )

        if llm_result:
            root_cause, confidence, explanation = llm_result
            state.append_log(
                format_stage_log("DIAGNOSIS", "Diagnosis used LLM reasoning.")
            )
        else:
            root_cause, confidence, explanation = self._determine_root_cause(
                error_type=state.error_type,
                anomaly_type=anomaly_type,
                execution_logs=state.execution_logs,
                schema=dict(state.diagnosis.get("schema", {})),
            )
            state.append_log(
                format_stage_log(
                    "DIAGNOSIS",
                    "Diagnosis fell back to rule-based analysis.",
                )
            )
        known_strategy = FailureMemory.retrieve_strategy(root_cause)
        if known_strategy:
            state.append_log(
                format_stage_log(
                    "MEMORY",
                    f"Memory recall: similar failure previously fixed using '{known_strategy}'.",
                )
            )

        diagnosis = dict(state.diagnosis)
        diagnosis.update(
            {
                "anomaly_type": anomaly_type,
                "root_cause": root_cause,
                "confidence": self._apply_confidence_floor(confidence),
                "explanation": explanation,
            }
        )

        confidence = self._apply_confidence_floor(confidence)

        state.record_diagnosis(diagnosis)
        state.update_status("diagnosed")
        state.append_log(
            format_stage_log(
                "DIAGNOSIS",
                f"Diagnosis identified root cause '{root_cause}' with confidence {confidence:.2f}.",
            )
        )
        state.append_log(format_stage_log("DIAGNOSIS", explanation))

        return state

    def _determine_root_cause(
        self,
        error_type: str,
        anomaly_type: str,
        execution_logs: list[str],
        schema: dict[str, Any],
    ) -> tuple[str, float, str]:
        """Determine the most likely root cause from error signals."""

        error_text = error_type.lower()
        anomaly_text = anomaly_type.lower()
        log_text = self._latest_failure_context(execution_logs).lower()
        combined_text = f"{error_text} {anomaly_text} {log_text}".strip()
        tables = schema.get("tables", [])
        columns = schema.get("columns", {})

        if "column" in combined_text and (
            "not found" in combined_text
            or "does not exist" in combined_text
            or "unknown" in combined_text
            or "invalid" in combined_text
            or "binder" in combined_text
        ):
            if isinstance(tables, list) and isinstance(columns, dict):
                for table_name, table_columns in columns.items():
                    if not isinstance(table_columns, list):
                        continue

                    available_columns = [
                        str(column.get("name"))
                        for column in table_columns
                        if isinstance(column, dict) and "name" in column
                    ]
                    if available_columns:
                        return (
                            "invalid_column",
                            0.80,
                            "Schema discovery suggests available columns in "
                            f"'{table_name}': {', '.join(available_columns)}.",
                        )

            return (
                "invalid_column",
                0.85,
                "Diagnosis found column reference errors, indicating an invalid or missing column in the SQL pipeline.",
            )

        if anomaly_text == "missing_table" or (
            "table" in combined_text
            and (
                "not found" in combined_text
                or "does not exist" in combined_text
                or "catalog" in combined_text
            )
        ):
            return (
                "missing_table",
                0.90,
                "Diagnosis found references to a table that is missing from the DuckDB environment.",
            )

        if anomaly_text == "syntax_error" or (
            "syntax" in combined_text or "parser" in combined_text
        ):
            return (
                "syntax_error",
                0.88,
                "Diagnosis found evidence of malformed SQL or parser failures in the execution logs.",
            )

        return (
            "runtime_failure",
            0.70,
            "Diagnosis could not match structured SQL issues and classified the failure as a general runtime failure.",
        )

    def _llm_root_cause(
        self,
        state: PipelineState,
        error_type: str,
        execution_logs: list[str],
        schema: dict[str, Any],
    ) -> tuple[str, float, str] | None:
        """Use the Groq client to infer a root cause from execution evidence."""

        state.append_log(
            format_stage_log("DIAGNOSIS", "Diagnosis attempting LLM reasoning.")
        )
        latest_failure_log = self._latest_failure_context(execution_logs)
        prompt = (
            "You are diagnosing a failed data pipeline.\n"
            "Return JSON with keys: root_cause, confidence, explanation.\n"
            "Allowed root_cause values: missing_table, syntax_error, "
            "invalid_column, runtime_failure.\n"
            f"error_type: {error_type}\n"
            f"latest_failure_log: {latest_failure_log}\n"
            f"schema: {schema}\n"
        )

        llm_started_at = time.perf_counter()
        result = generate_json(prompt)
        elapsed = time.perf_counter() - llm_started_at
        if not result.get("success"):
            if result.get("error") == LLM_BUDGET_MESSAGE:
                state.append_log(
                    format_stage_log("DIAGNOSIS", LLM_BUDGET_MESSAGE)
                )
            return None

        state.append_log(
            format_stage_log(
                "DIAGNOSIS",
                f"LLM reasoning completed in {elapsed:.2f}s.",
            )
        )

        root_cause = result.get("root_cause")
        confidence = result.get("confidence")
        explanation = result.get("explanation")
        allowed_root_causes = {
            "missing_table",
            "syntax_error",
            "invalid_column",
            "runtime_failure",
        }

        if not isinstance(root_cause, str) or root_cause not in allowed_root_causes:
            return None

        if isinstance(confidence, int):
            confidence = float(confidence)

        if not isinstance(confidence, float):
            return None

        if not isinstance(explanation, str) or not explanation.strip():
            return None

        bounded_confidence = min(max(confidence, self.MIN_CONFIDENCE), 1.0)
        return root_cause, bounded_confidence, explanation.strip()

    def _latest_failure_context(self, execution_logs: list[str]) -> str:
        """Return the most recent execution failure log for diagnosis."""

        for log in reversed(execution_logs):
            if "pipeline execution failed" in log.lower():
                return log

        if execution_logs:
            return execution_logs[-1]

        return ""

    def _apply_confidence_floor(self, confidence: float) -> float:
        """Ensure confidence never drops to zero."""

        return min(max(confidence, self.MIN_CONFIDENCE), 1.0)
