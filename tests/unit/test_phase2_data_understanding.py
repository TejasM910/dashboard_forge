"""Comprehensive unit and integration test suite for Phase 2: Data Understanding."""

import pytest
from pathlib import Path
from dforge.tools.connectors.duckdb_connector import DuckDBConnector
from dforge.tools.profiling.profiler import DataProfiler, TableProfile
from dforge.tools.profiling.inferrer import RelationshipInferrer
from dforge.tools.profiling.pii_masker import PIIMasker
from dforge.agents.semantic_mapper import SemanticMapper, SemanticMappingPlan
from dforge.core.models import Requirement, RequirementType, RequirementPriority, RequirementStatus
from dforge.llm.provider import MockLLMProvider


@pytest.fixture
def golden_db_path() -> Path:
    target = Path("evals/datasets/golden_ecommerce.duckdb")
    if not target.exists():
        from evals.datasets.create_golden_dataset import create_golden_ecommerce_dataset
        create_golden_ecommerce_dataset(target)
    return target


def test_duckdb_connector(golden_db_path):
    connector = DuckDBConnector(golden_db_path)
    tables = connector.list_tables()
    assert "orders" in tables
    assert "order_items" in tables
    assert "customers" in tables
    assert "products" in tables

    schema = connector.get_table_schema("orders")
    col_names = [c["name"] for c in schema]
    assert "order_id" in col_names
    assert "customer_id" in col_names
    assert "order_date" in col_names

    cols, rows = connector.execute_query("SELECT COUNT(*) FROM orders")
    assert len(rows) == 1
    assert rows[0][0] == 100


def test_data_profiler(golden_db_path):
    connector = DuckDBConnector(golden_db_path)
    profiler = DataProfiler(connector)

    order_profile = profiler.profile_table("orders")
    assert order_profile.table_name == "orders"
    assert order_profile.row_count == 100

    pk_cols = [c for c in order_profile.columns if c.name == "order_id"]
    assert len(pk_cols) == 1
    assert pk_cols[0].is_candidate_pk is True
    assert pk_cols[0].null_percentage == 0.0
    assert pk_cols[0].distinct_count == 100


def test_relationship_inferrer(golden_db_path):
    connector = DuckDBConnector(golden_db_path)
    profiler = DataProfiler(connector)
    all_profiles = profiler.profile_all()

    schema_graph = RelationshipInferrer.infer_schema_graph(all_profiles)
    assert "orders" in schema_graph.table_pks
    assert "order_id" in schema_graph.table_pks["orders"]

    # Verify orders -> customers relationship detected
    rel_names = [(r.from_table, r.from_column, r.to_table, r.to_column) for r in schema_graph.relationships]
    assert ("orders", "customer_id", "customers", "customer_id") in rel_names


def test_pii_masker(golden_db_path):
    connector = DuckDBConnector(golden_db_path)
    profiler = DataProfiler(connector)
    cust_profile = profiler.profile_table("customers")

    sanitized = PIIMasker.sanitize_profile_for_llm(cust_profile)
    name_col = next(c for c in sanitized.columns if c.name == "name")
    assert name_col.min_value == "[REDACTED_PII]"
    assert name_col.max_value == "[REDACTED_PII]"


@pytest.mark.asyncio
async def test_semantic_mapper_agent(golden_db_path):
    mock_mapping = {
        "SemanticMappingPlan": {
            "project_id": "proj-sales",
            "mappings": [
                {
                    "requirement_id": "REQ-001",
                    "term": "Net Revenue",
                    "target_table": "order_items",
                    "target_column": "line_total",
                    "transformation": "sum(line_total)",
                    "confidence": 0.99,
                },
                {
                    "requirement_id": "REQ-002",
                    "term": "Product Category",
                    "target_table": "products",
                    "target_column": "category",
                    "transformation": "exact",
                    "confidence": 0.97,
                },
            ],
        }
    }
    provider = MockLLMProvider(canned_responses=mock_mapping)
    mapper = SemanticMapper(llm_provider=provider)

    connector = DuckDBConnector(golden_db_path)
    profiler = DataProfiler(connector)
    profiles = profiler.profile_all()

    reqs = [
        Requirement(
            id="REQ-001",
            project_id="proj-sales",
            text="Calculate Net Revenue",
            type=RequirementType.METRIC,
            status=RequirementStatus.APPROVED,
        ),
        Requirement(
            id="REQ-002",
            project_id="proj-sales",
            text="Filter by Product Category",
            type=RequirementType.FILTER,
            status=RequirementStatus.APPROVED,
        ),
    ]

    plan = await mapper.generate_mapping_plan(
        project_id="proj-sales",
        requirements=reqs,
        profiles=profiles,
    )

    assert len(plan.mappings) == 2
    assert plan.mappings[0].requirement_id == "REQ-001"
    assert plan.mappings[0].target_table == "order_items"
    assert plan.mappings[1].target_column == "category"
from dforge.tools.profiling.eda_analyzer import QualityAndEDAAnalyzer, EDAReport, NullDiagnosis


def test_eda_and_null_handling(golden_db_path):
    connector = DuckDBConnector(golden_db_path)
    profiler = DataProfiler(connector)
    eda = QualityAndEDAAnalyzer(connector)

    order_profile = profiler.profile_table("orders")
    eda_report = eda.analyze_table_eda(order_profile)

    assert eda_report.table_name == "orders"
    # Ensure IQR outlier checks computed
    assert len(eda_report.outliers) > 0

    # Test orphan key check
    orphan_issue = eda.check_orphan_keys(
        from_table="orders",
        from_column="customer_id",
        to_table="customers",
        to_column="customer_id",
    )
    # In golden dataset, all customer_ids map cleanly to customers table
    assert orphan_issue is None
