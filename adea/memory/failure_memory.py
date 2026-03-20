"""In-memory failure pattern storage for repair lookups."""

from __future__ import annotations


FAILURE_MEMORY: list[dict] = []


class FailureMemory:
    """Store and retrieve historical failure repair patterns in memory."""

    @staticmethod
    def store_failure(
        error_type: str,
        root_cause: str,
        repair_strategy: str,
    ) -> dict:
        """Persist a failure pattern in memory and return the stored record."""

        record = {
            "error_type": error_type,
            "root_cause": root_cause,
            "repair_strategy": repair_strategy,
        }
        FAILURE_MEMORY.append(record)
        return record

    @staticmethod
    def retrieve_strategy(error_type: str) -> str | None:
        """Return the most recent repair strategy for the given error type."""

        for record in reversed(FAILURE_MEMORY):
            if record.get("error_type") == error_type:
                strategy = record.get("repair_strategy")
                if isinstance(strategy, str):
                    return strategy

        return None
