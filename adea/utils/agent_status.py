"""Utilities for exposing live agent execution status."""

from __future__ import annotations

from typing import Any


AGENT_SEQUENCE = [
    "Planner",
    "Executor",
    "Monitor",
    "SchemaDiscovery",
    "Diagnosis",
    "Repair",
    "Optimization",
]

_AGENT_TAGS = {
    "Planner": "[PLANNER]",
    "Executor": "[EXECUTOR]",
    "Monitor": "[MONITOR]",
    "SchemaDiscovery": "[SCHEMA]",
    "Diagnosis": "[DIAGNOSIS]",
    "Repair": "[REPAIR]",
    "Optimization": "[OPTIMIZATION]",
}

_COMPLETION_HINTS = {
    "Planner": ("generated pipeline plan",),
    "Executor": ("pipeline execution completed successfully",),
    "Monitor": ("no anomalies detected", "monitoring classified anomaly"),
    "SchemaDiscovery": ("schema discovery found", "detected tables:", "no tables discovered"),
    "Diagnosis": ("diagnosis identified root cause",),
    "Repair": (
        "repair agent used llm-generated repair",
        "repair prepended",
        "repair rewrote the failing query",
        "repair reused a previously successful sql fix from memory",
        "repair logged an invalid column issue",
        "repair could not apply an automatic fix",
        "repair marked the pipeline as unrecoverable",
    ),
    "Optimization": ("optimization generated", "optimization found no immediate"),
}

_RUNNING_HINTS = {
    "Planner": ("generating pipeline",),
    "Executor": ("pipeline execution started",),
    "Monitor": ("monitoring",),
    "SchemaDiscovery": ("schema discovery scanning",),
    "Diagnosis": ("diagnosis started root-cause analysis", "diagnosis analyzing anomaly"),
    "Repair": ("repair started remediation planning",),
    "Optimization": ("optimization agent analyzing pipeline plan",),
}

_FAILURE_HINTS = {
    "Executor": ("pipeline execution failed",),
    "Diagnosis": ("diagnosis llm failed", "output rejected"),
    "Repair": ("mark_unrecoverable",),
}

_PROGRESS_MARKERS = {
    "Planner": 0,
    "Executor": 20,
    "Monitor": 40,
    "SchemaDiscovery": 50,
    "Diagnosis": 60,
    "Repair": 80,
    "Optimization": 100,
}


def build_agent_execution_status(state: Any) -> dict[str, Any]:
    """Return a live agent execution status payload for one pipeline state."""

    logs = getattr(state, "execution_logs", []) or []
    normalized_logs = [str(log).lower() for log in logs]
    agents: list[dict[str, Any]] = []
    for agent in AGENT_SEQUENCE:
        status = _derive_agent_status(agent, normalized_logs)
        agents.append(
            {
                "name": agent,
                "status": status,
                "execution_time": _extract_execution_time(agent, logs),
            }
        )

    pipeline_status = str(getattr(state, "pipeline_status", ""))
    _normalize_agent_states(agents, pipeline_status)
    progress = _derive_progress(agents, pipeline_status)

    return {
        "pipeline_id": getattr(state, "pipeline_id", ""),
        "status": pipeline_status,
        "progress": progress,
        "agents": agents,
    }


def _derive_agent_status(agent: str, normalized_logs: list[str]) -> str:
    """Derive the current status for one agent from execution logs."""

    tag = _AGENT_TAGS[agent].lower()
    status = "waiting"

    for log in normalized_logs:
        if tag not in log:
            continue

        if any(marker in log for marker in _FAILURE_HINTS.get(agent, ())):
            status = "failed"
            continue

        if any(marker in log for marker in _COMPLETION_HINTS[agent]):
            status = "completed"
            continue

        if any(marker in log for marker in _RUNNING_HINTS[agent]):
            status = "running"
            continue

        status = "completed"

    return status


def _derive_progress(agents: list[dict[str, Any]], pipeline_status: str) -> int:
    """Return a stable progress percentage for the live timeline."""

    if pipeline_status == "success":
        return 100

    progress = 0
    for agent in agents:
        agent_name = str(agent.get("name", ""))
        agent_status = str(agent.get("status", "waiting"))

        if agent_status in {"running", "completed", "failed"}:
            progress = max(progress, _PROGRESS_MARKERS.get(agent_name, progress))

    return progress


def _normalize_agent_states(
    agents: list[dict[str, Any]],
    pipeline_status: str,
) -> None:
    """Promote stale running agents to completed once later stages advance."""

    seen_advanced_stage = False

    for agent in reversed(agents):
        status = str(agent.get("status", "waiting"))

        if status in {"running", "completed", "failed"}:
            if status == "running" and seen_advanced_stage:
                agent["status"] = "completed"
            else:
                seen_advanced_stage = True

    if pipeline_status == "success":
        for agent in agents:
            if agent.get("status") == "running":
                agent["status"] = "completed"


def _extract_execution_time(agent: str, logs: list[str]) -> str | None:
    """Return the latest reported execution time for an agent when available."""

    tag = _AGENT_TAGS[agent]
    for log in reversed(logs):
        if tag not in log:
            continue

        lower = log.lower()
        if "completed in " not in lower:
            continue

        suffix = lower.split("completed in ", maxsplit=1)[1]
        duration = suffix.split("s", maxsplit=1)[0].strip()
        if duration:
            return f"{duration}s"

    return None
