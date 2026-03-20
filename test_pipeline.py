"""Simple end-to-end test for the ADEA autonomous pipeline workflow."""

from adea.orchestration.langgraph_workflow import run_workflow
from adea.orchestration.state import PipelineState
from adea.utils.lineage import extract_lineage, format_lineage_graph, generate_pipeline_graph
from adea.utils.report import generate_pipeline_report
from adea.utils.timeline import format_pipeline_timeline, generate_pipeline_timeline


def _print_milestones(logs: list[str], final_status: str) -> None:
    """Print a judge-friendly summary of major workflow milestones."""

    milestones = [
        ("PIPELINE GENERATED", "Generated pipeline plan"),
        ("PIPELINE FAILED", "Pipeline execution failed"),
        ("ANOMALY DETECTED", "Monitoring classified anomaly"),
        ("ROOT CAUSE IDENTIFIED", "Diagnosis identified root cause"),
        ("PIPELINE REPAIRED", "Repair "),
    ]

    print("Workflow Milestones:")
    for title, marker in milestones:
        if any(marker in log for log in logs):
            print(f"- {title}")

    if final_status == "success":
        print("- PIPELINE SUCCESSFUL")


def main() -> None:
    """Run a test pipeline through the full ADEA workflow."""

    state = PipelineState(
        pipeline_id="demo_pipeline",
        user_prompt="Build sales analytics pipeline",
    )

    print("\n=== ADEA AUTONOMOUS PIPELINE EXECUTION ===\n")

    final_state = run_workflow(state)

    print("=== WORKFLOW COMPLETED ===\n")

    _print_milestones(final_state.execution_logs, final_state.pipeline_status)

    print("\nPipeline Status:")
    print(final_state.pipeline_status)

    print("\nDiagnosis:")
    print(final_state.diagnosis)

    print("\nRepair Action:")
    print(final_state.repair_action)

    print("\nExecution Logs:")
    for log in final_state.execution_logs:
        print("-", log)

    timeline = generate_pipeline_timeline(final_state.execution_logs)

    print("\n=== PIPELINE TIMELINE ===\n")
    print(format_pipeline_timeline(timeline))

    steps = final_state.pipeline_plan.get("steps", [])
    edges = extract_lineage(steps if isinstance(steps, list) else [])

    print("\n=== PIPELINE LINEAGE ===\n")
    print(format_lineage_graph(edges))

    graph_path: str | None = None
    if edges:
        try:
            graph_path = generate_pipeline_graph(edges)
            print("\nPipeline graph saved to:")
            print(graph_path)
        except Exception as exc:
            print("\nPipeline graph generation skipped:")
            print(exc)

    print("\n=== ADEA PIPELINE REPORT ===\n")
    print(generate_pipeline_report(final_state))


if __name__ == "__main__":
    main()
