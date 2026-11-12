"""End-to-end Pipeline Service orchestrating Intake -> Extraction -> Clarification -> Gate 1 Approval."""

from typing import List, Optional
from dforge.core.models import (
    Requirement,
    RequirementPriority,
    RequirementStatus,
    Ambiguity,
)
from dforge.llm.provider import BaseLLMProvider
from dforge.tools.parsers.document_parser import DocumentParser
from dforge.agents.requirement_analyst import (
    RequirementAnalysisResult,
    REQUIREMENT_ANALYST_SYSTEM_PROMPT,
)
from dforge.agents.clarifier import (
    ClarificationReport,
    CLARIFIER_SYSTEM_PROMPT,
)


class RequirementsService:
    """Manages Phase 1 intake, extraction, clarification, and Gate 1 state."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def process_brief(self, project_id: str, brief_content: str) -> List[Requirement]:
        """Ingest text brief, run Requirement Analyst, run Clarifier, return structured Requirements."""
        clean_text = DocumentParser.parse_text(brief_content)

        # 1. Extraction via Requirement Analyst Agent
        extract_prompt = f"Analyze and extract all atomic requirements from this client brief:\n\n{clean_text}"
        analysis: RequirementAnalysisResult = await self.llm.generate_structured(
            prompt=extract_prompt,
            response_model=RequirementAnalysisResult,
            system_prompt=REQUIREMENT_ANALYST_SYSTEM_PROMPT,
        )

        requirements: List[Requirement] = []
        for item in analysis.requirements:
            req = Requirement(
                id=item.id,
                project_id=project_id,
                text=item.text,
                type=item.type,
                priority=item.priority,
                status=RequirementStatus.DRAFT,
                source_citation=item.source_citation,
                confidence=item.confidence,
            )
            requirements.append(req)

        # 2. Inspect for Ambiguities via Clarifier Agent
        clarify_prompt = (
            f"Review these extracted requirements and identify ambiguities or missing definitions:\n\n"
            + "\n".join([f"- [{r.id}] ({r.type.value}): {r.text}" for r in requirements])
        )
        report: ClarificationReport = await self.llm.generate_structured(
            prompt=clarify_prompt,
            response_model=ClarificationReport,
            system_prompt=CLARIFIER_SYSTEM_PROMPT,
        )

        # Map ambiguities back to requirements
        req_map = {r.id: r for r in requirements}
        for q in report.questions:
            if q.requirement_id in req_map:
                target = req_map[q.requirement_id]
                target.status = RequirementStatus.CLARIFICATION_NEEDED
                target.ambiguities.append(
                    Ambiguity(
                        category=q.category,
                        question=q.question,
                        suggested_answers=q.suggested_answers,
                        resolution=None,
                    )
                )

        return requirements

    @staticmethod
    def approve_gate_1(requirements: List[Requirement]) -> bool:
        """Gate 1 Human Approval: returns True only if all Must requirements are resolved and approved."""
        for r in requirements:
            if r.priority == RequirementPriority.MUST and r.status == RequirementStatus.CLARIFICATION_NEEDED:
                return False
            # Approve valid drafts
            if r.status == RequirementStatus.DRAFT:
                r.status = RequirementStatus.APPROVED
        return True
