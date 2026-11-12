"""Zero-Cost Warehouse Connector interface and local DuckDB implementation (T-201)."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import duckdb


class BaseConnector(ABC):
    """Abstract interface for read-only database exploration and query execution."""

    @abstractmethod
    def list_tables(self) -> List[str]:
        """List all accessible tables/views."""
        pass

    @abstractmethod
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Return columns with their types, nullable status, etc."""
        pass

    @abstractmethod
    def execute_query(self, query: str, limit: Optional[int] = None) -> Tuple[List[str], List[Tuple[Any, ...]]]:
        """Execute a read-only query and return (columns, rows)."""
        pass


class DuckDBConnector(BaseConnector):
    """Local, embedded, 100% free DuckDB connector (supports BigQuery SQL simulation)."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"DuckDB database not found at {self.db_path}")

    def _get_connection(self):
        # Open in read-only mode to adhere to Principle 8: Least privilege
        return duckdb.connect(str(self.db_path), read_only=True)

    def list_tables(self) -> List[str]:
        with self._get_connection() as con:
            tables = con.execute("SHOW TABLES;").fetchall()
            return [t[0] for t in tables]

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        with self._get_connection() as con:
            info = con.execute(f"DESCRIBE {table_name};").fetchall()
            # Columns in DuckDB describe: column_name, column_type, null, key, default, extra
            schema = []
            for col in info:
                schema.append({
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                })
            return schema

    def execute_query(self, query: str, limit: Optional[int] = None) -> Tuple[List[str], List[Tuple[Any, ...]]]:
        clean_q = query.strip().rstrip(";")
        if limit:
            clean_q = f"SELECT * FROM ({clean_q}) LIMIT {limit}"

        with self._get_connection() as con:
            res = con.execute(clean_q)
            columns = [desc[0] for desc in res.description]
            rows = res.fetchall()
            return columns, rows
