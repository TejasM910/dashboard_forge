"""Data Profiler tool: Computes schema statistics, cardinality, null %, min/max, and freshness (T-202)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from dforge.tools.connectors.duckdb_connector import BaseConnector


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    total_count: int
    null_count: int
    null_percentage: float
    distinct_count: int
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    is_candidate_pk: bool = False


class TableProfile(BaseModel):
    table_name: str
    row_count: int
    columns: List[ColumnProfile] = Field(default_factory=list)


class DataProfiler:
    """Profiles warehouse tables to provide ground truth statistical summaries."""

    def __init__(self, connector: BaseConnector):
        self.connector = connector

    def profile_table(self, table_name: str) -> TableProfile:
        schema = self.connector.get_table_schema(table_name)
        _, count_rows = self.connector.execute_query(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = count_rows[0][0] if count_rows else 0

        columns_profile: List[ColumnProfile] = []
        for col in schema:
            c_name = col["name"]
            c_type = col["type"]

            if total_rows == 0:
                columns_profile.append(
                    ColumnProfile(
                        name=c_name,
                        data_type=c_type,
                        total_count=0,
                        null_count=0,
                        null_percentage=0.0,
                        distinct_count=0,
                    )
                )
                continue

            stats_sql = f"""
                SELECT 
                    COUNT(*) - COUNT({c_name}) AS null_cnt,
                    COUNT(DISTINCT {c_name}) AS distinct_cnt,
                    MIN(CAST({c_name} AS VARCHAR)) AS min_val,
                    MAX(CAST({c_name} AS VARCHAR)) AS max_val
                FROM {table_name}
            """
            _, stats_res = self.connector.execute_query(stats_sql)
            null_cnt, dist_cnt, min_v, max_v = stats_res[0]

            null_pct = round((null_cnt / total_rows) * 100, 2)
            is_pk = (null_cnt == 0 and dist_cnt == total_rows and total_rows > 0)

            columns_profile.append(
                ColumnProfile(
                    name=c_name,
                    data_type=c_type,
                    total_count=total_rows,
                    null_count=null_cnt,
                    null_percentage=null_pct,
                    distinct_count=dist_cnt,
                    min_value=str(min_v) if min_v is not None else None,
                    max_value=str(max_v) if max_v is not None else None,
                    is_candidate_pk=is_pk,
                )
            )

        return TableProfile(table_name=table_name, row_count=total_rows, columns=columns_profile)

    def profile_all(self) -> List[TableProfile]:
        tables = self.connector.list_tables()
        return [self.profile_table(t) for t in tables]
