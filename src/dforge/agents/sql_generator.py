"""SQL Generator Agent: Produces dialect-aware SQL queries from metric definitions and layout dimensions (T-304 & FR-42)."""


import sqlglot
from pydantic import BaseModel, Field

from dforge.core.models import MetricDefinition
from dforge.tools.profiling.inferrer import SchemaGraph


class GeneratedQuery(BaseModel):
    metric_name: str
    target_dialect: str = "duckdb"
    sql: str
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    explanation: str | None = None


class SQLGenerator:
    """Generates deterministic SQL for metrics with proper joins, dimensions, and filter conditions."""

    def __init__(self, schema_graph: SchemaGraph, dialect: str = "duckdb"):
        self.schema_graph = schema_graph
        self.dialect = dialect

    def generate_metric_query(
        self,
        metric: MetricDefinition,
        dimensions: list[str] | None = None,
        filters: list[str] | None = None,
        time_grain: str | None = None,
        time_dimension: str | None = None,
    ) -> GeneratedQuery:
        dims = list(metric.dimensions) if dimensions is None else list(dimensions)
        flts = list(metric.filters)
        if filters:
            flts.extend(filters)
        selected_time_dimension = time_dimension or (metric.time_dimension if time_grain else None)
        if time_grain and not selected_time_dimension:
            raise ValueError("A time grain requires a metric time_dimension.")
        if time_grain and time_grain not in {"day", "week", "month", "quarter", "year"}:
            raise ValueError(f"Unsupported time grain '{time_grain}'.")

        # Base SELECT list
        select_items = []
        group_by_items = []

        # Handle dimensions
        for d in dims:
            select_items.append(d)
            group_by_items.append(d)

        if selected_time_dimension:
            time_expression = (
                f"DATE_TRUNC('{time_grain}', {selected_time_dimension})"
                if time_grain
                else selected_time_dimension
            )
            select_items.insert(0, f"{time_expression} AS time_period")
            group_by_items.insert(0, time_expression)

        # Metric aggregation formula
        select_items.append(f"{metric.formula} AS {metric.name}")

        # FROM and JOIN logic based on SchemaGraph
        from_table = metric.dataset
        joins = []

        # Automatic join resolution if dimensions span multiple tables
        # Example: if querying order_items and needing products.category
        used_fields = dims + ([selected_time_dimension] if selected_time_dimension else []) + flts
        if from_table == "orders" and any("line_total" in f or "item" in f for f in [metric.formula] + flts):
            joins.append("JOIN order_items ON orders.order_id = order_items.order_id")
        elif from_table == "order_items":
            if any("category" in d or "title" in d for d in used_fields):
                joins.append("JOIN products ON order_items.product_id = products.product_id")
            if any("status" in fl or "order_date" in fl or "region" in fl for fl in used_fields):
                joins.append("JOIN orders ON order_items.order_id = orders.order_id")
            if any("region" in d or "segment" in d for d in used_fields):
                if not any("JOIN orders" in j for j in joins):
                    joins.append("JOIN orders ON order_items.order_id = orders.order_id")
                joins.append("JOIN customers ON orders.customer_id = customers.customer_id")

        join_clause = " " + " ".join(joins) if joins else ""
        where_clause = f" WHERE {' AND '.join(flts)}" if flts else ""
        group_clause = f" GROUP BY {', '.join(group_by_items)}" if group_by_items else ""

        raw_sql = f"SELECT {', '.join(select_items)} FROM {from_table}{join_clause}{where_clause}{group_clause};"

        # Format and transpile through SQLGlot
        transpiled = sqlglot.transpile(raw_sql, read="duckdb", write=self.dialect, pretty=True)[0]

        return GeneratedQuery(
            metric_name=metric.name,
            target_dialect=self.dialect,
            sql=transpiled,
            dimensions=dims,
            filters=flts,
            explanation=f"Aggregated {metric.name} across {dims} from dataset {from_table}",
        )
