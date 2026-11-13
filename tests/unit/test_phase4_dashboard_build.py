"""Phase 4 dashboard schema, design, preview data, and BI adapter tests."""

import json
from pathlib import Path

import httpx
import pytest
import yaml
from pydantic import ValidationError

from dforge.agents.dashboard_designer import DashboardDesigner, DimensionBinding
from dforge.agents.sql_generator import SQLGenerator
from dforge.core.models import (
    DashboardPage,
    DashboardSpec,
    FilterSpec,
    MetricDefinition,
    Requirement,
    RequirementStatus,
    RequirementType,
    WidgetSpec,
    WidgetType,
)
from dforge.tools.bi.adapter import SupersetDatasetRef
from dforge.tools.bi.chart_recommender import ChartRecommender
from dforge.tools.bi.streamlit_renderer import (
    StreamlitDashboardRenderer,
    format_metric_value,
)
from dforge.tools.bi.superset_adapter import BIAdapterError, SupersetBIAdapter
from dforge.tools.connectors.duckdb_connector import DuckDBConnector
from dforge.tools.profiling.inferrer import RelationshipInferrer
from dforge.tools.profiling.profiler import DataProfiler
from dforge.tools.sql.sql_validator import SQLValidator
from dforge.validation.dashboard_spec_validator import DashboardSpecValidator

PROJECT_ID = "proj-phase4"
GOLDEN_DB = Path("evals/datasets/golden_ecommerce.duckdb")


@pytest.fixture
def phase4_context():
    connector = DuckDBConnector(GOLDEN_DB)
    profiles = DataProfiler(connector).profile_all()
    schema_graph = RelationshipInferrer.infer_schema_graph(profiles)
    requirement = Requirement(
        id="REQ-001",
        project_id=PROJECT_ID,
        text="Show monthly net revenue by product category.",
        type=RequirementType.METRIC,
        status=RequirementStatus.APPROVED,
    )
    metric = MetricDefinition(
        name="net_revenue",
        label="Net Revenue",
        description="Sum of line totals.",
        formula="ROUND(SUM(line_total), 2)",
        dataset="order_items",
        grain="item_id",
        time_dimension="orders.order_date",
        dimensions=["products.category"],
        unit="USD",
        requirement_ids=[requirement.id],
        status="approved",
    )
    generator = SQLGenerator(schema_graph=schema_graph)
    generated = generator.generate_metric_query(metric, time_grain="month")
    validation = SQLValidator(connector=connector).validate_sql(generated.sql)
    return connector, profiles, schema_graph, requirement, metric, validation


def test_dashboard_spec_model_rejects_empty_pages_and_duplicate_ids():
    with pytest.raises(ValidationError):
        DashboardSpec(
            id="dashboard",
            title="Dashboard",
            description="",
            project_id=PROJECT_ID,
            pages=[],
        )

    widget = WidgetSpec(
        id="widget",
        title="Revenue",
        type=WidgetType.KPI_CARD,
        metric="net_revenue",
    )
    with pytest.raises(ValidationError, match="Widget on page"):
        DashboardSpec(
            id="dashboard",
            title="Dashboard",
            description="",
            project_id=PROJECT_ID,
            pages=[
                DashboardPage(
                    id="overview",
                    title="Overview",
                    widgets=[widget, widget.model_copy()],
                )
            ],
        )
    with pytest.raises(ValidationError, match="hex color"):
        DashboardSpec(
            id="dashboard",
            title="Dashboard",
            description="",
            project_id=PROJECT_ID,
            theme={"primary_color": "red"},
            pages=[DashboardPage(id="overview", title="Overview", widgets=[widget])],
        )
    with pytest.raises(ValidationError):
        WidgetSpec(
            id="too-wide",
            title="Too wide",
            type=WidgetType.KPI_CARD,
            metric="net_revenue",
            width=13,
        )


def test_sample_dashboard_spec_round_trips_to_canonical_model():
    with Path("examples/sample-dashboard-spec.yaml").open(encoding="utf-8") as file:
        spec = DashboardSpec.model_validate(yaml.safe_load(file))
    assert spec.pages[0].widgets[0].type == WidgetType.KPI_CARD
    assert len(spec.pages[0].widgets) == 7


