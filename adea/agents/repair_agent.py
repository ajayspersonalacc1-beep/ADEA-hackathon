"""Repair agent for deterministic pipeline plan adjustments."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from adea.agents.base_agent import BaseAgent
from adea.llm.groq_client import LLM_BUDGET_MESSAGE, generate_json, validate_sql_statement
from adea.memory.failure_memory import FailureMemory
from adea.memory.knowledge_base import KnowledgeBase
from adea.utils.helpers import format_stage_log

if TYPE_CHECKING:
    from adea.orchestration.state import PipelineState


class RepairAgent(BaseAgent):
    """Apply a repair strategy based on the diagnosed root cause."""

    def run(self, state: PipelineState) -> PipelineState:
        """Modify the pipeline plan or record a repair outcome."""

        if state.pipeline_status != "diagnosed":
            state.append_log(
                format_stage_log(
                    "REPAIR",
                    f"Repair skipped because pipeline status is '{state.pipeline_status}'.",
                )
            )
            return state

        root_cause = str(state.diagnosis.get("root_cause", "")).strip().lower()
        state.append_log(
            format_stage_log("REPAIR", "Repair started remediation planning.")
        )
        state.append_log(
            format_stage_log(
                "REPAIR",
                f"Repair agent evaluating root cause '{root_cause}'.",
            )
        )

        memory_action = self._memory_repair(state, root_cause)

        if memory_action:
            repair_action = memory_action
        else:
            llm_action = self._llm_repair(state, root_cause)

            if llm_action:
                repair_action = llm_action
                state.append_log(
                    format_stage_log("REPAIR", "Repair agent used LLM-generated repair.")
                )
            else:
                state.append_log(
                    format_stage_log(
                        "REPAIR",
                        "Repair agent falling back to deterministic repair.",
                    )
                )

                if root_cause == "missing_table":
                    repair_action = self._repair_missing_table(state)
                elif root_cause == "syntax_error":
                    repair_action = self._handle_syntax_error()
                elif root_cause == "invalid_column":
                    repair_action = self._repair_invalid_column(state)
                else:
                    repair_action = self._handle_runtime_failure()

        state.record_repair(repair_action)
        FailureMemory.store_failure(
            error_type=root_cause,
            root_cause=root_cause,
            repair_strategy=repair_action.get("strategy", "unknown"),
        )
        if repair_action["strategy"] == "mark_unrecoverable":
            state.update_status("unrecoverable")
        else:
            state.update_status("repaired")
        state.append_log(format_stage_log("REPAIR", repair_action["description"]))

        return state

    def _memory_repair(
        self,
        state: PipelineState,
        root_cause: str,
    ) -> dict[str, str] | None:
        """Reuse a successful prior repair from memory when available."""

        failure_query = self._latest_failed_query(state.execution_logs)
        experience, similarity_score = KnowledgeBase().search_similar_failure(
            error_type=state.error_type,
            root_cause=root_cause,
            failure_query=failure_query,
            execution_logs=state.execution_logs,
        )
        if experience is None:
            return None

        state.append_log(format_stage_log("MEMORY", "Memory recall: similar failure found"))
        state.append_log(format_stage_log("MEMORY", "Reusing stored repair strategy"))
        state.append_log(
            format_stage_log("MEMORY", f"Memory similarity score: {similarity_score:.2f}")
        )

        repair_sql = experience.get("repair_sql")
        strategy = experience.get("repair_strategy")
        if not isinstance(repair_sql, str) or not repair_sql.strip():
            return None
        if not isinstance(strategy, str) or not strategy.strip():
            strategy = "memory_reused_sql_fix"

        if not self._apply_sql_fix_to_pipeline(state, repair_sql.strip(), root_cause):
            return None

        return {
            "strategy": strategy,
            "description": (
                "Repair reused a previously successful SQL fix from memory."
            ),
            "sql_fix": repair_sql.strip(),
        }

    def _latest_failed_query(self, execution_logs: list[str]) -> str:
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

    def _llm_repair(
        self,
        state: PipelineState,
        root_cause: str,
    ) -> dict[str, str] | None:
        """Use LLM to generate a SQL repair strategy."""

        pipeline_plan = state.pipeline_plan
        schema = state.diagnosis.get("schema", {})
        logs = state.execution_logs[-5:]

        prompt = f"""
You are an autonomous data engineer.

A data pipeline failed.

Root cause:
{root_cause}

Pipeline SQL steps:
{pipeline_plan}

Recent logs:
{logs}

Schema metadata:
{schema}

Return JSON with:

strategy
description
sql_fix

