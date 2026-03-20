"""Utilities for deriving pipeline lifecycle timelines from execution logs."""

from __future__ import annotations


def generate_pipeline_timeline(logs: list[str]) -> list[dict[str, str]]:
    """Parse execution logs into ordered pipeline lifecycle stages."""

    timeline: list[dict[str, str]] = []
    has_retry_routing = any(
        "Workflow routing repaired pipeline back to executor" in log for log in logs
    )
    retry_executor_recorded = False

    for index, log in enumerate(logs):
        normalized_log = log.lower()

        if "Generating pipeline" in log:
            timeline.append({"stage": "Generator", "status": "success"})
            continue

        if "Pipeline execution started" in log:
            stage_name = "Executor"
            if retry_executor_recorded or (
                has_retry_routing and index > 0 and any(
                    "Workflow routing repaired pipeline back to executor" in previous_log
                    for previous_log in logs[:index]
                )
            ):
                stage_name = "RetryExecutor"

            timeline.append({"stage": stage_name, "status": "start"})
            continue

        if "Pipeline execution failed" in log:
            stage_name = "Executor"
            if any(
                "RetryExecutor" == item["stage"] and item["status"] == "start"
                for item in timeline
            ):
                stage_name = "RetryExecutor"

            timeline.append({"stage": stage_name, "status": "failure"})
            continue

        if "Monitoring classified anomaly" in log:
            timeline.append({"stage": "Monitoring", "status": "success"})
            continue

        if "Schema discovery scanning" in log:
            timeline.append({"stage": "SchemaDiscovery", "status": "success"})
            continue

        if "Diagnosis identified root cause" in log:
            timeline.append({"stage": "Diagnosis", "status": "success"})
            continue

        if any(
            marker in normalized_log
            for marker in (
                "repair prepended",
                "repair agent used llm-generated repair",
                "repair reused a previously successful sql fix from memory",
                "repair rewrote the failing query",
            )
        ):
            timeline.append({"stage": "Repair", "status": "success"})
            continue

        if "Workflow routing repaired pipeline back to executor" in log:
            timeline.append({"stage": "RetryExecutor", "status": "success"})
            retry_executor_recorded = True
            continue

        if "Optimization generated" in log:
            timeline.append({"stage": "Optimization", "status": "success"})

    return timeline


def format_pipeline_timeline(timeline: list[dict[str, str]]) -> str:
    """Convert timeline data into a readable pipeline lifecycle diagram."""

    lines = []
    lines.append("PIPELINE EXECUTION TIMELINE")
    lines.append("----------------------------")

    for item in timeline:
        stage = item["stage"]
        status = item["status"]

        if status == "success":
            symbol = "[OK]"
        elif status == "failure":
            symbol = "[FAIL]"
        else:
            symbol = "[...]"

        lines.append(f"{stage:<15} {symbol}")

    return "\n".join(lines)
