"""Shared contracts for BI publication adapters."""

from collections.abc import Sequence
from typing import Any, Protocol

import pandas as pd
from pydantic import BaseModel, Field

from dforge.core.models import DashboardSpec


class BIValidationIssue(BaseModel):
    code: str
    message: str
    path: str


class SupersetDatasetRef(BaseModel):
    """A metric-to-Superset dataset binding required to publish a chart."""

    metric_name: str
    metric_label: str
    metric_expression: str
    datasource_id: int | None = None
    datasource_type: str = "table"
    database_id: int | None = None
    schema_name: str | None = None
    table_name: str | None = None
    columns: list[str] = Field(default_factory=list)


class PublishedDashboardRef(BaseModel):
    dashboard_id: int
    dashboard_url: str
    page_ids: list[str] = Field(default_factory=list)
    chart_ids: list[int] = Field(default_factory=list)
    widget_chart_ids: dict[str, int] = Field(default_factory=dict)
    widget_queries: dict[str, dict[str, Any]] = Field(default_factory=dict)


class BIAdapter(Protocol):
    def validate(
        self, spec: DashboardSpec, datasets: Sequence[SupersetDatasetRef]
    ) -> list[BIValidationIssue]: ...

    def publish(
        self, spec: DashboardSpec, datasets: Sequence[SupersetDatasetRef]
    ) -> PublishedDashboardRef: ...

    def update(
        self,
        published_ref: PublishedDashboardRef,
        spec: DashboardSpec,
        datasets: Sequence[SupersetDatasetRef],
    ) -> PublishedDashboardRef: ...

    def fetch_widget_data(
        self,
        published_ref: PublishedDashboardRef,
        widget_id: str,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame: ...

    def screenshot(self, published_ref: PublishedDashboardRef, page_id: str) -> bytes: ...
