"""Unit tests verifying Phase 0 foundational models and mock LLM provider."""

import pytest
from dforge.core.models import (
    Requirement,
    RequirementType,
    RequirementPriority,
    RequirementStatus,
    MetricDefinition,
    DashboardSpec,
    WidgetSpec,
    WidgetType,
    TestCase,
    TestType,
)
from dforge.llm.provider import MockLLMProvider


def test_requirement_model_validation():
    req = Requirement(
        id="REQ-001",
        project_id="proj-sales",
        text="Display total net sales for 2025 by quarter",
        type=RequirementType.METRIC,
        priority=RequirementPriority.MUST,
        status=RequirementStatus.APPROVED,
        source_citation="brief.md:line 12",
        confidence=0.95,
    )
    assert req.id == "REQ-001"
    assert req.type == RequirementType.METRIC
    assert req.priority == RequirementPriority.MUST
    assert req.confidence == 0.95


def test_metric_definition_model():
    metric = MetricDefinition(
        name="net_sales",
        label="Net Sales",
        description="Total revenue after discounts and refunds",
        formula="sum(line_total - coalesce(discount_amount, 0))",
        dataset="orders",
        grain="order_id",
        unit="USD",
        requirement_ids=["REQ-001"],
    )
    assert metric.name == "net_sales"
    assert metric.unit == "USD"
    assert "REQ-001" in metric.requirement_ids


@pytest.mark.asyncio
async def test_mock_llm_provider():
    mock_data = {
        "Requirement": {
            "id": "REQ-002",
            "project_id": "proj-retention",
            "text": "Track monthly churn rate",
            "type": "metric",
            "priority": "must",
            "status": "draft",
        }
    }
    provider = MockLLMProvider(canned_responses=mock_data)
    result = await provider.generate_structured(
        prompt="Extract requirement",
        response_model=Requirement,
    )
    assert result.id == "REQ-002"
    assert result.type == RequirementType.METRIC
