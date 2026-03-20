"""SQLAlchemy models for persistence."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class Pipeline(Base):
    """Stored pipeline definition."""

    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class PipelineRun(Base):
    """Pipeline execution record."""

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    pipeline_id: Mapped[str] = mapped_column(
        ForeignKey("pipelines.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(100), nullable=False)

    runtime_seconds: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class FailureEvent(Base):
    """Failure event record."""

    __tablename__ = "failure_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    pipeline_run_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_runs.id"),
        nullable=False,
    )

    error_type: Mapped[str] = mapped_column(String(255), nullable=False)

    details: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class DiagnosisRecord(Base):
    """Diagnosis result record."""

    __tablename__ = "diagnosis_records"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    failure_event_id: Mapped[str] = mapped_column(
        ForeignKey("failure_events.id"),
        nullable=False,
    )

    diagnosis: Mapped[dict] = mapped_column(JSON, default=dict)

    confidence: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class RepairAction(Base):
    """Repair action record."""

    __tablename__ = "repair_actions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    diagnosis_record_id: Mapped[str] = mapped_column(
        ForeignKey("diagnosis_records.id"),
        nullable=False,
    )

    action_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(100), default="applied")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class OptimizationRecord(Base):
    """Optimization recommendation record."""

    __tablename__ = "optimization_records"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    pipeline_id: Mapped[str] = mapped_column(
        ForeignKey("pipelines.id"),
        nullable=False,
    )

    recommendation: Mapped[dict] = mapped_column(JSON, default=dict)

    expected_runtime_reduction: Mapped[str | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
