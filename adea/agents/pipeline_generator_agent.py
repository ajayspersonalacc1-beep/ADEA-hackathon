"""Rule-based pipeline generation agent."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from adea.agents.base_agent import BaseAgent
from adea.llm.groq_client import LLM_BUDGET_MESSAGE, generate_json, validate_sql_statement
from adea.utils.helpers import format_stage_log

if TYPE_CHECKING:
    from adea.orchestration.state import PipelineState


class PipelineGeneratorAgent(BaseAgent):
    """Generate a simple pipeline plan from the user prompt."""

    def run(self, state: PipelineState) -> PipelineState:
        """Build a deterministic SQL pipeline plan and store it on the state."""

        prompt = state.user_prompt.strip()
        if not prompt:
            state.record_failure("empty_prompt")
            state.update_status("failed")
            state.append_log(format_stage_log("PLANNER", "User prompt was empty."))
            return state

        pipeline_type = self._detect_pipeline_type(prompt)
        state.append_log(
            format_stage_log("PLANNER", f"Generating pipeline for prompt: {prompt}")
        )
        state.append_log(
            format_stage_log("PLANNER", f"Detected pipeline type: {pipeline_type}")
        )

        llm_plan = self._llm_pipeline_plan(prompt)
        if llm_plan is not None:
            llm_log = llm_plan.pop("_llm_log", None)
            if isinstance(llm_log, str) and llm_log:
                state.append_log(llm_log)
            pipeline_plan = self._sanitize_pipeline_plan(llm_plan)
            state.append_log(
                format_stage_log("PLANNER", "Pipeline planner using LLM reasoning")
            )
        else:
            pipeline_plan = self._sanitize_pipeline_plan(
                self._build_pipeline_plan(pipeline_type)
            )
            state.append_log(
                format_stage_log(
                    "PLANNER",
                    "Pipeline planner fallback to rule-based generator",
                )
            )

        step_count = len(pipeline_plan.get("steps", []))

        state.pipeline_plan = pipeline_plan
        state.update_status("pipeline_generated")
        state.append_log(
            format_stage_log(
                "PLANNER",
                f"Generated pipeline plan with {step_count} SQL step(s).",
            )
        )

        return state

    def _detect_pipeline_type(self, user_prompt: str) -> str:
        """Detect the pipeline type from prompt keywords."""

        prompt = user_prompt.lower()

        if "__adea_demo__" in prompt:
            return "demo"

        if "sales" in prompt:
            return "sales"

        if "customer" in prompt:
            return "customer"

        if "inventory" in prompt:
            return "inventory"

        return "default"

    def _llm_pipeline_plan(self, user_prompt: str) -> dict[str, Any] | None:
        """Use the LLM to generate a structured SQL pipeline plan."""

        prompt = f"""
You are an expert data engineer.

User request:
{user_prompt}

Generate a SQL analytics pipeline from the user's request.

Return JSON in this structure:
{{
  "name": "pipeline_name",
  "steps": [
    {{"type": "sql", "query": "..."}},
    {{"type": "sql", "query": "..."}}
  ]
}}

