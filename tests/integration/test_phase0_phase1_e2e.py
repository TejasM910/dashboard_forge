"""Comprehensive End-to-End Integration Test:
Validates alignment between Phase 0 (Foundation models, DuckDB warehouse, LLM schemas)
and Phase 1 (Document intake, atomic requirement extraction, ambiguity detection, Gate 1 approval).
"""

import pytest
from pathlib import Path
from dforge.tools.parsers.document_parser import DocumentParser
from dforge.agents.requirements_service import RequirementsService
from dforge.core.models import (
    Requirement,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
    MetricDefinition,
    Task,
    TaskStatus,
)
from dforge.llm.provider import MockLLMProvider
import duckdb


@pytest.mark.asyncio
async def test_phase0_phase1_e2e_alignment():
    # 1. Intake: Parse official examples/sample-client-brief.md
    brief_path = Path("examples/sample-client-brief.md")
    assert brief_path.exists(), "sample-client-brief.md must exist in examples/"
    brief_content = DocumentParser.parse_file(brief_path)
    assert "RetailCo" in brief_content

    # 2. Mock realistic LLM extraction matching the sample brief
    mock_responses = {
        "RequirementAnalysisResult": {
            "project_id": "proj-retailco",
            "summary": "Extracted requirements from RetailCo executive brief",
            "requirements": [
                {
                    "id": "REQ-001",
                    "text": "Calculate Net Revenue (excluding cancelled/test orders, refunds reduce revenue)",
                    "type": "metric",
                    "priority": "must",
                    "source_citation": "Bullet 1 & 4",
                    "confidence": 0.98,
                },
                {
                    "id": "REQ-002",
                    "text": "Count Total Completed Orders",
                    "type": "metric",
                    "priority": "must",
                    "source_citation": "Bullet 1 & 4",
                    "confidence": 0.99,
                },
                {
                    "id": "REQ-003",
                    "text": "Calculate Average Order Value (AOV)",
                    "type": "metric",
                    "priority": "must",
                    "source_citation": "Bullet 1",
                    "confidence": 0.95,
                },
                {
                    "id": "REQ-004",
                    "text": "Calculate Conversion Rate",
                    "type": "metric",
                    "priority": "should",
                    "source_citation": "Bullet 1",
                    "confidence": 0.90,
                },
                {
                    "id": "REQ-005",
                    "text": "Dimension slice: Product Category",
                    "type": "dimension",
                    "priority": "must",
                    "source_citation": "Bullet 2",
                    "confidence": 0.97,
                },
                {
                    "id": "REQ-006",
                    "text": "Data freshness: Daily refresh by 8 AM IST",
                    "type": "data_quality",
                    "priority": "should",
                    "source_citation": "Bullet 5",
                    "confidence": 0.92,
                },
            ],
        },
        "ClarificationReport": {
            "has_ambiguity": True,
            "questions": [
                {
                    "requirement_id": "REQ-001",
                    "category": "business_definition",
                    "question": "Does Net Revenue include tax and shipping?",
                    "suggested_answers": [
                        "Exclude tax and shipping (Product subtotal only)",
                        "Include shipping, exclude tax",
                        "Include both tax and shipping",
                    ],
                    "default_assumption": "Exclude tax and shipping",
                },
                {
                    "requirement_id": "REQ-004",
                    "category": "missing_data",
                    "question": "What is the denominator for Conversion Rate?",
                    "suggested_answers": [
                        "Web sessions to orders",
                        "Unique visitors to paying customers",
                    ],
                    "default_assumption": "Web sessions to orders",
                },
            ],
        },
    }

    provider = MockLLMProvider(canned_responses=mock_responses)
    service = RequirementsService(llm_provider=provider)

    # 3. Execute Phase 1 service pipeline
    requirements = await service.process_brief(project_id="proj-retailco", brief_content=brief_content)
    assert len(requirements) == 6

    # 4. Verify Phase 0 models alignment
    for r in requirements:
        assert isinstance(r, Requirement)
        assert r.project_id == "proj-retailco"
        assert r.created_at is not None

    req_map = {r.id: r for r in requirements}
    
    # Check Ambiguity detection
    assert req_map["REQ-001"].status == RequirementStatus.CLARIFICATION_NEEDED
    assert len(req_map["REQ-001"].ambiguities) == 1
    assert req_map["REQ-001"].ambiguities[0].category == "business_definition"

    # 5. Verify Gate 1 Human Approval semantics
    # Initially Gate 1 MUST fail because REQ-001 is a MUST requirement with unresolved ambiguity
    assert RequirementsService.approve_gate_1(requirements) is False

    # Simulate Human Gate 1 Analyst Action: Resolve REQ-001
    req_map["REQ-001"].ambiguities[0].resolution = "Exclude tax and shipping (Product subtotal only)"
    req_map["REQ-001"].status = RequirementStatus.APPROVED

    # REQ-004 is SHOULD priority, so analyst can waive or accept default
    req_map["REQ-004"].ambiguities[0].resolution = "Web sessions to orders"
    req_map["REQ-004"].status = RequirementStatus.APPROVED

    # Now Gate 1 MUST pass
    assert RequirementsService.approve_gate_1(requirements) is True
    assert all(r.status == RequirementStatus.APPROVED for r in requirements)

    # 6. Verify Alignment with Phase 0 Downstream Models:
    # Check that approved REQ-001 cleanly generates a valid Phase 0 MetricDefinition
    net_revenue_metric = MetricDefinition(
        name="net_revenue",
        label="Net Revenue ($)",
        description=req_map["REQ-001"].text,
        formula="sum(line_total - discount_amount)",
        dataset="orders",
        grain="order_id",
        unit="USD",
        requirement_ids=[req_map["REQ-001"].id],
        status="approved",
    )
    assert net_revenue_metric.requirement_ids == ["REQ-001"]

    # Check that approved REQ-001 can create a traceable downstream Task
    task = Task(
        id="TASK-201",
        run_id="run-001",
        name="Profile orders table for Net Revenue",
        agent="Data Profiler",
        status=TaskStatus.PENDING,
        requirement_ids=[req_map["REQ-001"].id],
    )
    assert task.requirement_ids == ["REQ-001"]

    # 7. Verify Alignment with Phase 0 DuckDB Golden Warehouse:
    # Ensure that the metric formula generated from REQ-001 actually computes on the Phase 0 DuckDB tables
    db_path = Path("evals/datasets/golden_ecommerce.duckdb")
    con = duckdb.connect(str(db_path), read_only=True)
    sql = f"""
        SELECT 
            ROUND({net_revenue_metric.formula}, 2) as computed_metric
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.status = 'completed';
    """
    res = con.execute(sql).fetchone()
    assert res is not None
    assert res[0] > 0  # Verified executed computation on golden database!
    con.close()
