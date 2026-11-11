"""Core Pydantic models for Dashboard Forge as defined in specs/05-data-models.md."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


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
    dimensions: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    unit: str = Field(default="count", description="currency, count, percent, seconds...")
    requirement_ids: List[str] = Field(default_factory=list)
    status: Literal["draft", "approved", "rejected"] = "draft"
    version: int = 1


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
    id: str
    title: str
    type: WidgetType
    metric: str
    dimensions: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    time_grain: Optional[str] = None
    width: int = Field(default=6, ge=1, le=12, description="12-column grid system")
    requirement_ids: List[str] = Field(default_factory=list)


class FilterSpec(BaseModel):
    id: str
    label: str
    column: str
    type: Literal["select", "date_range", "multi_select", "search"]
    default_value: Optional[Any] = None


class DashboardPage(BaseModel):
    id: str
    title: str
    widgets: List[WidgetSpec] = Field(default_factory=list)


class DashboardSpec(BaseModel):
    id: str
    title: str
    description: str
    project_id: str
    global_filters: List[FilterSpec] = Field(default_factory=list)
    pages: List[DashboardPage] = Field(default_factory=list)
    theme: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1


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
