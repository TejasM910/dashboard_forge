"""Cross-reference and schema validation for generated dashboard specifications."""

from collections import deque
from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from dforge.core.models import (
    DashboardSpec,
    MetricDefinition,
    Requirement,
    RequirementStatus,
    RequirementType,
    WidgetType,
)
from dforge.tools.profiling.inferrer import SchemaGraph
from dforge.tools.profiling.profiler import TableProfile


class DashboardValidationIssue(BaseModel):
    code: str
    message: str
    path: str


class DashboardValidationResult(BaseModel):
    is_valid: bool
    issues: list[DashboardValidationIssue]


class DashboardSpecValidator:
    """Check that a spec only references approved business objects and discovered fields."""

    def validate(
        self,
        spec: DashboardSpec,
        metrics: Sequence[MetricDefinition],
        requirements: Sequence[Requirement],
        profiles: Sequence[TableProfile],
        schema_graph: SchemaGraph | None = None,
    ) -> DashboardValidationResult:
        issues: list[DashboardValidationIssue] = []
        metric_by_name = {metric.name: metric for metric in metrics}
        requirement_by_id = {requirement.id: requirement for requirement in requirements}
        profile_by_table = {profile.table_name: profile for profile in profiles}
        filter_by_id = {item.id: item for item in spec.global_filters}

        for filter_index, dashboard_filter in enumerate(spec.global_filters):
            path = f"global_filters[{filter_index}]"
            if not self._field_exists(dashboard_filter.column, profile_by_table):
                self._add(
                    issues,
                    "unknown_filter_column",
                    f"Filter column '{dashboard_filter.column}' is not present in the discovered schema.",
                    f"{path}.column",
                )
            self._validate_requirement_refs(
                dashboard_filter.requirement_ids,
                requirement_by_id,
                spec.project_id,
                issues,
                f"{path}.requirement_ids",
            )

        for page_index, page in enumerate(spec.pages):
            for widget_index, widget in enumerate(page.widgets):
                path = f"pages[{page_index}].widgets[{widget_index}]"
                metric = metric_by_name.get(widget.metric)
                if metric is None:
                    self._add(
                        issues,
                        "unknown_metric",
                        f"Widget references unknown metric '{widget.metric}'.",
                        f"{path}.metric",
                    )
                    continue
                if metric.status != "approved":
                    self._add(
                        issues,
                        "metric_not_approved",
                        f"Metric '{metric.name}' must be approved before dashboard design.",
                        f"{path}.metric",
                    )
                if metric.dataset not in profile_by_table:
                    self._add(
                        issues,
                        "unknown_metric_dataset",
                        f"Metric dataset '{metric.dataset}' is not present in the discovered schema.",
                        f"{path}.metric",
                    )
                if widget.type == WidgetType.KPI_CARD and (
                    widget.dimensions or widget.time_dimension or widget.time_grain
                ):
                    self._add(
                        issues,
                        "kpi_has_dimensions",
                        "A KPI card cannot declare dimensions or a time grain.",
                        path,
                    )
                if widget.type == WidgetType.LINE and not (
                    widget.time_dimension or metric.time_dimension or widget.time_grain
                ):
                    self._add(
                        issues,
                        "line_missing_time_dimension",
                        "A line chart requires a time dimension or time grain.",
                        path,
                    )
                if widget.type == WidgetType.HEATMAP and len(widget.dimensions) != 2:
                    self._add(
                        issues,
                        "invalid_heatmap_dimensions",
                        "A heatmap requires exactly two categorical dimensions.",
                        f"{path}.dimensions",
                    )
                if widget.type == WidgetType.PIE and len(widget.dimensions) != 1:
                    self._add(
                        issues,
                        "invalid_pie_dimensions",
                        "A pie chart requires exactly one categorical dimension.",
                        f"{path}.dimensions",
                    )
                if widget.type == WidgetType.BAR and not widget.dimensions:
                    self._add(
                        issues,
                        "bar_missing_dimension",
                        "A bar chart requires at least one categorical dimension.",
                        f"{path}.dimensions",
                    )
                if widget.type == WidgetType.STACKED_BAR and len(widget.dimensions) != 2:
                    self._add(
                        issues,
                        "invalid_stacked_bar_dimensions",
                        "A stacked bar chart requires exactly two categorical dimensions.",
                        f"{path}.dimensions",
                    )

                for dimension in widget.dimensions:
                    if dimension not in metric.dimensions:
                        self._add(
                            issues,
                            "dimension_not_declared",
                            f"Dimension '{dimension}' is not declared by metric '{metric.name}'.",
                            f"{path}.dimensions",
                        )
                    if not self._field_exists(dimension, profile_by_table):
                        self._add(
                            issues,
                            "unknown_dimension",
                            f"Dimension '{dimension}' is not present in the discovered schema.",
                            f"{path}.dimensions",
                        )
                    elif schema_graph and not self._field_joins_to_dataset(
                        dimension, metric.dataset, schema_graph
                    ):
                        self._add(
                            issues,
                            "unconnected_dimension",
                            f"Dimension '{dimension}' has no inferred join path to dataset '{metric.dataset}'.",
                            f"{path}.dimensions",
                        )

                effective_time_dimension = widget.time_dimension or metric.time_dimension
                if effective_time_dimension:
                    if effective_time_dimension not in metric.dimensions and (
                        effective_time_dimension != metric.time_dimension
                    ):
                        self._add(
                            issues,
                            "time_dimension_not_declared",
                            f"Time dimension '{effective_time_dimension}' is not declared by metric '{metric.name}'.",
                            f"{path}.time_dimension",
                        )
                    if not self._field_exists(effective_time_dimension, profile_by_table):
                        self._add(
                            issues,
                            "unknown_time_dimension",
                            f"Time dimension '{effective_time_dimension}' is not present in the discovered schema.",
                            f"{path}.time_dimension",
                        )
                    elif schema_graph and not self._field_joins_to_dataset(
                        effective_time_dimension, metric.dataset, schema_graph
                    ):
                        self._add(
                            issues,
                            "unconnected_time_dimension",
                            f"Time dimension '{effective_time_dimension}' has no inferred join path "
                            f"to dataset '{metric.dataset}'.",
                            f"{path}.time_dimension",
                        )

                applicable_filter_ids = widget.filters or list(filter_by_id)
                for filter_id in applicable_filter_ids:
                    if filter_id not in filter_by_id:
                        self._add(
                            issues,
                            "unknown_filter",
                            f"Widget references unknown global filter '{filter_id}'.",
                            f"{path}.filters",
                        )
                    elif schema_graph and not self._field_joins_to_dataset(
                        filter_by_id[filter_id].column, metric.dataset, schema_graph
                    ):
                        self._add(
                            issues,
                            "unconnected_filter",
                            f"Filter column '{filter_by_id[filter_id].column}' has no inferred join path "
                            f"to dataset '{metric.dataset}'.",
                            f"{path}.filters",
                        )
                self._validate_requirement_refs(
                    widget.requirement_ids,
                    requirement_by_id,
                    spec.project_id,
                    issues,
                    f"{path}.requirement_ids",
                )
                if not widget.requirement_ids:
                    self._add(
                        issues,
                        "missing_requirement_trace",
                        "Every widget must trace to at least one approved requirement.",
                        f"{path}.requirement_ids",
                    )

        widget_requirement_ids = {
            requirement_id
            for page in spec.pages
            for widget in page.widgets
            for requirement_id in widget.requirement_ids
        }
        filter_requirement_ids = {
            requirement_id
            for dashboard_filter in spec.global_filters
            for requirement_id in dashboard_filter.requirement_ids
        }
        for requirement in requirements:
            if requirement.project_id != spec.project_id:
                continue
            if requirement.type in {RequirementType.METRIC, RequirementType.DIMENSION}:
                if requirement.id not in widget_requirement_ids:
                    self._add(
                        issues,
                        "unmapped_dashboard_requirement",
                        f"Requirement '{requirement.id}' is not represented by a widget.",
                        "pages",
                    )
            elif requirement.type == RequirementType.FILTER:
                if requirement.id not in filter_requirement_ids:
                    self._add(
                        issues,
                        "unmapped_filter_requirement",
                        f"Filter requirement '{requirement.id}' is not represented by a global filter.",
                        "global_filters",
                    )

        return DashboardValidationResult(is_valid=not issues, issues=issues)

    @staticmethod
    def _validate_requirement_refs(
        requirement_ids: Iterable[str],
        requirement_by_id: dict[str, Requirement],
        project_id: str,
        issues: list[DashboardValidationIssue],
        path: str,
    ) -> None:
        for requirement_id in requirement_ids:
            requirement = requirement_by_id.get(requirement_id)
            if requirement is None:
                DashboardSpecValidator._add(
                    issues,
                    "unknown_requirement",
                    f"Unknown requirement '{requirement_id}'.",
                    path,
                )
            elif requirement.project_id != project_id:
                DashboardSpecValidator._add(
                    issues,
                    "requirement_project_mismatch",
                    f"Requirement '{requirement_id}' belongs to another project.",
                    path,
                )
            elif requirement.status != RequirementStatus.APPROVED:
                DashboardSpecValidator._add(
                    issues,
                    "requirement_not_approved",
                    f"Requirement '{requirement_id}' must be approved.",
                    path,
                )

    @staticmethod
    def _field_exists(field: str, profiles: dict[str, TableProfile]) -> bool:
        table_name, column_name = DashboardSpecValidator._split_field(field)
        return any(
            (table_name is None or profile.table_name == table_name)
            and any(column.name == column_name for column in profile.columns)
            for profile in profiles.values()
        )

    @staticmethod
    def _field_joins_to_dataset(
        field: str,
        dataset: str,
        schema_graph: SchemaGraph,
    ) -> bool:
        table_name, _ = DashboardSpecValidator._split_field(field)
        if table_name is None or table_name == dataset:
            return True

        adjacency: dict[str, set[str]] = {}
        for relationship in schema_graph.relationships:
            adjacency.setdefault(relationship.from_table, set()).add(relationship.to_table)
            adjacency.setdefault(relationship.to_table, set()).add(relationship.from_table)

        pending = deque([dataset])
        visited = {dataset}
        while pending:
            current = pending.popleft()
            if current == table_name:
                return True
            for neighbor in adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        return False

    @staticmethod
    def _split_field(field: str) -> tuple[str | None, str]:
        parts = field.split(".", maxsplit=1)
        return (parts[0], parts[1]) if len(parts) == 2 else (None, parts[0])

    @staticmethod
    def _add(
        issues: list[DashboardValidationIssue],
        code: str,
        message: str,
        path: str,
    ) -> None:
        issues.append(DashboardValidationIssue(code=code, message=message, path=path))
