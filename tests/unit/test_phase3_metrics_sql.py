"""Comprehensive unit test suite for Phase 3: Metrics & SQL."""

import pytest
from pathlib import Path
from dforge.core.models import MetricDefinition, Requirement, RequirementType, RequirementStatus
from dforge.semantic.layer import SemanticLayer
from dforge.agents.metric_designer import MetricDesigner, MetricDesignerOutput
from dforge.agents.semantic_mapper import SemanticMappingPlan
from dforge.agents.sql_generator import SQLGenerator
from dforge.tools.sql.sql_validator import SQLValidator
from dforge.tools.connectors.duckdb_connector import DuckDBConnector
from dforge.tools.profiling.inferrer import SchemaGraph, CandidateRelationship
from dforge.llm.provider import MockLLMProvider


@pytest.fixture
def golden_db_path() -> Path:
    return Path("evals/datasets/golden_ecommerce.duckdb")


def test_semantic_layer_serialization(tmp_path):
    metric = MetricDefinition(
        name="net_revenue",
        label="Net Revenue ($)",
        description="Total completed revenue minus discounts",
        formula="ROUND(SUM(line_total), 2)",
        dataset="order_items",
        grain="order_id",
        unit="USD",
        requirement_ids=["REQ-001"],
    )
    layer = SemanticLayer()
    layer.register_metric(metric)

    out_file = tmp_path / "metrics.yaml"
    layer.save_to_file(out_file)
    assert out_file.exists()

    loaded_layer = SemanticLayer.load_from_file(out_file)
    loaded_metric = loaded_layer.get_metric("net_revenue")
    assert loaded_metric.name == "net_revenue"
    assert loaded_metric.formula == "ROUND(SUM(line_total), 2)"


@pytest.mark.asyncio
async def test_metric_designer_agent():
    mock_output = {
        "MetricDesignerOutput": {
            "metrics": [
                {
                    "name": "net_revenue",
                    "label": "Net Revenue ($)",
                    "description": "Total revenue after discounts",
                    "formula": "ROUND(SUM(line_total - COALESCE(discount_amount, 0)), 2)",
                    "dataset": "order_items",
                    "grain": "order_id",
                    "unit": "USD",
                    "requirement_ids": ["REQ-001"],
                    "status": "draft",
                }
            ],
            "self_critique": "Verified that discount_amount uses COALESCE and grain is order_id.",
        }
    }
    provider = MockLLMProvider(canned_responses=mock_output)
    designer = MetricDesigner(llm_provider=provider)

    reqs = [
        Requirement(id="REQ-001", project_id="proj-sales", text="Calculate Net Revenue", type=RequirementType.METRIC, status=RequirementStatus.APPROVED)
    ]
    mapping = SemanticMappingPlan(
        project_id="proj-sales",
        mappings=[
            {
                "requirement_id": "REQ-001",
                "term": "Net Revenue",
                "target_table": "order_items",
                "target_column": "line_total",
                "transformation": "sum(line_total)",
                "confidence": 0.99,
            }
        ],
    )

    result = await designer.design_metrics(reqs, mapping)
    assert len(result.metrics) == 1
    assert result.metrics[0].name == "net_revenue"
    assert "COALESCE" in result.metrics[0].formula


def test_sql_validator_static_checks(golden_db_path):
    connector = DuckDBConnector(golden_db_path)
    validator = SQLValidator(connector=connector)

    # 1. Valid SQL with live dry-run
    valid_sql = "SELECT category, count(*) FROM products GROUP BY category;"
    res_valid = validator.validate_sql(valid_sql)
    assert res_valid.is_valid is True
    assert res_valid.dry_run_success is True

    # 2. Forbidden DML check
    drop_sql = "DROP TABLE products;"
    res_drop = validator.validate_sql(drop_sql)
    assert res_drop.is_valid is False
    assert res_drop.is_read_only is False
    assert any("Forbidden" in err for err in res_drop.errors)

    # 3. Unsafe Cartesian Join check
    cartesian_sql = "SELECT * FROM orders JOIN products;"
    res_cartesian = validator.validate_sql(cartesian_sql)
    assert res_cartesian.is_valid is False
    assert res_cartesian.contains_cartesian_product is True


def test_sql_generator_and_execution(golden_db_path):
    connector = DuckDBConnector(golden_db_path)
    validator = SQLValidator(connector=connector)

    schema_graph = SchemaGraph(
        table_pks={"orders": ["order_id"], "order_items": ["item_id"], "products": ["product_id"]},
        relationships=[
            CandidateRelationship(from_table="order_items", from_column="order_id", to_table="orders", to_column="order_id"),
            CandidateRelationship(from_table="order_items", from_column="product_id", to_table="products", to_column="product_id"),
        ],
    )
    generator = SQLGenerator(schema_graph=schema_graph, dialect="duckdb")

    metric = MetricDefinition(
        name="total_revenue",
        label="Total Revenue",
        description="Sum of line totals",
        formula="ROUND(SUM(line_total), 2)",
        dataset="order_items",
        grain="order_id",
        unit="USD",
        requirement_ids=["REQ-001"],
    )

    # Generate query sliced by products.category
    gen_query = generator.generate_metric_query(
        metric=metric,
        dimensions=["products.category"],
        filters=["orders.status = 'completed'"],
    )

    # Validate generated query through AST & dry-run against warehouse
    val_res = validator.validate_sql(gen_query.sql)
    assert val_res.is_valid is True
    assert val_res.dry_run_success is True

    # Execute query live and verify real numbers
    cols, rows = connector.execute_query(gen_query.sql)
    assert len(rows) > 0
    assert "category" in cols[0]
