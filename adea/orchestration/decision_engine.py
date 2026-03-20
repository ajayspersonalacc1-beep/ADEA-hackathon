"""Decision engine placeholders for orchestration flow."""

from adea.orchestration.state import PipelineState


def determine_next_step(state: PipelineState) -> str:
    """Return a placeholder transition decision."""

    _ = state
    return "pending"
