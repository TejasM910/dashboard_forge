"""Interactive verification demo for Phase 1: Requirements Engine & Gate 1."""

import asyncio
from dforge.agents.requirements_service import RequirementsService
from dforge.llm.provider import MockLLMProvider
from dforge.core.models import RequirementStatus


async def run_phase1_demo():
    print("=" * 70)
    print("📋 DASHBOARD FORGE — PHASE 1 REQUIREMENTS ENGINE & GATE 1 DEMO")
    print("=" * 70)

    # 1. Sample Client Brief Intake
    sample_brief = """
    Client: Acme Retail
    Need a Q3 Executive Sales Dashboard.
    Key requests:
    - Track total quarterly revenue and compare with target.
    - Measure customer churn rate.
    - Slicers for product category and customer region.
    - High priority: alert if data is delayed by more than 24 hours.
    """
    print("\n[1/4] Ingesting Sample Client Brief...")
    print(sample_brief.strip())

    # 2. Mock Agent outputs simulating LLM reasoning on the brief
    mock_responses = {
        "RequirementAnalysisResult": {
            "project_id": "proj-acme-sales",
            "summary": "Decomposed Acme Retail client brief into atomic requirements",
            "requirements": [
                {
                    "id": "REQ-001",
                    "text": "Calculate and display total quarterly revenue",
                    "type": "metric",
                    "priority": "must",
                    "source_citation": "line 4: 'Track total quarterly revenue'",
                    "confidence": 0.99,
                },
                {
                    "id": "REQ-002",
                    "text": "Calculate customer churn rate",
                    "type": "metric",
                    "priority": "must",
                    "source_citation": "line 5: 'Measure customer churn rate'",
                    "confidence": 0.95,
                },
                {
                    "id": "REQ-003",
                    "text": "Interactive filter for Product Category",
                    "type": "filter",
                    "priority": "should",
                    "source_citation": "line 6: 'Slicers for product category'",
                    "confidence": 0.98,
                },
                {
                    "id": "REQ-004",
                    "text": "Interactive filter for Customer Region",
                    "type": "filter",
                    "priority": "should",
                    "source_citation": "line 6: 'and customer region'",
                    "confidence": 0.98,
                },
                {
                    "id": "REQ-005",
                    "text": "Data freshness check: alert if max order timestamp is older than 24 hours",
                    "type": "data_quality",
                    "priority": "must",
                    "source_citation": "line 7: 'alert if data is delayed by more than 24 hours'",
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
                    "question": "Does quarterly revenue represent Gross Sales or Net Sales (after refunds/discounts)?",
                    "suggested_answers": [
                        "Net Sales (after subtracting refunds & discounts)",
                        "Gross Sales (total transaction volume)",
                    ],
                    "default_assumption": "Net Sales",
                },
                {
                    "requirement_id": "REQ-002",
                    "category": "business_definition",
                    "question": "How is 'churned customer' defined?",
                    "suggested_answers": [
                        "No completed purchase in the last 90 days",
                        "Explicit account cancellation or unsubscription",
                    ],
                    "default_assumption": "No completed purchase in 90 days",
                },
            ],
        },
    }

    provider = MockLLMProvider(canned_responses=mock_responses)
    service = RequirementsService(llm_provider=provider)

    print("\n[2/4] Running Requirement Analyst & Clarifier Agents...")
    requirements = await service.process_brief("proj-acme-sales", sample_brief)
    
    for r in requirements:
        status_symbol = "⚠️ [CLARIFY]" if r.status == RequirementStatus.CLARIFICATION_NEEDED else "✅ [READY]"
        print(f"  {status_symbol} {r.id} ({r.type.value:<12} | {r.priority.value}): {r.text}")
        for amb in r.ambiguities:
            print(f"       ❓ Ambiguity [{amb.category}]: {amb.question}")
            print(f"          Options: {', '.join(amb.suggested_answers)}")

    # 3. Gate 1 Evaluation
    print("\n[3/4] Testing Gate 1 (Human Approval Gate)...")
    passed_gate_1 = RequirementsService.approve_gate_1(requirements)
    print(f"  Gate 1 Result (Unresolved Must Requirements): {'PASSED' if passed_gate_1 else 'BLOCKED (As expected!)'}")

    # 4. Human Analyst Resolves Ambiguities
    print("\n[4/4] Simulating Human Analyst Resolving Ambiguities & Re-evaluating Gate 1...")
    req1 = next(r for r in requirements if r.id == "REQ-001")
    req1.ambiguities[0].resolution = "Net Sales (after subtracting refunds & discounts)"
    req1.status = RequirementStatus.APPROVED

    req2 = next(r for r in requirements if r.id == "REQ-002")
    req2.ambiguities[0].resolution = "No completed purchase in the last 90 days"
    req2.status = RequirementStatus.APPROVED

    passed_gate_1_final = RequirementsService.approve_gate_1(requirements)
    print(f"  Gate 1 Result (After Resolutions): {'PASSED ✅ - Ready for Task Planning & Data Profiling' if passed_gate_1_final else 'BLOCKED ❌'}")

    print("\n" + "=" * 70)
    print("🎉 PHASE 1 REQUIREMENTS ENGINE & GATE 1 FULLY FUNCTIONAL ($0 COST)!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_phase1_demo())
