"""Verify Phase 4 dashboard design and query-backed widget data on the golden dataset."""

from pathlib import Path

from dforge.agents.dashboard_designer import DashboardDesigner, DimensionBinding
from dforge.agents.sql_generator import SQLGenerator
from dforge.core.models import (
    FilterSpec,
    MetricDefinition,
    Requirement,
    RequirementStatus,
    RequirementType,
)
from dforge.tools.bi.streamlit_renderer import (
    StreamlitDashboardRenderer,
    format_metric_value,
)
from dforge.tools.connectors.duckdb_connector import DuckDBConnector
from dforge.tools.profiling.inferrer import RelationshipInferrer
from dforge.tools.profiling.profiler import DataProfiler
from dforge.tools.sql.sql_validator import SQLValidator


def run_phase4_demo() -> None:
    print("=" * 72)
    print("DASHBOARD FORGE — PHASE 4 DASHBOARD BUILD VERIFICATION")
    print("=" * 72)

    project_id = "phase4-demo"
    requirements = [
        Requirement(
            id="REQ-401",
            project_id=project_id,
            text="Show net revenue.",
            type=RequirementType.METRIC,
            status=RequirementStatus.APPROVED,
        ),
        Requirement(
            id="REQ-402",
            project_id=project_id,
            text="Break revenue out by product category.",
            type=RequirementType.DIMENSION,
            status=RequirementStatus.APPROVED,
        ),
        Requirement(
            id="REQ-403",
            project_id=project_id,
            text="Filter by customer region.",
            type=RequirementType.FILTER,
            status=RequirementStatus.APPROVED,
        ),
    ]
    metric = MetricDefinition(
        name="net_revenue",
        label="Net Revenue",
        description="Sum of order item line totals.",
        formula="ROUND(SUM(line_total), 2)",
        dataset="order_items",
        grain="item_id",
        dimensions=["products.category"],
        unit="USD",
        format="#,##0.00",
        requirement_ids=["REQ-401", "REQ-402"],
        status="approved",
    )

    connector = DuckDBConnector(Path("evals/datasets/golden_ecommerce.duckdb"))
    profiles = DataProfiler(connector).profile_all()
    schema_graph = RelationshipInferrer.infer_schema_graph(profiles)
    generator = SQLGenerator(schema_graph=schema_graph)
    validator = SQLValidator(connector=connector)
    generated_query = generator.generate_metric_query(metric)
    query_validation = validator.validate_sql(generated_query.sql)
    if not query_validation.is_valid or not query_validation.dry_run_success:
        raise RuntimeError(f"Metric SQL did not pass validation: {query_validation.errors}")
    print("[1/3] Approved metric SQL passed AST checks and DuckDB dry-run.")

    region_filter = FilterSpec(
        id="customer-region",
        label="Customer region",
        column="customers.region",
        type="multi_select",
        requirement_ids=["REQ-403"],
    )
    spec = DashboardDesigner().design_dashboard(
        project_id=project_id,
        title="Phase 4 Sales Overview",
        requirements=requirements,
        metrics=[metric],
        schema_graph=schema_graph,
        profiles=profiles,
        validated_queries={metric.name: query_validation},
        dimension_mappings={
            "REQ-402": DimensionBinding(
                metric_name=metric.name,
                dimension="products.category",
            )
        },
        filter_mappings={"REQ-403": region_filter},
    )
    print("[2/3] DashboardSpec passed validation with KPI, chart, and traced filters.")

    _, region_rows = connector.execute_query(
        "SELECT DISTINCT region FROM customers ORDER BY region LIMIT 1"
    )
    if not region_rows:
        raise RuntimeError("The golden dataset has no customer regions to verify.")
    renderer = StreamlitDashboardRenderer(connector, schema_graph, profiles)
    chart_widget = spec.pages[0].widgets[1]
    chart_query = renderer.build_widget_query(
        metric=metric,
        widget=chart_widget,
        filter_specs=[region_filter],
        selected_filters={"customer-region": [region_rows[0][0]]},
    )
    chart_validation = validator.validate_sql(chart_query.sql)
    if not chart_validation.is_valid or not chart_validation.dry_run_success:
        raise RuntimeError(f"Widget SQL did not pass validation: {chart_validation.errors}")
    columns, rows = connector.execute_query(chart_query.sql)
    if not rows:
        raise RuntimeError("The filtered chart query returned no rows.")
    print("[3/3] Interactive chart filter produced executed warehouse values:")
    for row in rows[:5]:
        values = dict(zip(columns, row))
        print(
            f"  • {values['category']}: "
            f"{format_metric_value(values['net_revenue'], metric)}"
        )
    print("=" * 72)
    print("PHASE 4 DASHBOARD BUILD VERIFICATION PASSED")
    print("=" * 72)


if __name__ == "__main__":
    run_phase4_demo()