Rules:
- sql_fix must be a valid SQL statement
- If a table is missing, create it
- If a column is invalid, rewrite the query
- Only return JSON
"""

        llm_started_at = time.perf_counter()
        result = generate_json(prompt)
        elapsed = time.perf_counter() - llm_started_at
        if not result.get("success"):
            error_message = str(result.get("error", "unknown LLM error"))
            if error_message == LLM_BUDGET_MESSAGE:
                state.append_log(format_stage_log("REPAIR", error_message))
            else:
                state.append_log(
                    format_stage_log(
                        "REPAIR",
                        f"Repair LLM failed: {error_message}.",
                    )
                )
            return None

        state.append_log(
            format_stage_log(
                "REPAIR",
                f"LLM reasoning completed in {elapsed:.2f}s.",
            )
        )

        strategy = result.get("strategy")
        description = result.get("description")
        sql_fix = result.get("sql_fix")

        if not isinstance(strategy, str) or not strategy.strip():
            state.append_log(
                format_stage_log("REPAIR", "Repair LLM output rejected: missing strategy.")
            )
            return None

        if not isinstance(description, str) or not description.strip():
            state.append_log(
                format_stage_log("REPAIR", "Repair LLM output rejected: missing description.")
            )
            return None

        if not isinstance(sql_fix, str) or not sql_fix.strip():
            state.append_log(
                format_stage_log("REPAIR", "Repair LLM output rejected: missing sql_fix.")
            )
            return None

        state.append_log(
            format_stage_log(
                "REPAIR",
                f"Repair LLM produced sql_fix: {sql_fix.strip()[:120]}",
            )
        )
        if not self._apply_sql_fix_to_pipeline(state, sql_fix.strip(), root_cause):
            state.append_log(
                format_stage_log(
                    "REPAIR",
                    "Repair LLM output rejected by SQL safety guardrails.",
                )
            )
            return None

        return {
            "strategy": strategy.strip(),
            "description": description.strip(),
            "sql_fix": sql_fix.strip(),
        }

    def _repair_missing_table(self, state: PipelineState) -> dict[str, str]:
        """Prepend a placeholder table creation step for a missing table."""

        table_name = self._extract_missing_table_name(state.execution_logs)
        repaired_plan = dict(state.pipeline_plan)
        if "steps" not in repaired_plan:
            repaired_plan["steps"] = []

        existing_steps = list(repaired_plan.get("steps", []))
        creation_step = {
            "type": "sql",
            "query": self._build_placeholder_table_query(table_name),
        }
        repaired_plan["steps"] = [creation_step, *existing_steps]
        state.pipeline_plan = repaired_plan

        return {
            "strategy": "prepend_table_creation",
            "table": table_name,
            "sql_fix": creation_step["query"],
            "description": (
                f"Repair prepended a schema-compatible table creation step for '{table_name}'."
            ),
        }

    def _handle_syntax_error(self) -> dict[str, str]:
        """Mark the pipeline as unrecoverable for deterministic syntax failures."""

        return {
            "strategy": "mark_unrecoverable",
            "description": (
                "Repair marked the pipeline as unrecoverable because SQL syntax errors "
                "require manual query correction."
            ),
        }

    def _repair_invalid_column(self, state: PipelineState) -> dict[str, str]:
        """Rewrite the failing query when schema metadata suggests a safe replacement."""

        failed_query = self._latest_failed_query(state.execution_logs)
        if not failed_query:
            return self._handle_invalid_column()

        replacement_query = self._rewrite_invalid_column_query(
            failed_query,
            dict(state.diagnosis.get("schema", {})),
        )
        if not replacement_query or replacement_query == failed_query:
            return self._handle_invalid_column()

        applied = self._replace_failed_query(state, failed_query, replacement_query)
        if not applied:
            return self._handle_invalid_column()

        return {
            "strategy": "rewrite_invalid_column_query",
            "description": "Repair rewrote the failing query using discovered schema columns.",
            "sql_fix": replacement_query,
        }

    def _handle_invalid_column(self) -> dict[str, str]:
        """Record a repair attempt without modifying the pipeline plan."""

        return {
            "strategy": "logged_repair_attempt",
            "description": (
                "Repair logged an invalid column issue but left the pipeline plan "
                "unchanged pending schema review."
            ),
        }

    def _handle_runtime_failure(self) -> dict[str, str]:
        """Record that the runtime failure requires manual intervention."""

        return {
            "strategy": "manual_intervention_required",
            "description": (
                "Repair could not apply an automatic fix and flagged the pipeline "
                "for manual intervention."
            ),
        }

    def _extract_missing_table_name(self, execution_logs: list[str]) -> str:
        """Extract the missing table name from execution logs when possible."""

        patterns = [
            r"table with name ([a-zA-Z_][a-zA-Z0-9_]*)",
            r"table ([a-zA-Z_][a-zA-Z0-9_]*) does not exist",
            r"missing table anomaly.*?([a-zA-Z_][a-zA-Z0-9_]*)",
            r"from ([a-zA-Z_][a-zA-Z0-9_]*)",
        ]

        for log in execution_logs:
            lowered_log = log.lower()
            for pattern in patterns:
                match = re.search(pattern, lowered_log)
                if match:
                    return match.group(1)

        return "missing_table_placeholder"

    def _build_placeholder_table_query(self, table_name: str) -> str:
        """Build a schema-compatible empty table creation query."""

        if table_name == "transactions":
            return (
                "CREATE TABLE IF NOT EXISTS transactions AS "
                "SELECT "
                "CAST(NULL AS DATE) AS date, "
                "CAST(NULL AS DOUBLE) AS amount, "
                "CAST(NULL AS VARCHAR) AS customer_id "
                "WHERE FALSE"
            )

        if table_name == "inventory_events":
            return (
                "CREATE TABLE IF NOT EXISTS inventory_events AS "
                "SELECT "
                "CAST(NULL AS VARCHAR) AS item_id, "
                "CAST(NULL AS INTEGER) AS quantity_change "
                "WHERE FALSE"
            )

        if table_name == "orders":
            return (
                "CREATE TABLE IF NOT EXISTS orders AS "
                "SELECT "
                "CAST(NULL AS DATE) AS order_date, "
                "CAST(NULL AS DOUBLE) AS amount, "
                "CAST(NULL AS VARCHAR) AS customer_id "
                "WHERE FALSE"
            )

        return (
            f"CREATE TABLE IF NOT EXISTS {table_name} AS "
            "SELECT 1 AS placeholder_id WHERE FALSE"
        )

    def _apply_sql_fix_to_pipeline(
        self,
        state: PipelineState,
        sql_fix: str,
        root_cause: str,
    ) -> bool:
        """Apply a validated SQL fix to the pipeline plan."""

        is_safe, _ = validate_sql_statement(sql_fix)
        if not is_safe:
            return False

        repaired_plan = dict(state.pipeline_plan)
        steps = list(repaired_plan.get("steps", []))

        normalized_root_cause = root_cause.strip().lower()
        if normalized_root_cause == "missing_table":
            steps.insert(0, {"type": "sql", "query": sql_fix})
        else:
            failed_query = self._latest_failed_query(state.execution_logs)
            if failed_query and self._replace_in_steps(steps, failed_query, sql_fix):
                pass
            else:
                steps.insert(0, {"type": "sql", "query": sql_fix})

        repaired_plan["steps"] = steps
        state.pipeline_plan = repaired_plan
        return True

    def _replace_failed_query(
        self,
        state: PipelineState,
        failed_query: str,
        replacement_query: str,
    ) -> bool:
        """Replace the failed query inside the pipeline plan."""

        repaired_plan = dict(state.pipeline_plan)
        steps = list(repaired_plan.get("steps", []))
        if not self._replace_in_steps(steps, failed_query, replacement_query):
            return False

        repaired_plan["steps"] = steps
        state.pipeline_plan = repaired_plan
        return True

    def _replace_in_steps(
        self,
        steps: list[Any],
        failed_query: str,
        replacement_query: str,
    ) -> bool:
        """Replace the first matching SQL query inside a step list."""

        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue

            query = step.get("query")
            if query != failed_query:
                continue

            updated_step = dict(step)
            updated_step["query"] = replacement_query
            steps[index] = updated_step
            return True

        return False

    def _rewrite_invalid_column_query(
        self,
        failed_query: str,
        schema: dict[str, Any],
    ) -> str | None:
        """Return a safe query rewrite for simple invalid-column failures."""

        columns = schema.get("columns", {})
        if not isinstance(columns, dict):
            return None

        available_columns = {
            str(column.get("name", "")).lower()
            for table_columns in columns.values()
            if isinstance(table_columns, list)
            for column in table_columns
            if isinstance(column, dict)
        }
        if not available_columns:
            return None

        replacements = {
            "order_total": "amount",
            "sales_amount": "amount",
            "revenue_amount": "amount",
        }

        rewritten_query = failed_query
        for invalid_name, replacement_name in replacements.items():
            if invalid_name not in rewritten_query.lower():
                continue
            if replacement_name not in available_columns:
                continue
            rewritten_query = re.sub(
                rf"\b{invalid_name}\b",
                replacement_name,
                rewritten_query,
                flags=re.IGNORECASE,
            )

        is_safe, _ = validate_sql_statement(rewritten_query)
        if not is_safe or rewritten_query == failed_query:
            return None

        return rewritten_query
