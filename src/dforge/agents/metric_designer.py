"""Metric Designer Agent: Formulates atomic metric definitions with self-critique (T-302 & FR-40)."""

from typing import List, Optional
from pydantic import BaseModel, Field
from dforge.core.models import MetricDefinition, Requirement
from dforge.llm.provider import BaseLLMProvider
from dforge.agents.semantic_mapper import SemanticMappingPlan


class MetricDesignerOutput(BaseModel):
    metrics: List[MetricDefinition] = Field(default_factory=list)
    self_critique: Optional[str] = Field(
        default=None,
        description="Self-critique checking for double counting, null-handling, and grain alignment.",
    )


METRIC_DESIGNER_SYSTEM_PROMPT = """You are the Metric Designer Agent in Dashboard Forge.
Your role is to formulate declarative MetricDefinitions based on approved requirements and semantic mappings.

Principles:
1. Every metric must have a stable unique name (snake_case), label, description, dataset, grain, unit, and SQL formula.
2. Formulate aggregation expressions using standard ANSI/DuckDB SQL (e.g. sum, count, avg, round).
3. Always include null-safe handling (e.g. coalesce(discount, 0)).
4. Perform a rigorous self-critique: ensure formulas avoid fan-out join multiplication, verify appropriate grain, and confirm every metric maps back to requirement_ids.
"""


class MetricDesigner:
    """Agent service that creates and validates MetricDefinitions."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def design_metrics(
        self,
        requirements: List[Requirement],
        mapping_plan: SemanticMappingPlan,
    ) -> MetricDesignerOutput:
        req_lines = [f"- [{r.id}]: {r.text} (Type: {r.type.value})" for r in requirements]
        mapping_lines = [
            f"- [{m.requirement_id}] '{m.term}' -> {m.target_table}.{m.target_column} ({m.transformation})"
            for m in mapping_plan.mappings
        ]

        prompt = (
            f"Generate formal MetricDefinitions for the following approved requirements:\n\n"
            f"--- APPROVED REQUIREMENTS ---\n" + "\n".join(req_lines) + "\n\n"
            f"--- SEMANTIC MAPPINGS ---\n" + "\n".join(mapping_lines)
        )

        return await self.llm.generate_structured(
            prompt=prompt,
            response_model=MetricDesignerOutput,
            system_prompt=METRIC_DESIGNER_SYSTEM_PROMPT,
        )