def test_date_range_default_uses_latest_profiled_date(phase4_context):
    connector, profiles, graph, _, _, _ = phase4_context
    renderer = StreamlitDashboardRenderer(connector, graph, profiles)
    date_filter = FilterSpec(
        id="date-range",
        label="Date range",
        column="orders.order_date",
        type="date_range",
        default_value="last_12_weeks",
    )
    start_date, end_date = renderer._date_range_default(date_filter)
    assert (end_date - start_date).days == 84
    with pytest.raises(ValidationError, match="Date-range defaults"):
        FilterSpec(
            id="bad-date-range",
            label="Date range",
            column="orders.order_date",
            type="date_range",
            default_value="last_few_weeks",
        )


def test_chart_recommender_selects_deterministic_types(phase4_context):
    _, profiles, _, _, metric, _ = phase4_context
    recommender = ChartRecommender()

    assert recommender.recommend(metric.model_copy(update={"dimensions": [], "time_dimension": None})).chart_type == WidgetType.KPI_CARD
    assert recommender.recommend(metric, profiles=profiles).chart_type == WidgetType.LINE
    assert recommender.recommend(
        metric.model_copy(update={"time_dimension": None}),
        dimensions=["products.category"],
        profiles=profiles,
    ).chart_type == WidgetType.BAR
    assert recommender.recommend(
        metric.model_copy(update={"time_dimension": None}),
        dimensions=["products.category", "customers.region"],
        profiles=profiles,
    ).chart_type == WidgetType.HEATMAP
    assert recommender.recommend(
        metric.model_copy(update={"time_dimension": None}),
        dimensions=["products.category", "customers.region", "orders.status"],
        profiles=profiles,
    ).chart_type == WidgetType.TABLE
    assert recommender.recommend(
        metric.model_copy(update={"time_dimension": None}),
        dimensions=["orders.order_id"],
        profiles=profiles,
    ).chart_type == WidgetType.TABLE


def test_streamlit_layout_wraps_widgets_at_the_twelve_column_limit():
    widgets = [
        WidgetSpec(
            id=f"widget-{index}",
            title=f"Widget {index}",
            type=WidgetType.KPI_CARD,
            metric="net_revenue",
            width=width,
        )
        for index, width in enumerate([6, 6, 3], start=1)
    ]
    rows = StreamlitDashboardRenderer._layout_rows(widgets)
    assert [[widget.id for widget in row] for row in rows] == [
        ["widget-1", "widget-2"],
        ["widget-3"],
    ]


def test_dashboard_designer_requires_approved_inputs_and_successful_sql(phase4_context):
    _, profiles, graph, requirement, metric, validation = phase4_context
    assert validation.is_valid and validation.dry_run_success

    spec = DashboardDesigner().design_dashboard(
        project_id=PROJECT_ID,
        title="Sales Overview",
        requirements=[requirement],
        metrics=[metric],
        schema_graph=graph,
        profiles=profiles,
        validated_queries={metric.name: validation},
    )
    widgets = spec.pages[0].widgets
    assert [widget.type for widget in widgets] == [WidgetType.KPI_CARD, WidgetType.LINE]
    chart = widgets[1]
    assert chart.time_dimension == metric.time_dimension
    assert chart.time_grain == "month"
    assert chart.requirement_ids == [requirement.id]

    dimension_requirement = Requirement(
        id="REQ-002",
        project_id=PROJECT_ID,
        text="Break revenue out by product category.",
        type=RequirementType.DIMENSION,
        status=RequirementStatus.APPROVED,
    )
    metric_with_dimension_requirement = metric.model_copy(
        update={"requirement_ids": [requirement.id, dimension_requirement.id]}
    )
    dimension_spec = DashboardDesigner().design_dashboard(
        project_id=PROJECT_ID,
        title="Sales by Category",
        requirements=[requirement, dimension_requirement],
        metrics=[metric_with_dimension_requirement],
        schema_graph=graph,
        profiles=profiles,
        validated_queries={metric.name: validation},
        dimension_mappings={
            dimension_requirement.id: DimensionBinding(
                metric_name=metric.name,
                dimension="products.category",
            )
        },
    )
    assert dimension_requirement.id in dimension_spec.pages[0].widgets[1].requirement_ids

    with pytest.raises(ValueError, match="explicit mappings"):
        DashboardDesigner().design_dashboard(
            project_id=PROJECT_ID,
            title="Sales by Category",
            requirements=[requirement, dimension_requirement],
            metrics=[metric_with_dimension_requirement],
            schema_graph=graph,
            profiles=profiles,
            validated_queries={metric.name: validation},
        )

    with pytest.raises(ValueError, match="not approved"):
        DashboardDesigner().design_dashboard(
            project_id=PROJECT_ID,
            title="Sales Overview",
            requirements=[requirement.model_copy(update={"status": RequirementStatus.DRAFT})],
            metrics=[metric],
            schema_graph=graph,
            profiles=profiles,
            validated_queries={metric.name: validation},
        )

    with pytest.raises(ValueError, match="dry-run"):
        DashboardDesigner().design_dashboard(
            project_id=PROJECT_ID,
            title="Sales Overview",
            requirements=[requirement],
            metrics=[metric],
            schema_graph=graph,
            profiles=profiles,
            validated_queries={
                metric.name: validation.model_copy(update={"dry_run_success": False})
            },
        )


