"""Pipeline report generator for summarizing ADEA execution results."""

from __future__ import annotations

from typing import Any

from adea.utils.lineage import extract_lineage, format_lineage_graph
from adea.utils.timeline import generate_pipeline_timeline, format_pipeline_timeline


def generate_pipeline_report(state: Any) -> str:
    """Build a readable pipeline report from the final PipelineState."""

    lines: list[str] = []

    lines.append("ADEA PIPELINE REPORT")
    lines.append("==============================")
    lines.append("")
    lines.append(f"Pipeline ID: {state.pipeline_id}")
    lines.append(f"Status: {state.pipeline_status.upper()}")
    lines.append("")

    timeline = generate_pipeline_timeline(state.execution_logs)
    lines.append(format_pipeline_timeline(timeline))
    lines.append("")

    steps = state.pipeline_plan.get("steps", [])
    normalized_steps = steps if isinstance(steps, list) else []
    edges = extract_lineage(normalized_steps)
    lines.append(format_lineage_graph(edges))
    lines.append("")

    if state.repair_action:
        lines.append("REPAIR ACTION")
        lines.append("------------------------")
        for key, value in state.repair_action.items():
            lines.append(f"{key}: {value}")
        lines.append("")

    if state.optimization:
        lines.append("OPTIMIZATION SUGGESTIONS")
        lines.append("------------------------")
        recommendations = state.optimization.get("recommendations", [])
        if isinstance(recommendations, list):
            for suggestion in recommendations:
                lines.append(f"- {suggestion}")
        lines.append("")

    return "\n".join(lines)
