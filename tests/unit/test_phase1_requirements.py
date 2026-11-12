"""Unit tests verifying Phase 1 Requirements Engine, Agents, and Gate 1 (T-108)."""

import pytest
from dforge.tools.parsers.document_parser import DocumentParser
from dforge.agents.requirement_analyst import RequirementAnalysisResult
from dforge.agents.clarifier import ClarificationReport
from dforge.agents.requirements_service import RequirementsService
from dforge.core.models import (
    RequirementPriority,
    RequirementStatus,
    RequirementType,
)
from dforge.llm.provider import MockLLMProvider


def test_document_parser():
    raw_text = "   Client brief: track revenue and churn.   "
    clean = DocumentParser.parse_text(raw_text)
    assert clean == "Client brief: track revenue and churn."

    with pytest.raises(ValueError):
        DocumentParser.parse_text("   ")


@pytest.mark.asyncio
async def test_requirements_service_pipeline():
    # Setup canned mock response simulating LLM extraction and clarification
    mock_responses = {
        "RequirementAnalysisResult": {
            "project_id": "proj-sales",
            "summary": "Extracted requirements for sales dashboard",
            "requirements": [
                {
                    "id": "REQ-001",
                    "text": "Display total quarterly revenue",
                    "type": "metric",
                    "priority": "must",
                    "source_citation": "brief.md: line 3",
                    "confidence": 0.98,
                },
                {
                    "id": "REQ-002",
                    "text": "Filter by Region",
                    "type": "filter",
                    "priority": "should",
                    "source_citation": "brief.md: line 5",
                    "confidence": 0.95,
                },
            ],
        },
        "ClarificationReport": {
            "has_ambiguity": True,
            "questions": [
                {
                    "requirement_id": "REQ-001",
                    "category": "business_definition",
                    "question": "Does revenue refer to Gross Revenue or Net Revenue after refunds?",
                    "suggested_answers": [
                        "Net Revenue (after refunds & discounts)",
                        "Gross Revenue",
                        "Cash collections",
                    ],
                    "default_assumption": "Net Revenue",
                }
            ],
        },
    }

    provider = MockLLMProvider(canned_responses=mock_responses)
    service = RequirementsService(llm_provider=provider)

    sample_brief = "We need a dashboard for quarterly revenue and filtering by region."
    requirements = await service.process_brief(project_id="proj-sales", brief_content=sample_brief)

    assert len(requirements) == 2
    req1 = next(r for r in requirements if r.id == "REQ-001")
    req2 = next(r for r in requirements if r.id == "REQ-002")

    assert req1.type == RequirementType.METRIC
    assert req1.status == RequirementStatus.CLARIFICATION_NEEDED
    assert len(req1.ambiguities) == 1
    assert req1.ambiguities[0].category == "business_definition"

    assert req2.type == RequirementType.FILTER
    assert req2.status == RequirementStatus.DRAFT

    # Gate 1 should block approval while REQ-001 has unresolved ambiguity
    approved_initially = RequirementsService.approve_gate_1(requirements)
    assert approved_initially is False

    # Simulate human analyst resolving ambiguity at Gate 1
    req1.ambiguities[0].resolution = "Net Revenue (after refunds & discounts)"
    req1.text = "Display total quarterly net revenue (excluding refunds & discounts)"
    req1.status = RequirementStatus.APPROVED

    # Now Gate 1 should pass
    approved_after_resolution = RequirementsService.approve_gate_1(requirements)
    assert approved_after_resolution is True
    assert req1.status == RequirementStatus.APPROVED
    assert req2.status == RequirementStatus.APPROVED