def test_dashboard_validator_checks_references_filters_and_schema(phase4_context):
    _, profiles, graph, requirement, metric, _ = phase4_context
    spec = DashboardSpec(
        id="dashboard",
        title="Sales Overview",
        description="",
        project_id=PROJECT_ID,
        global_filters=[
            FilterSpec(
                id="region",
                label="Region",
                column="customers.region",
                type="multi_select",
            )
        ],
        pages=[
            DashboardPage(
                id="overview",
                title="Overview",
                widgets=[
                    WidgetSpec(
                        id="chart",
                        title="Revenue by category",
                        type=WidgetType.BAR,
                        metric=metric.name,
                        dimensions=["products.category"],
                        filters=["missing-filter"],
                        requirement_ids=[requirement.id, "REQ-MISSING"],
                    )
                ],
            )
        ],
    )
    result = DashboardSpecValidator().validate(
        spec,
        [metric],
        [requirement],
        profiles,
        graph,
    )
    assert not result.is_valid
    assert {issue.code for issue in result.issues} >= {
        "unknown_filter",
        "unknown_requirement",
    }


def test_streamlit_filter_expressions_are_escaped_and_metric_formatting(phase4_context):
    connector, profiles, graph, _, metric, _ = phase4_context
    renderer = StreamlitDashboardRenderer(connector, graph, profiles)
    dashboard_filter = FilterSpec(
        id="region",
        label="Region",
        column="customers.region",
        type="select",
    )
    renderer._rendering_filters = [dashboard_filter]
    expression = renderer._filter_expression(
        dashboard_filter,
        "O'Reilly",
    )
    assert expression is not None
    assert "'O''Reilly'" in expression
    assert format_metric_value(1234.5, metric) == "$1,234.50"

    chart_widget = WidgetSpec(
        id="revenue-chart",
        title="Revenue by category",
        type=WidgetType.LINE,
        metric=metric.name,
        dimensions=metric.dimensions,
        time_dimension=metric.time_dimension,
        time_grain="month",
        requirement_ids=metric.requirement_ids,
    )
    _, region_rows = connector.execute_query("SELECT DISTINCT region FROM customers LIMIT 1")
    assert region_rows
    query = renderer.build_widget_query(
        metric,
        chart_widget,
        [dashboard_filter],
        {"region": region_rows[0][0]},
    )
    result = SQLValidator(connector=connector).validate_sql(query.sql)
    assert result.is_valid and result.dry_run_success
    columns, rows = connector.execute_query(query.sql)
    assert "time_period" in columns
    assert "net_revenue" in columns
    assert rows


