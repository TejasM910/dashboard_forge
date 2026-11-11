"""Interactive Phase 0 verification demo."""

import asyncio
from pathlib import Path
import duckdb
from dforge.core.models import (
    Requirement,
    RequirementType,
    RequirementPriority,
    RequirementStatus,
    MetricDefinition,
)
from dforge.llm.provider import MockLLMProvider


async def run_phase0_demo():
    print("=" * 65)
    print("🚀 DASHBOARD FORGE — PHASE 0 VERIFICATION DEMO")
    print("=" * 65)

    # 1. Test Pydantic Models
    print("\n[1/3] Testing Core Data Models (specs/05-data-models.md)...")
    req = Requirement(
        id="REQ-001",
        project_id="demo-ecommerce",
        text="Display monthly net revenue for 2025 by product category",
        type=RequirementType.METRIC,
        priority=RequirementPriority.MUST,
        status=RequirementStatus.APPROVED,
        source_citation="sample-client-brief.md:line 10",
        confidence=0.98,
    )
    metric = MetricDefinition(
        name="net_revenue",
        label="Net Revenue ($)",
        description="Completed orders sum(line_total - discount)",
        formula="sum(line_total - discount_amount)",
        dataset="orders",
        grain="order_id",
        unit="USD",
        requirement_ids=[req.id],
    )
    print(f"  ✅ Requirement Created : {req.id} -> '{req.text}'")
    print(f"  ✅ Metric Definition    : {metric.name} ({metric.unit}) using [{metric.formula}]")

    # 2. Test LLM Structured Output Abstraction
    print("\n[2/3] Testing Zero-Cost LLM Provider Abstraction...")
    mock_data = {
        "Requirement": {
            "id": "REQ-002",
            "project_id": "demo-ecommerce",
            "text": "Show order return rate percentage",
            "type": "metric",
            "priority": "should",
            "status": "draft",
            "confidence": 0.91,
        }
    }
    provider = MockLLMProvider(canned_responses=mock_data)
    generated_req = await provider.generate_structured(
        prompt="Parse client brief into Requirement model",
        response_model=Requirement,
    )
    print(f"  ✅ Provider Structured I/O: Generated {generated_req.id} (Status: {generated_req.status.value})")

    # 3. Test Golden DuckDB Dataset (Zero-Cost Local Warehouse)
    print("\n[3/3] Testing Golden DuckDB Dataset (evals/datasets/golden_ecommerce.duckdb)...")
    db_file = Path("evals/datasets/golden_ecommerce.duckdb")
    if not db_file.exists():
        print("  ❌ Dataset not found! Generating...")
        from evals.datasets.create_golden_dataset import create_golden_ecommerce_dataset
        create_golden_ecommerce_dataset(db_file)

    con = duckdb.connect(str(db_file), read_only=True)
    tables = con.execute("SHOW TABLES;").fetchall()
    print(f"  ✅ Discovered Tables in DuckDB: {[t[0] for t in tables]}")

    sample_query = """
        SELECT 
            p.category,
            COUNT(DISTINCT o.order_id) as total_orders,
            ROUND(SUM(oi.line_total), 2) as total_revenue
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.status = 'completed'
        GROUP BY p.category
        ORDER BY total_revenue DESC;
    """
    results = con.execute(sample_query).fetchall()
    print("  📊 Live Query Execution Results (SQL against DuckDB):")
    for row in results:
        print(f"     • Category: {row[0]:<12} | Completed Orders: {row[1]:<3} | Revenue: ${row[2]:,.2f}")
    con.close()

    print("\n" + "=" * 65)
    print("🎉 ALL PHASE 0 FOUNDATIONAL COMPONENTS ARE FULLY FUNCTIONAL!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_phase0_demo())
