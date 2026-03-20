"""Simple natural language interface for controlling ADEA."""

from __future__ import annotations

from adea.orchestration.langgraph_workflow import run_workflow
from adea.orchestration.state import PipelineState
from adea.utils.lineage import extract_lineage, generate_pipeline_graph
from adea.utils.report import generate_pipeline_report


def run_cli_agent(demo: bool = False) -> None:
    """Interactive command interface for ADEA."""

    if demo:
        _run_demo()
        return

    print("\nADEA AI Data Engineer")
    print("Type a request or 'exit'\n")

    prompt_index = 0
    while True:
        user_input = input("ADEA> ")

        if user_input.lower() in {"exit", "quit"}:
            print("Exiting ADEA.")
            break

        prompt_index += 1
        final_state = _execute_pipeline(
            pipeline_id=f"cli_pipeline_{prompt_index}",
            user_prompt=user_input,
        )
        if final_state is None:
            continue

        report = generate_pipeline_report(final_state)
        graph_path = _generate_graph_output(final_state)

        print("\n")
        print(report)
        _print_graph_output(graph_path)
        print("\n")


def _run_demo() -> None:
    """Run the canned judge demo scenario."""

    print("\nADEA AI Data Engineer Demo\n")
    final_state = _execute_pipeline(
        pipeline_id="demo_pipeline",
        user_prompt="__adea_demo__ Build sales analytics pipeline",
    )

    if final_state is None:
        return

    graph_path = _generate_graph_output(final_state)
    print(generate_pipeline_report(final_state))
    _print_graph_output(graph_path)
    print("\n")


def _execute_pipeline(
    pipeline_id: str,
    user_prompt: str,
) -> PipelineState | None:
    """Execute a pipeline prompt and return the final state."""

    state = PipelineState(
        pipeline_id=pipeline_id,
        user_prompt=user_prompt,
    )

    try:
        return run_workflow(state)
    except Exception as exc:
        print("ADEA encountered an unexpected error.")
        print(exc)
        print("\n")
        return None


def _generate_graph_output(state: PipelineState) -> str | None:
    """Generate the pipeline graph artifact and return its path."""

    steps = state.pipeline_plan.get("steps", [])
    if not isinstance(steps, list):
        return None

    edges = extract_lineage(steps)
    if not edges:
        return None

    safe_pipeline_id = _sanitize_filename(state.pipeline_id)
    return generate_pipeline_graph(
        edges,
        output_path=f"output/{safe_pipeline_id}_graph.png",
    )


def _print_graph_output(graph_path: str | None) -> None:
    """Print the pipeline graph artifact path."""

    if graph_path is None:
        print("\nPipeline graph artifact:")
        print("not generated")
        return

    print("\nPipeline graph artifact:")
    print(graph_path)


def _sanitize_filename(name: str) -> str:
    """Return a filesystem-safe filename stem."""

    sanitized = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in name
    ).strip("_")
    return sanitized or "pipeline"
