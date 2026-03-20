"""Knowledge base helpers for repair experience storage and retrieval."""

from __future__ import annotations

from typing import Any

from adea.memory.vector_store import VectorStore


class KnowledgeBase:
    """Coordinate storing and searching repair experiences."""

    def __init__(self) -> None:
        self.vector_store = VectorStore()

    def remember_experience(self, record: dict[str, Any]) -> dict[str, Any]:
        """Persist a repair experience in the vector store."""

        return self.vector_store.store_experience(record)

    def search_similar_failure(
        self,
        error_type: str,
        root_cause: str,
        failure_query: str,
        execution_logs: list[str],
        threshold: float = 0.35,
    ) -> tuple[dict[str, Any] | None, float]:
        """Return the best matching experience and its similarity score."""

        return self.vector_store.find_similar_failure(
            error_type=error_type,
            root_cause=root_cause,
            failure_query=failure_query,
            execution_logs=execution_logs,
            threshold=threshold,
        )
