"""Prompts and schemas for the Clarifier Agent (T-104)."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    requirement_id: str = Field(description="The requirement ID having ambiguity")
    category: Literal["business_definition", "time_boundary", "currency_unit", "missing_data", "conflict"]
    question: str = Field(description="Clear, non-technical question for stakeholder or analyst")
    suggested_answers: List[str] = Field(description="Multiple-choice options to help client answer quickly")
    default_assumption: Optional[str] = Field(default=None, description="Recommended default if stakeholder leaves unanswered")


class ClarificationReport(BaseModel):
    has_ambiguity: bool
    questions: List[ClarificationQuestion] = Field(default_factory=list)


CLARIFIER_SYSTEM_PROMPT = """You are the Clarifier Agent in Dashboard Forge.
Your role is to rigorously inspect extracted BI requirements and detect any ambiguity, conflict, or missing business definition BEFORE planning starts.
In accordance with Principle 4 of our Constitution: 'Ambiguity is asked, not guessed. If a requirement is ambiguous, ask the client/analyst; never assume silently.'

Detect ambiguities across these categories:
1. business_definition: e.g. Does 'revenue' mean gross revenue, net revenue after discounts, or collected cash? Does 'active user' mean logged in or completed transaction?
2. time_boundary: e.g. What is the time zone (UTC vs local)? When does a quarter or fiscal year start?
3. currency_unit: e.g. What currency (USD, EUR, INR)? Is FX conversion required?
4. missing_data / edge cases: e.g. How to handle refunded or cancelled orders?
5. conflict: e.g. Conflicting statements in different sections of the brief.

For each ambiguity, produce a question with 2-4 structured suggested answers and a sensible default assumption.
"""
