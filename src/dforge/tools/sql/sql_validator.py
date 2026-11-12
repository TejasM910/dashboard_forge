"""SQL Static Checks, AST Safety Linter, and Dry-Run Validator via SQLGlot (T-305 & FR-43)."""

from typing import List, Optional
from pydantic import BaseModel, Field
import sqlglot
from sqlglot import exp
from dforge.tools.connectors.duckdb_connector import BaseConnector


class SQLValidationResult(BaseModel):
    is_valid: bool
    ast_parsed: bool
    is_read_only: bool
    contains_cartesian_product: bool
    errors: List[str] = Field(default_factory=list)
    formatted_sql: Optional[str] = None
    dry_run_success: bool = False
    estimated_rows: Optional[int] = None


class SQLValidator:
    """Performs deterministic AST analysis and static safety checks on generated SQL."""

    FORBIDDEN_EXPRESSIONS = [
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
    ]

    def __init__(self, connector: Optional[BaseConnector] = None, dialect: str = "duckdb"):
        self.connector = connector
        self.dialect = dialect

    def validate_sql(self, sql_query: str) -> SQLValidationResult:
        errors = []
        is_read_only = True
        ast_parsed = False
        formatted_sql = None
        has_cartesian = False

        # 1. Parse AST
        try:
            parsed = sqlglot.parse_one(sql_query, read=self.dialect)
            ast_parsed = True
            formatted_sql = parsed.sql(dialect=self.dialect, pretty=True)
        except Exception as e:
            return SQLValidationResult(
                is_valid=False,
                ast_parsed=False,
                is_read_only=False,
                contains_cartesian_product=False,
                errors=[f"SQL syntax / parsing error: {e}"],
            )

        # 2. Check for DDL / DML write operations (Principle 8: Least Privilege)
        for forbidden in self.FORBIDDEN_EXPRESSIONS:
            if parsed.find(forbidden):
                is_read_only = False
                errors.append(f"Forbidden non-read-only operation detected: {forbidden.__name__}")

        # 3. Detect unintentional Cartesian Joins
        for join in parsed.find_all(exp.Join):
            # If JOIN without ON or USING clause and not CROSS JOIN explicitly
            if not join.args.get("on") and not join.args.get("using") and join.args.get("kind") != "CROSS":
                has_cartesian = True
                errors.append("Unsafe Cartesian product detected: JOIN missing ON/USING clause.")

        is_valid = (len(errors) == 0 and is_read_only and ast_parsed)

        # 4. Dry-run query execution against warehouse (if connector provided)
        dry_run_success = False
        estimated_rows = None
        if is_valid and self.connector:
            try:
                # Dry run with LIMIT 1 to test warehouse compatibility and calculate row count safely
                _, rows = self.connector.execute_query(sql_query, limit=1)
                dry_run_success = True
                estimated_rows = len(rows)
            except Exception as e:
                is_valid = False
                errors.append(f"Warehouse dry-run execution failed: {e}")

        return SQLValidationResult(
            is_valid=is_valid,
            ast_parsed=ast_parsed,
            is_read_only=is_read_only,
            contains_cartesian_product=has_cartesian,
            errors=errors,
            formatted_sql=formatted_sql,
            dry_run_success=dry_run_success,
            estimated_rows=estimated_rows,
        )
