"""In-memory experience vector store for repair recall."""

from __future__ import annotations

import math
import re
from typing import Any

try:
    import faiss
    import numpy as np
except ImportError:
    faiss = None
    np = None


EXPERIENCE_STORE: list[dict[str, Any]] = []
EMBEDDING_DIMENSION = 256
_FAISS_INDEX: Any | None = None
_FAISS_ROW_TO_RECORD: list[int] = []


class VectorStore:
    """Store and retrieve successful repair experiences."""

    def store_experience(self, record: dict[str, Any]) -> dict[str, Any]:
        """Persist a successful pipeline repair experience."""

        stored_record = dict(record)
        stored_record["embedding_text"] = self._build_embedding_text(stored_record)
        stored_record["embedding_vector"] = self._embed_text(stored_record["embedding_text"])
        EXPERIENCE_STORE.append(stored_record)
        self._rebuild_index()
        return EXPERIENCE_STORE[-1]

    def find_similar_failure(
        self,
        error_type: str,
        root_cause: str,
        failure_query: str,
        execution_logs: list[str],
        threshold: float = 0.35,
    ) -> tuple[dict[str, Any] | None, float]:
        """Return the best matching successful repair experience."""

        query_text = self._build_embedding_text(
            {
                "error_type": error_type,
                "root_cause": root_cause,
                "failure_query": failure_query,
                "execution_logs": execution_logs,
            }
        )
        query_vector = self._embed_text(query_text)

        best_match: dict[str, Any] | None = None
        best_score = 0.0

        for record in reversed(EXPERIENCE_STORE):
            if record.get("outcome") != "success":
                continue

            repair_sql = record.get("repair_sql")
            if not isinstance(repair_sql, str) or not repair_sql.strip():
                continue

            vector = record.get("embedding_vector")
            if not isinstance(vector, list):
                continue

            score = self._cosine_similarity(query_vector, vector)
            if record.get("root_cause") == root_cause:
                score += 0.20
            if record.get("error_type") == error_type:
                score += 0.15

            score = min(score, 1.0)
            if score > best_score:
                best_score = score
                best_match = record

        if best_match is None or best_score < threshold:
            return None, best_score

        return dict(best_match), best_score

    def _latest_failure_context(self, execution_logs: list[str]) -> str:
        """Return the most recent failure log entry for similarity matching."""

        for log in reversed(execution_logs):
            if "pipeline execution failed" in log.lower():
                return log

        if execution_logs:
            return execution_logs[-1]

        return ""

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text for lightweight local embeddings."""

        return [
            token
            for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
            if len(token) > 2
        ]

    def _build_embedding_text(self, record: dict[str, Any]) -> str:
        """Build the text representation used for vector retrieval."""

        error_type = str(record.get("error_type", ""))
        root_cause = str(record.get("root_cause", ""))
        failure_query = str(record.get("failure_query", ""))
        repair_sql = str(record.get("repair_sql", ""))
        execution_logs = record.get("execution_logs", [])
        if isinstance(execution_logs, list):
            recent_logs = " ".join(str(log) for log in execution_logs[-5:])
        else:
            recent_logs = str(execution_logs)

        failure_context = str(record.get("failure_context", ""))

        return " ".join(
            part
            for part in [
                error_type,
                root_cause,
                failure_query,
                repair_sql,
                failure_context,
                recent_logs,
            ]
            if part
        )

    def _embed_text(self, text: str) -> list[float]:
        """Create a normalized local embedding vector for retrieval."""

        vector = [0.0] * EMBEDDING_DIMENSION
        for token in self._tokenize(text):
            index = hash(token) % EMBEDDING_DIMENSION
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector

        return [value / norm for value in vector]

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        """Return cosine similarity between normalized vectors."""

        if len(left) != len(right):
            return 0.0

        return sum(left_value * right_value for left_value, right_value in zip(left, right))

    def _rebuild_index(self) -> None:
        """Rebuild the FAISS index from the in-memory experience store."""

        global _FAISS_INDEX, _FAISS_ROW_TO_RECORD

        if faiss is None or np is None:
            _FAISS_INDEX = None
            _FAISS_ROW_TO_RECORD = []
            return

        vectors: list[list[float]] = []
        _FAISS_ROW_TO_RECORD = []

        for record_index, record in enumerate(EXPERIENCE_STORE):
            if record.get("outcome") != "success":
                continue
            if not isinstance(record.get("repair_sql"), str) or not record.get("repair_sql", "").strip():
                continue
            embedding_vector = record.get("embedding_vector")
            if not isinstance(embedding_vector, list):
                continue

            vectors.append(embedding_vector)
            _FAISS_ROW_TO_RECORD.append(record_index)

        if not vectors:
            _FAISS_INDEX = None
            _FAISS_ROW_TO_RECORD = []
            return

        _FAISS_INDEX = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        _FAISS_INDEX.add(np.array(vectors, dtype="float32"))
