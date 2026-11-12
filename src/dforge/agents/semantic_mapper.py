"""Semantic Mapper Agent: Maps business requirement terms to discovered tables and columns (T-205)."""

from typing import List
from pydantic import BaseModel, Field
from dforge.core.models import Requirement
from dforge.llm.provider import BaseLLMProvider
from dforge.tools.profiling.profiler import TableProfile
from dforge.tools.profiling.pii_masker import PIIMasker


class TermMapping(BaseModel):
    requirement_id: str
    term: str = Field(description="Business term extracted from the requirement e.g. 'Revenue' or 'Product Category'")
    target_table: str = Field(description="Mapped warehouse table e.g. orders, products")
    target_column: str = Field(description="Mapped column e.g. line_total, category")
    transformation: str = Field(default="exact", description="Aggregation or formula hint e.g. sum(line_total), exact")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class SemanticMappingPlan(BaseModel):
    project_id: str
    mappings: List[TermMapping] = Field(default_factory=list)


SEMANTIC_MAPPER_SYSTEM_PROMPT = """You are the Semantic Mapper Agent in Dashboard Forge.
Your responsibility is to map each approved business requirement term to the exact table and column in the client warehouse schema.

Guidelines:
1. Only map terms to tables and columns that exist in the provided schema catalog.
2. Note any necessary transformations or aggregations (e.g. sum, count distinct, case when).
3. If a metric requires multiple columns (e.g., net sales = line_total - discount_amount), provide clear mappings for the underlying terms.
4. Provide a confidence score between 0.0 and 1.0.
"""


class SemanticMapper:
    """Service that coordinates schema profiling summaries and LLM semantic mapping."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def generate_mapping_plan(
        self,
        project_id: str,
        requirements: List[Requirement],
        profiles: List[TableProfile],
    ) -> SemanticMappingPlan:
        # Sanitize profiles using PII masking before sending to LLM (Principle 8)
        sanitized_profiles = [PIIMasker.sanitize_profile_for_llm(p) for p in profiles]

        # Build schema catalog summary for prompt
        schema_summary = []
        for p in sanitized_profiles:
            cols = [f"{c.name} ({c.data_type})" for c in p.columns]
            schema_summary.append(f"Table '{p.table_name}' ({p.row_count} rows): {', '.join(cols)}")
        schema_text = "\n".join(schema_summary)

        req_summary = []
        for r in requirements:
            req_summary.append(f"- [{r.id}] ({r.type.value}): {r.text}")
        req_text = "\n".join(req_summary)

        prompt = (
            f"Map the following requirements to the warehouse schema:\n\n"
            f"--- REQUIREMENTS ---\n{req_text}\n\n"
            f"--- DISCOVERED WAREHOUSE SCHEMA ---\n{schema_text}"
        )

        return await self.llm.generate_structured(
            prompt=prompt,
            response_model=SemanticMappingPlan,
            system_prompt=SEMANTIC_MAPPER_SYSTEM_PROMPT,
        )
