"""Shared state schema for agent orchestration."""

from typing import Any, Self

from pydantic import BaseModel, Field


class PipelineState(BaseModel):
    """Global state shared across the orchestration workflow."""

    pipeline_id: str
    user_prompt: str

    pipeline_plan: dict[str, Any] = Field(default_factory=dict)

    execution_logs: list[str] = Field(default_factory=list)

    pipeline_status: str = "pending"
    error_type: str = ""

    diagnosis: dict[str, Any] = Field(default_factory=dict)
    repair_action: dict[str, Any] = Field(default_factory=dict)
    optimization: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0

    started_at: float | None = None
    finished_at: float | None = None

    def update_status(self, new_status: str) -> Self:
        """Update the current pipeline status."""
        self.pipeline_status = new_status
        return self

    def append_log(self, message: str) -> Self:
        """Append a log message to the execution log list."""
        self.execution_logs.append(message)
        return self

    def record_failure(self, error_type: str) -> Self:
        """Record a failure type on the shared state."""
        self.error_type = error_type
        return self

    def record_diagnosis(self, diagnosis: dict) -> Self:
        """Store diagnosis details on the shared state."""
        self.diagnosis = dict(diagnosis)
        return self

    def record_repair(self, action: dict) -> Self:
        """Store repair action details on the shared state."""
        self.repair_action = dict(action)
        return self

    def record_optimization(self, result: dict) -> Self:
        """Store optimization details on the shared state."""
        self.optimization = dict(result)
        return self

    def to_dict(self) -> dict:
        """Convert state to plain dictionary."""
        return self.model_dump()

    class Config:
        arbitrary_types_allowed = True