def test_superset_adapter_publishes_and_fetches_widget_data():
    requests = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v1/chart/":
            payload = json.loads(request.content)
            assert payload["viz_type"] == "big_number_total"
            return httpx.Response(201, json={"result": {"id": 41}})
        if request.url.path == "/api/v1/dashboard/":
            payload = json.loads(request.content)
            assert payload["published"] is True
            metadata = json.loads(payload["json_metadata"])
            assert metadata["native_filter_configuration"][0]["targets"] == [
                {"datasetId": 12, "column": {"name": "region"}}
            ]
            return httpx.Response(201, json={"result": {"id": 7}})
        if request.url.path == "/api/v1/chart/data":
            payload = json.loads(request.content)
            assert payload["queries"][0]["filters"] == [
                {"col": "region", "op": "IN", "val": ["CA", "NY"]},
                {"col": "order_date", "op": ">=", "val": "2024-01-01"},
                {"col": "order_date", "op": "<=", "val": "2024-02-01"},
            ]
            return httpx.Response(
                200,
                json={"result": [{"data": [{"net_revenue": 123.0}]}]},
            )
        if request.url.path.endswith("/thumbnail/"):
            return httpx.Response(
                200,
                content=b"png",
                headers={"content-type": "image/png"},
            )
        return httpx.Response(404, json={"message": "unexpected endpoint"})

    client = httpx.Client(transport=httpx.MockTransport(handle_request))
    adapter = SupersetBIAdapter(
        "http://localhost:8088",
        access_token="test-token",
        client=client,
    )
    spec = DashboardSpec(
        id="sales",
        title="Sales",
        description="",
        project_id=PROJECT_ID,
        global_filters=[
            FilterSpec(
                id="region",
                label="Region",
                column="customers.region",
                type="multi_select",
            )
        ],
        pages=[
            DashboardPage(
                id="overview",
                title="Overview",
                widgets=[
                    WidgetSpec(
                        id="revenue",
                        title="Revenue",
                        type=WidgetType.KPI_CARD,
                        metric="net_revenue",
                        requirement_ids=["REQ-001"],
                    )
                ],
            )
        ],
    )
    datasets = [
        SupersetDatasetRef(
            metric_name="net_revenue",
            metric_label="Net Revenue",
            metric_expression="SUM(line_total)",
            datasource_id=12,
            columns=["line_total", "region"],
        )
    ]

    published = adapter.publish(spec, datasets)
    assert published.dashboard_id == 7
    assert published.widget_chart_ids == {"revenue": 41}
    assert adapter.fetch_widget_data(
        published,
        "revenue",
        filters={
            "region": ["CA", "NY"],
            "order_date": ("2024-01-01", "2024-02-01"),
        },
    ).to_dict(orient="records") == [{"net_revenue": 123.0}]
    assert adapter.screenshot(published, "overview") == b"png"
    assert all(
        request.headers["authorization"] == "Bearer test-token"
        for request in requests
    )


def test_superset_adapter_rejects_unbound_metrics_before_network_call():
    def fail_if_called(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Unexpected network call: {request.url}")

    adapter = SupersetBIAdapter(
        "http://localhost:8088",
        access_token="test-token",
        client=httpx.Client(transport=httpx.MockTransport(fail_if_called)),
    )
    spec = DashboardSpec(
        id="sales",
        title="Sales",
        description="",
        project_id=PROJECT_ID,
        pages=[
            DashboardPage(
                id="overview",
                title="Overview",
                widgets=[
                    WidgetSpec(
                        id="revenue",
                        title="Revenue",
                        type=WidgetType.KPI_CARD,
                        metric="net_revenue",
                    )
                ],
            )
        ],
    )
    with pytest.raises(BIAdapterError, match="No Superset dataset binding"):
        adapter.publish(spec, [])


def test_superset_adapter_rejects_unsafe_metric_functions():
    adapter = SupersetBIAdapter("http://localhost:8088", access_token="test-token")
    spec = DashboardSpec(
        id="sales",
        title="Sales",
        description="",
        project_id=PROJECT_ID,
        pages=[
            DashboardPage(
                id="overview",
                title="Overview",
                widgets=[
                    WidgetSpec(
                        id="revenue",
                        title="Revenue",
                        type=WidgetType.KPI_CARD,
                        metric="net_revenue",
                    )
                ],
            )
        ],
    )
    issues = adapter.validate(
        spec,
        [
            SupersetDatasetRef(
                metric_name="net_revenue",
                metric_label="Revenue",
                metric_expression="read_csv('file.csv')",
                datasource_id=10,
            )
        ],
    )
    assert any(issue.code == "invalid_metric_expression" for issue in issues)


def test_superset_layout_preserves_pages_as_tabs():
    layout = SupersetBIAdapter._position_json(
        [
            {
                "chart_id": 1,
                "widget_id": "sales",
                "width": 6,
                "page_id": "overview",
                "page_title": "Overview",
            },
            {
                "chart_id": 2,
                "widget_id": "regions",
                "width": 6,
                "page_id": "regions",
                "page_title": "Regions",
            },
        ]
    )
    assert layout["GRID_ID"]["children"] == ["TABS_ID"]
    assert layout["TABS_ID"]["children"] == ["TAB-0-overview", "TAB-1-regions"]
