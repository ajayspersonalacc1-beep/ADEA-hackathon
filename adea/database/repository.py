"""Repository layer placeholders for database access."""

from sqlalchemy.orm import Session

from adea.database import models


class PipelineRepository:
    """Placeholder repository for pipeline persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_pipeline(self, pipeline_id: str) -> models.Pipeline | None:
        _ = pipeline_id
        return None
