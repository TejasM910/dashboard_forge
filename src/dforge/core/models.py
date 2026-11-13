"""Core Pydantic models for Dashboard Forge as defined in specs/05-data-models.md."""

import re
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# --- Requirement Models ---

class RequirementType(str, Enum):
    METRIC = "metric"
    DIMENSION = "dimension"
    FILTER = "filter"
    LAYOUT = "layout"
    DATA_QUALITY = "data_quality"
    NON_FUNCTIONAL = "non_functional"


class RequirementPriority(str, Enum):
    MUST = "must"
    SHOULD = "should"
    COULD = "could"


class RequirementStatus(str, Enum):
    DRAFT = "draft"
    CLARIFICATION_NEEDED = "clarification_needed"
    APPROVED = "approved"
    REJECTED = "rejected"


class Ambiguity(BaseModel):
    category: Literal["business_definition", "time_boundary", "currency_unit", "missing_data", "conflict"]
    question: str
    suggested_answers: List[str] = Field(default_factory=list)
    resolution: Optional[str] = None


class Requirement(BaseModel):
    id: str = Field(description="Unique stable ID e.g. REQ-001")
    project_id: str
    text: str
    type: RequirementType
    priority: RequirementPriority = RequirementPriority.MUST
    status: RequirementStatus = RequirementStatus.DRAFT
    source_citation: str = Field(default="", description="File, paragraph or sentence where requirement originated")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    ambiguities: List[Ambiguity] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Task / DAG Models ---

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task(BaseModel):
    id: str = Field(description="e.g. TASK-001")
    run_id: str
    name: str
    agent: str = Field(description="Agent or human responsible for executing the task")
    status: TaskStatus = TaskStatus.PENDING
    depends_on: List[str] = Field(default_factory=list)
    requirement_ids: List[str] = Field(default_factory=list)
    inputs_hash: Optional[str] = None
    outputs: Dict[str, Any] = Field(default_factory=dict)
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


# --- Semantic Layer / Metric Models ---

class MetricDefinition(BaseModel):
    name: str = Field(description="Unique metric key e.g. net_revenue")
    label: str = Field(description="Display label e.g. Net Revenue ($)")
    description: str
    type: Literal["simple", "derived", "ratio", "cumulative"] = "simple"
    formula: str = Field(description="SQL aggregation expression e.g. sum(amount - coalesce(refund, 0))")
    dataset: str = Field(description="Underlying table or view")
    grain: str = Field(description="Grain e.g. order_id, day, customer_id")
    time_dimension: Optional[str] = None
    dimensions: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    unit: str = Field(default="count", description="currency, count, percent, seconds...")
    format: Optional[str] = None
    requirement_ids: List[str] = Field(default_factory=list)
    status: Literal["draft", "approved", "rejected"] = "draft"
    version: int = 1

    @field_validator("format")
    @classmethod
    def validate_display_format(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not re.fullmatch(r"[#,0]+(?:\.[0#]+)?", value):
            raise ValueError("Metric format may contain only numeric grouping and decimal placeholders.")
        return value


# --- Dashboard Spec Models ---

class WidgetType(str, Enum):
    KPI_CARD = "kpi_card"
    LINE = "line"
    BAR = "bar"
    STACKED_BAR = "stacked_bar"
    PIE = "pie"
    TABLE = "table"
    HEATMAP = "heatmap"


class WidgetSpec(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    type: WidgetType
    metric: str = Field(min_length=1)
    dimensions: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    time_dimension: Optional[str] = None
    time_grain: Optional[str] = None
    width: int = Field(default=6, ge=1, le=12, description="12-column grid system")
    requirement_ids: List[str] = Field(default_factory=list)

    @field_validator("id", "title", "metric")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip()


class FilterSpec(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    column: str = Field(min_length=1)
    type: Literal["select", "date_range", "multi_select", "search"]
    default_value: Optional[Any] = None
    requirement_ids: List[str] = Field(default_factory=list)

    @field_validator("id", "label", "column")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def validate_default_value(self) -> "FilterSpec":
        if self.default_value is None:
            return self
        if self.type == "date_range":
            default = self.default_value
            if isinstance(default, str) and re.fullmatch(
                r"last_\d+_(days|weeks|months)", default
            ):
                return self
            if isinstance(default, (list, tuple)) and len(default) == 2:
                try:
                    date.fromisoformat(default[0])
                    date.fromisoformat(default[1])
                    return self
                except (TypeError, ValueError):
                    pass
            raise ValueError(
                "Date-range defaults must be a supported relative range or two ISO dates."
            )
        if self.type == "multi_select" and not isinstance(self.default_value, list):
            raise ValueError("Multi-select defaults must be a list.")
        if self.type == "search" and not isinstance(self.default_value, str):
            raise ValueError("Search defaults must be strings.")
        return self


class DashboardPage(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    widgets: List[WidgetSpec] = Field(min_length=1)

    @field_validator("id", "title")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip()


class DashboardSpec(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str
    project_id: str = Field(min_length=1)
    global_filters: List[FilterSpec] = Field(default_factory=list)
    pages: List[DashboardPage] = Field(min_length=1)
    theme: Dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=1, ge=1)

    @field_validator("id", "title", "project_id")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "DashboardSpec":
        def ensure_unique(values: List[str], label: str) -> None:
            if len(values) != len(set(values)):
                raise ValueError(f"{label} IDs must be unique")

        ensure_unique([page.id for page in self.pages], "Page")
        ensure_unique([item.id for item in self.global_filters], "Filter")
        for page in self.pages:
            ensure_unique([widget.id for widget in page.widgets], f"Widget on page '{page.id}'")
        for color_key in ("primary_color", "secondary_color", "background_color"):
            color = self.theme.get(color_key)
            if color is not None and (
                not isinstance(color, str)
                or not re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", color)
            ):
                raise ValueError(f"Dashboard theme '{color_key}' must be a 3- or 6-digit hex color.")
        return self


# --- Test & Verification Models ---

class TestType(str, Enum):
    __test__ = False
    SPEC_CHECK = "spec_check"
    SQL_STATIC = "sql_static"
    DATA_INTEGRITY = "data_integrity"
    RECONCILIATION = "reconciliation"
    GOLDEN = "golden"
    CONSISTENCY = "consistency"
    RENDERED = "rendered"


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class TestCase(BaseModel):
    __test__ = False  # Prevent pytest from treating this model as a test class
    id: str = Field(description="e.g. TC-001")
    requirement_id: str
    metric: Optional[str] = None
    type: TestType
    method: str = Field(default="reconciliation", description="sql_vs_duckdb, static_lint, row_count, etc.")
    params: Dict[str, Any] = Field(default_factory=dict)
    expected: Optional[Any] = None


class TestResult(BaseModel):
    __test__ = False  # Prevent pytest from treating this model as a test class
    test_id: str
    run_id: str
    status: TestStatus
    actual: Optional[Any] = None
    expected: Optional[Any] = None
    diff: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0
