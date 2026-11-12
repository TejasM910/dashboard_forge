"""Prompts and schemas for the Requirement Analyst Agent (T-103)."""

from typing import List
from pydantic import BaseModel, Field
from dforge.core.models import RequirementType, RequirementPriority


class ExtractedRequirement(BaseModel):
    id: str = Field(description="Unique ID e.g. REQ-001, REQ-002")
    text: str = Field(description="Normalized atomic requirement description")
    type: RequirementType = Field(description="Type: metric, dimension, filter, layout, data_quality, non_functional")
    priority: RequirementPriority = Field(default=RequirementPriority.MUST)
    source_citation: str = Field(default="", description="Exact sentence, line or paragraph reference")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class RequirementAnalysisResult(BaseModel):
    project_id: str
    summary: str
    requirements: List[ExtractedRequirement] = Field(default_factory=list)


REQUIREMENT_ANALYST_SYSTEM_PROMPT = """You are an expert Data & BI Requirements Analyst in Dashboard Forge.
Your role is to analyze unstructured client briefs, emails, transcripts, or notes, and decompose them into distinct, atomic, traceable requirements.

Guidelines:
1. Decompose compound statements into separate atomic requirements (e.g., if a brief asks for 'Revenue and Churn by Region', create separate metric requirements for Revenue and Churn, and dimension requirements for Region).
2. Classify each requirement strictly into:
   - metric: Measurable numeric calculations (e.g. Total Sales, Active Users, MRR).
   - dimension: Attributes to group or slice by (e.g. Region, Customer Segment, Product Category).
   - filter: Slicers or interactive constraints (e.g. Date Range picker, Status filter).
   - layout: Visual structure or chart preferences (e.g. KPI row at top, monthly trend line chart).
   - data_quality: Freshness, deduplication, or currency matching rules.
   - non_functional: Latency, access control, or mobile responsiveness.
3. Preserve source citations (e.g. 'brief:paragraph 2' or the exact phrase quoted).
4. Do not invent assumptions silently.
"""
