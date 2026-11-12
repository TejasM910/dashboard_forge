"""SQL Generator Agent: Produces dialect-aware SQL queries from metric definitions and layout dimensions (T-304 & FR-42)."""

from typing import List, Optional
from pydantic import BaseModel, Field
import sqlglot
from dforge.core.models import MetricDefinition
from dforge.tools.profiling.inferrer import SchemaGraph


class GeneratedQuery(BaseModel):
    metric_name: str
    target_dialect: str = "duckdb"
    sql: str
    dimensions: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class SQLGenerator:
    """Generates deterministic SQL for metrics with proper joins, dimensions, and filter conditions."""

    def __init__(self, schema_graph: SchemaGraph, dialect: str = "duckdb"):
        self.schema_graph = schema_graph
        self.dialect = dialect

    def generate_metric_query(
        self,
        metric: MetricDefinition,
        dimensions: Optional[List[str]] = None,
        filters: Optional[List[str]] = None,
        time_grain: Optional[str] = None,
    ) -> GeneratedQuery:
        dims = dimensions or metric.dimensions or []
        flts = list(metric.filters)
        if filters:
            flts.extend(filters)

        # Base SELECT list
        select_items = []
        group_by_items = []

        # Handle dimensions
        for d in dims:
            select_items.append(d)
            group_by_items.append(d)

        # Metric aggregation formula
        select_items.append(f"{metric.formula} AS {metric.name}")

        # FROM and JOIN logic based on SchemaGraph
        from_table = metric.dataset
        joins = []

        # Automatic join resolution if dimensions span multiple tables
        # Example: if querying order_items and needing products.category
        if from_table == "orders" and any("line_total" in f or "item" in f for f in [metric.formula] + flts):
            joins.append("JOIN order_items ON orders.order_id = order_items.order_id")
        elif from_table == "order_items":
            if any("category" in d or "title" in d for d in dims + flts):
                joins.append("JOIN products ON order_items.product_id = products.product_id")
            if any("status" in fl or "order_date" in fl or "region" in fl for fl in flts + dims):
                joins.append("JOIN orders ON order_items.order_id = orders.order_id")
            if any("region" in d or "segment" in d for d in dims + flts):
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
