"""Optimization agent for rule-based pipeline suggestions."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from adea.agents.base_agent import BaseAgent
from adea.llm.groq_client import LLM_BUDGET_MESSAGE, generate_json
from adea.memory.knowledge_base import KnowledgeBase
from adea.utils.helpers import format_stage_log

if TYPE_CHECKING:
    from adea.orchestration.state import PipelineState


class OptimizationAgent(BaseAgent):
    """Analyze successful pipeline plans and suggest simple optimizations."""

    def run(self, state: PipelineState) -> PipelineState:
        """Generate optimization recommendations for a successful pipeline."""

        if state.pipeline_status != "success":
            state.append_log(
                format_stage_log(
                    "OPTIMIZATION",
                    f"Optimization skipped because pipeline status is '{state.pipeline_status}'.",
                )
            )
            return state

        state.append_log(
            format_stage_log("OPTIMIZATION", "Optimization agent analyzing pipeline plan.")
        )
        steps = self._extract_steps(state.pipeline_plan)
        llm_result = self._llm_recommendations(
            pipeline_plan=state.pipeline_plan,
            execution_logs=state.execution_logs,
            schema=dict(state.diagnosis.get("schema", {})),
            pipeline_status=state.pipeline_status,
        )

        if llm_result is not None:
            recommendations, llm_elapsed = llm_result
            state.append_log(
                format_stage_log(
                    "OPTIMIZATION",
                    f"LLM reasoning completed in {llm_elapsed:.2f}s.",
                )
            )
            state.append_log(
                format_stage_log("OPTIMIZATION", "Optimization used LLM reasoning.")
            )
        else:
            recommendations = self._build_recommendations(steps)
            state.append_log(
                format_stage_log(
                    "OPTIMIZATION",
                    "Optimization fell back to rule-based analysis.",
                )
            )

        state.record_optimization({"recommendations": recommendations})

        if recommendations:
            state.append_log(
                format_stage_log(
                    "OPTIMIZATION",
                    f"Optimization generated {len(recommendations)} recommendation(s).",
                )
            )
            for recommendation in recommendations:
                state.append_log(
                    format_stage_log(
                        "OPTIMIZATION",
                        f"Optimization suggestion: {recommendation}",
                    )
                )
        else:
            state.append_log(
                format_stage_log(
                    "OPTIMIZATION",
                    "Optimization found no immediate pipeline improvements.",
                )
            )

        self._store_success_experience(state)

        return state

    def _extract_steps(self, pipeline_plan: dict[str, Any]) -> list[dict[str, Any]]:
        """Return pipeline steps in a normalized list form."""

        steps = pipeline_plan.get("steps", [])
        if isinstance(steps, list):
            return [step for step in steps if isinstance(step, dict)]

        return []

    def _llm_recommendations(
        self,
        pipeline_plan: dict[str, Any],
        execution_logs: list[str],
        schema: dict[str, Any],
        pipeline_status: str,
    ) -> tuple[list[str], float] | None:
        """Request optimization recommendations from the LLM."""

        prompt = f"""
You are an autonomous data engineer optimizing a data pipeline.

Analyze the pipeline and return JSON with:

recommendations

Rules:
- recommendations must be a JSON array of strings
- focus on SQL optimization, cost reduction, query rewrite, and pipeline simplification
- only return JSON

Pipeline status:
{pipeline_status}

Pipeline plan:
{pipeline_plan}

Recent execution logs:
{execution_logs[-10:]}

Schema metadata:
{schema}
"""

        llm_started_at = time.perf_counter()
        result = generate_json(prompt)
        elapsed = time.perf_counter() - llm_started_at
        if not result.get("success"):
            if result.get("error") == LLM_BUDGET_MESSAGE:
                return None
            return None

        recommendations = result.get("recommendations")
        if not isinstance(recommendations, list):
            return None

        normalized_recommendations = [
            recommendation.strip()
            for recommendation in recommendations
            if isinstance(recommendation, str) and recommendation.strip()
        ]

        deduplicated = list(dict.fromkeys(normalized_recommendations))
        return deduplicated, elapsed

    def _store_success_experience(self, state: PipelineState) -> None:
        """Persist a successful repair experience for future reuse."""

        root_cause = state.diagnosis.get("root_cause")
        repair_strategy = state.repair_action.get("strategy")
        if not isinstance(root_cause, str) or not root_cause.strip():
            return
        if not isinstance(repair_strategy, str) or not repair_strategy.strip():
            return

        repair_sql = state.repair_action.get("sql_fix")
        if not isinstance(repair_sql, str) or not repair_sql.strip():
            steps = state.pipeline_plan.get("steps", [])
            if isinstance(steps, list) and steps:
                first_step = steps[0]
                if isinstance(first_step, dict):
                    query = first_step.get("query")
                    if isinstance(query, str) and query.strip():
                        repair_sql = query.strip()

        if not isinstance(repair_sql, str) or not repair_sql.strip():
            return

        KnowledgeBase().remember_experience(
            {
                "error_type": state.error_type,
                "failure_context": self._latest_failure_context(state.execution_logs),
                "failure_query": self._latest_failure_query(state.execution_logs),
                "execution_logs": list(state.execution_logs),
                "pipeline_plan": dict(state.pipeline_plan),
                "root_cause": root_cause,
                "repair_sql": repair_sql,
                "repair_strategy": repair_strategy,
                "outcome": "success",
            }
        )
        state.append_log(
            format_stage_log(
                "MEMORY",
                "Experience memory stored successful repair outcome.",
            )
        )

    def _build_recommendations(self, steps: list[dict[str, Any]]) -> list[str]:
        """Generate optimization suggestions from SQL pipeline steps."""

        recommendations: list[str] = []

        if len(steps) > 2:
            recommendations.append(
                "Consider consolidating pipeline steps to reduce execution overhead."
            )

        for index, step in enumerate(steps, start=1):
            query = step.get("query")
            if not isinstance(query, str):
                continue

            normalized_query = query.lower()

            if "select *" in normalized_query:
                recommendations.append(
                    f"Step {index}: replace SELECT * with explicit column selection."
                )

            if self._has_aggregation(normalized_query) and " where " not in normalized_query:
                recommendations.append(
                    f"Step {index}: add an earlier filter or WHERE clause before aggregation."
                )

        return list(dict.fromkeys(recommendations))

    def _has_aggregation(self, query: str) -> bool:
        """Return whether the SQL query contains common aggregation patterns."""

        aggregations = ("sum(", "count(", "avg(", "min(", "max(")
        return any(token in query for token in aggregations)

    def _latest_failure_context(self, execution_logs: list[str]) -> str:
        """Return the most recent failure log for experience storage."""

        for log in reversed(execution_logs):
            if "pipeline execution failed" in log.lower():
                return log

        if execution_logs:
            return execution_logs[-1]

        return ""

    def _latest_failure_query(self, execution_logs: list[str]) -> str:
        """Return the SQL query associated with the most recent failure."""

        failure_index = None
        for index in range(len(execution_logs) - 1, -1, -1):
            if "pipeline execution failed" in execution_logs[index].lower():
                failure_index = index
                break

        if failure_index is None:
            return ""

        for index in range(failure_index - 1, -1, -1):
            log = execution_logs[index]
            if "SQL Query: " in log:
                return log.split("SQL Query: ", maxsplit=1)[1].strip()

        return ""
