"""Schema discovery agent for collecting DuckDB metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import duckdb

from adea.agents.base_agent import BaseAgent
from adea.utils.helpers import format_stage_log

if TYPE_CHECKING:
    from adea.orchestration.state import PipelineState


class SchemaDiscoveryAgent(BaseAgent):
    """Inspect DuckDB schema metadata and store it in diagnosis state."""

    def __init__(self, database_path: str = ":memory:") -> None:
        self.database_path = database_path

    def run(self, state: PipelineState) -> PipelineState:
        """Discover tables and columns for failed or anomalous pipeline runs."""

        if state.pipeline_status not in {"failed", "anomaly_detected"}:
            state.append_log(
                format_stage_log(
                    "SCHEMA",
                    "Schema discovery skipped because pipeline status is "
                    f"'{state.pipeline_status}'.",
                )
            )
            return state

        state.append_log(
            format_stage_log("SCHEMA", "Schema discovery scanning database metadata...")
        )
        schema_payload = {
            "tables": [],
            "columns": {},
        }

        connection = duckdb.connect(database=self.database_path)
        try:
            tables = self._fetch_tables(connection)
            schema_payload["tables"] = tables
            state.append_log(
                format_stage_log(
                    "SCHEMA",
                    f"Schema discovery found {len(tables)} table(s).",
                )
            )

            if tables:
                state.append_log(
                    format_stage_log(
                        "SCHEMA",
                        f"Detected tables: {', '.join(tables)}",
                    )
                )
            else:
                state.append_log(
                    format_stage_log("SCHEMA", "No tables discovered in the database.")
                )
                state.append_log(format_stage_log("SCHEMA", "Detected tables: none"))

            for table_name in tables:
                columns = self._fetch_columns(connection, table_name)
                schema_payload["columns"][table_name] = columns

                if columns:
                    column_names = ", ".join(column["name"] for column in columns)
                    state.append_log(
                        format_stage_log(
                            "SCHEMA",
                            f"Detected columns for {table_name}: {column_names}",
                        )
                    )
                else:
                    state.append_log(
                        format_stage_log(
                            "SCHEMA",
                            f"Detected columns for {table_name}: none",
                        )
                    )
        finally:
            connection.close()

        diagnosis = dict(state.diagnosis)
        diagnosis["schema"] = schema_payload
        state.record_diagnosis(diagnosis)
        return state

    def _fetch_tables(self, connection: duckdb.DuckDBPyConnection) -> list[str]:
        """Return table names from the DuckDB main schema."""

        rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchall()
        return [str(row[0]) for row in rows]

    def _fetch_columns(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str,
    ) -> list[dict[str, Any]]:
        """Return column metadata for the given table."""

        rows = connection.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = ?
            ORDER BY ordinal_position
            """,
            [table_name],
        ).fetchall()
        return [
            {
                "name": str(column_name),
                "type": str(data_type),
            }
            for column_name, data_type in rows
        ]
