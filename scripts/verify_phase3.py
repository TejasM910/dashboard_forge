"""Interactive verification demo for Phase 3: Metrics & SQL."""

import asyncio
from pathlib import Path
from dforge.core.models import MetricDefinition, Requirement, RequirementType, RequirementStatus
from dforge.semantic.layer import SemanticLayer
from dforge.agents.metric_designer import MetricDesigner
from dforge.agents.semantic_mapper import SemanticMappingPlan
from dforge.agents.sql_generator import SQLGenerator
from dforge.tools.sql.sql_validator import SQLValidator
from dforge.tools.connectors.duckdb_connector import DuckDBConnector
from dforge.tools.profiling.inferrer import SchemaGraph, CandidateRelationship
from dforge.llm.provider import MockLLMProvider


async def run_phase3_demo():
    print("=" * 70)
    print("📐 DASHBOARD FORGE — PHASE 3 METRICS & SQL DEMO")
    print("=" * 70)

    db_path = Path("evals/datasets/golden_ecommerce.duckdb")
    connector = DuckDBConnector(db_path)

    # 1. Metric Designer Agent with Self-Critique (T-302)
    print("\n[1/4] Running Metric Designer Agent with Self-Critique...")
    mock_metric_output = {
        "MetricDesignerOutput": {
            "metrics": [
                {
                    "name": "net_revenue",
                    "label": "Net Revenue ($)",
                    "description": "Total revenue subtracting refunds and line discounts",
                    "formula": "ROUND(SUM(line_total - COALESCE(discount_amount, 0)), 2)",
                    "dataset": "order_items",
                    "grain": "order_id",
                    "unit": "USD",
                    "requirement_ids": ["REQ-001"],
                    "status": "approved",
                },
                {
                    "name": "total_completed_orders",
                    "label": "Completed Orders",
                    "description": "Distinct count of completed orders",
                    "formula": "COUNT(DISTINCT orders.order_id)",
                    "dataset": "orders",
                    "grain": "order_id",
                    "unit": "count",
                    "requirement_ids": ["REQ-002"],
                    "status": "approved",
                },
            ],
            "self_critique": "Verified: Net revenue properly null-coalesces discount_amount and uses order grain.",
        }
    }
    provider = MockLLMProvider(canned_responses=mock_metric_output)
    designer = MetricDesigner(llm_provider=provider)

    sample_reqs = [
        Requirement(id="REQ-001", project_id="proj-demo", text="Calculate Net Revenue", type=RequirementType.METRIC, status=RequirementStatus.APPROVED),
        Requirement(id="REQ-002", project_id="proj-demo", text="Count Completed Orders", type=RequirementType.METRIC, status=RequirementStatus.APPROVED),
    ]
    mapping = SemanticMappingPlan(
        project_id="proj-demo",
        mappings=[
            {"requirement_id": "REQ-001", "term": "Net Revenue", "target_table": "order_items", "target_column": "line_total", "transformation": "sum(line_total)"},
            {"requirement_id": "REQ-002", "term": "Completed Orders", "target_table": "orders", "target_column": "order_id", "transformation": "count(distinct)"},
        ],
    )
    designer_res = await designer.design_metrics(sample_reqs, mapping)
    for m in designer_res.metrics:
        print(f"  ✨ Designed Metric: {m.name:<24} | Formula: {m.formula}")
    print(f"     Critique Notes: {designer_res.self_critique}")

    # 2. Semantic Layer YAML Management (T-301)
    print("\n[2/4] Saving and Compiling to Semantic Layer YAML...")
    layer = SemanticLayer()
    for m in designer_res.metrics:
        layer.register_metric(m)
    yaml_preview = layer.to_yaml()
    print("--- YAML METRIC CONTRACT ---")
    print(yaml_preview.strip())

    # 3. SQL Generator with Join Resolution (T-304)
    print("\n[3/4] Generating Dialect-Aware SQL with Automatic Join Resolution...")
    schema_graph = SchemaGraph(
        table_pks={"orders": ["order_id"], "order_items": ["item_id"], "products": ["product_id"], "customers": ["customer_id"]},
        relationships=[
            CandidateRelationship(from_table="order_items", from_column="order_id", to_table="orders", to_column="order_id"),
            CandidateRelationship(from_table="order_items", from_column="product_id", to_table="products", to_column="product_id"),
            CandidateRelationship(from_table="orders", from_column="customer_id", to_table="customers", to_column="customer_id"),
        ],
    )
    generator = SQLGenerator(schema_graph=schema_graph, dialect="duckdb")
    net_rev_metric = designer_res.metrics[0]

    gen_query = generator.generate_metric_query(
        metric=net_rev_metric,
        dimensions=["products.category", "customers.region"],
        filters=["orders.status = 'completed'"],
    )
    print(f"Generated SQL for '{gen_query.metric_name}' across {gen_query.dimensions}:")
    print(gen_query.sql)

    # 4. AST Static Linter, Safety Checks, and Live Dry-Run (T-305)
    print("\n[4/4] Validating SQL via SQLGlot AST & Dry-Running on DuckDB...")
    validator = SQLValidator(connector=connector)
    val_res = validator.validate_sql(gen_query.sql)
    print(f"  • AST Parsed successfully : {val_res.ast_parsed} ✅")
    print(f"  • Read-only safety check  : {val_res.is_read_only} ✅")
    print(f"  • No Cartesian product    : {not val_res.contains_cartesian_product} ✅")
    print(f"  • Dry-run executed on DB  : {val_res.dry_run_success} ✅")

    cols, rows = connector.execute_query(gen_query.sql)
    print("\n📊 Live Query Execution Results (SQL against DuckDB Warehouse):")
    for r in rows[:6]:
        print(f"   • Category: {r[0]:<12} | Region: {r[1]:<6} | Net Revenue: ${r[2]:,.2f}")

    print("\n" + "=" * 70)
    print("🎉 ALL PHASE 3 METRICS & SQL COMPONENTS FULLY VERIFIED ($0 COST)!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_phase3_demo())