Rules:
- steps must be a JSON array
- each step must have type="sql"
- each query must be executable SQL
- only return JSON
"""

        llm_started_at = time.perf_counter()
        result = generate_json(prompt)
        elapsed = time.perf_counter() - llm_started_at
        if not result.get("success"):
            if result.get("error") == LLM_BUDGET_MESSAGE:
                return None
            return None

        step_log = format_stage_log(
            "PLANNER",
            f"LLM reasoning completed in {elapsed:.2f}s.",
        )

        steps = result.get("steps")
        if not isinstance(steps, list) or not steps:
            return None

        normalized_steps: list[dict[str, str]] = []
        for step in steps:
            if not isinstance(step, dict):
                return None

            step_type = step.get("type")
            query = step.get("query")
            if step_type != "sql":
                return None
            if not isinstance(query, str) or not query.strip():
                return None
            is_safe, _ = validate_sql_statement(query)
            if not is_safe:
                return None

            normalized_steps.append(
                {
                    "type": "sql",
                    "query": query.strip(),
                }
            )

        name = result.get("name")
        if not isinstance(name, str) or not name.strip():
            name = "llm_generated_pipeline"

        return {
            "name": name.strip(),
            "steps": normalized_steps,
            "_llm_log": step_log,
        }

    def _build_pipeline_plan(self, pipeline_type: str) -> dict[str, Any]:
        """Return a deterministic SQL pipeline plan for the detected type."""

        if pipeline_type == "demo":
            return self._demo_pipeline_plan()

        if pipeline_type == "sales":
            return self._sales_pipeline_plan()

        if pipeline_type == "customer":
            return self._customer_pipeline_plan()

        if pipeline_type == "inventory":
            return self._inventory_pipeline_plan()

        return self._default_pipeline_plan()

    def _sanitize_pipeline_plan(self, pipeline_plan: dict[str, Any]) -> dict[str, Any]:
        """Normalize planner SQL so plain CREATE TABLE becomes IF NOT EXISTS."""

        sanitized_plan = dict(pipeline_plan)
        steps = sanitized_plan.get("steps", [])
        if not isinstance(steps, list):
            return sanitized_plan

        sanitized_steps: list[dict[str, Any]] = []
        for step in steps:
            if not isinstance(step, dict):
                sanitized_steps.append(step)
                continue

            updated_step = dict(step)
            query = updated_step.get("query")
            if isinstance(query, str):
                updated_step["query"] = self._sanitize_sql_query(query)
            sanitized_steps.append(updated_step)

        sanitized_plan["steps"] = sanitized_steps
        return sanitized_plan

    def _sanitize_sql_query(self, query: str) -> str:
        """Ensure plain CREATE TABLE statements use IF NOT EXISTS."""

        return re.sub(
            r"^\s*create\s+table\s+(?!if\s+not\s+exists\b)",
            "CREATE TABLE IF NOT EXISTS ",
            query,
            count=1,
            flags=re.IGNORECASE,
        )

    def _demo_pipeline_plan(self) -> dict[str, list[dict[str, str]] | str]:
        """Build a deterministic demo pipeline that triggers repair and retry."""

        return {
            "name": "demo_pipeline",
            "steps": [
                {
                    "type": "sql",
                    "query": (
                        "CREATE OR REPLACE TABLE sales_data AS "
                        "SELECT order_date AS date, amount, customer_id FROM orders"
                    ),
                },
                {
                    "type": "sql",
                    "query": (
                        "CREATE OR REPLACE TABLE daily_revenue AS "
                        "SELECT date, SUM(order_total) AS total_revenue "
                        "FROM sales_data GROUP BY date"
                    ),
                },
                {
                    "type": "sql",
                    "query": (
                        "CREATE OR REPLACE TABLE monthly_revenue AS "
                        "SELECT date_trunc('month', date) AS revenue_month, "
                        "SUM(total_revenue) AS monthly_revenue "
                        "FROM daily_revenue GROUP BY revenue_month"
                    ),
                },
                {
                    "type": "sql",
                    "query": "SELECT * FROM monthly_revenue",
                },
            ],
        }

    def _sales_pipeline_plan(self) -> dict[str, list[dict[str, str]] | str]:
        """Build a sales analytics oriented pipeline plan."""

        return {
            "name": "sales_pipeline",
            "steps": [
                {
                    "type": "sql",
                    "query": "CREATE TABLE sales AS SELECT * FROM transactions",
                },
                {
                    "type": "sql",
                    "query": (
                        "SELECT date, SUM(amount) AS total_amount "
                        "FROM sales GROUP BY date"
                    ),
                },
            ]
        }

    def _customer_pipeline_plan(self) -> dict[str, list[dict[str, str]] | str]:
        """Build a customer analytics oriented pipeline plan."""

        return {
            "name": "customer_pipeline",
            "steps": [
                {
                    "type": "sql",
                    "query": (
                        "CREATE TABLE customer_activity AS "
                        "SELECT * FROM transactions"
                    ),
                },
                {
                    "type": "sql",
                    "query": (
                        "SELECT customer_id, COUNT(*) AS transaction_count "
                        "FROM customer_activity GROUP BY customer_id"
                    ),
                },
            ]
        }

    def _inventory_pipeline_plan(self) -> dict[str, list[dict[str, str]] | str]:
        """Build an inventory analytics oriented pipeline plan."""

        return {
            "name": "inventory_pipeline",
            "steps": [
                {
                    "type": "sql",
                    "query": (
                        "CREATE TABLE inventory_snapshot AS "
                        "SELECT * FROM inventory_events"
                    ),
                },
                {
                    "type": "sql",
                    "query": (
                        "SELECT item_id, SUM(quantity_change) AS net_quantity "
                        "FROM inventory_snapshot GROUP BY item_id"
                    ),
                },
            ]
        }

    def _default_pipeline_plan(self) -> dict[str, list[dict[str, str]] | str]:
        """Build a generic analytics pipeline plan."""

        return {
            "name": "default_pipeline",
            "steps": [
                {
                    "type": "sql",
                    "query": "CREATE TABLE prepared_data AS SELECT * FROM source_data",
                },
                {
                    "type": "sql",
                    "query": "SELECT * FROM prepared_data",
                },
            ]
        }
