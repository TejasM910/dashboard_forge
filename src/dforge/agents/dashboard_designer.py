"""Deterministic Dashboard Designer for approved requirements and metrics (T-403)."""

import re
from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from dforge.core.models import (
    DashboardPage,
    DashboardSpec,
    FilterSpec,
    MetricDefinition,
    Requirement,
    RequirementStatus,
    RequirementType,
    WidgetSpec,
    WidgetType,
)
from dforge.tools.bi.chart_recommender import ChartRecommender
from dforge.tools.profiling.inferrer import SchemaGraph
from dforge.tools.profiling.profiler import TableProfile
from dforge.tools.sql.sql_validator import SQLValidationResult
from dforge.validation.dashboard_spec_validator import DashboardSpecValidator


class DimensionBinding(BaseModel):
    metric_name: str
    dimension: str


class DashboardDesigner:
    """Build a traceable spec only from approved inputs and dry-run validated metrics."""

    def __init__(
        self,
        chart_recommender: ChartRecommender | None = None,
        spec_validator: DashboardSpecValidator | None = None,
    ):
        self.chart_recommender = chart_recommender or ChartRecommender()
        self.spec_validator = spec_validator or DashboardSpecValidator()

    def design_dashboard(
        self,
        project_id: str,
        title: str,
        requirements: Sequence[Requirement],
        metrics: Sequence[MetricDefinition],
        schema_graph: SchemaGraph,
        profiles: Sequence[TableProfile],
        validated_queries: Mapping[str, SQLValidationResult],
        dimension_mappings: Mapping[str, DimensionBinding] | None = None,
        filter_mappings: Mapping[str, FilterSpec] | None = None,
        dashboard_id: str | None = None,
    ) -> DashboardSpec:
        if not project_id.strip() or not title.strip():
            raise ValueError("Dashboard project_id and title must not be blank.")
        if not requirements:
            raise ValueError("At least one approved requirement is needed to design a dashboard.")
        if not metrics:
            raise ValueError("At least one approved metric is needed to design a dashboard.")

        requirement_by_id = {requirement.id: requirement for requirement in requirements}
        if len(requirement_by_id) != len(requirements):
            raise ValueError("Requirement IDs must be unique.")
        for requirement in requirements:
            if requirement.project_id != project_id:
                raise ValueError(f"Requirement '{requirement.id}' belongs to another project.")
            if requirement.status != RequirementStatus.APPROVED:
                raise ValueError(f"Requirement '{requirement.id}' is not approved.")

        metric_by_name = {metric.name: metric for metric in metrics}
        if len(metric_by_name) != len(metrics):
            raise ValueError("Metric names must be unique.")
        for metric in metrics:
            if metric.status != "approved":
                raise ValueError(f"Metric '{metric.name}' is not approved.")
            for requirement_id in metric.requirement_ids:
                linked_requirement = requirement_by_id.get(requirement_id)
                if linked_requirement is None:
                    raise ValueError(
                        f"Metric '{metric.name}' references unknown requirement '{requirement_id}'."
                    )

        dimension_requirements = [
            requirement
            for requirement in requirements
            if requirement.type == RequirementType.DIMENSION
        ]
        mapped_dimensions = dict(dimension_mappings or {})
        missing_dimension_mappings = [
            requirement.id
            for requirement in dimension_requirements
            if requirement.id not in mapped_dimensions
        ]
        if missing_dimension_mappings:
            raise ValueError(
                "Dimension requirements need explicit mappings to approved metric dimensions: "
                + ", ".join(missing_dimension_mappings)
            )
        dimension_requirement_ids_by_metric: dict[str, list[str]] = {}
        for requirement in dimension_requirements:
            binding = mapped_dimensions[requirement.id]
            bound_metric = metric_by_name.get(binding.metric_name)
            if bound_metric is None:
                raise ValueError(
                    f"Dimension requirement '{requirement.id}' maps to unknown metric "
                    f"'{binding.metric_name}'."
                )
            if binding.dimension not in bound_metric.dimensions:
                raise ValueError(
                    f"Dimension '{binding.dimension}' is not approved on metric "
                    f"'{bound_metric.name}'."
                )
            if requirement.id not in bound_metric.requirement_ids:
                raise ValueError(
                    f"Metric '{bound_metric.name}' must trace to dimension requirement "
                    f"'{requirement.id}'."
                )
            dimension_requirement_ids_by_metric.setdefault(bound_metric.name, []).append(
                requirement.id
            )

        for metric_name in metric_by_name:
            validation = validated_queries.get(metric_name)
            if validation is None:
                raise ValueError(f"Metric '{metric_name}' has no validated SQL artifact.")
            if not validation.is_valid or not validation.dry_run_success:
                raise ValueError(
                    f"Metric '{metric_name}' SQL must pass static checks and a warehouse dry-run."
                )

        filter_requirements = [
            requirement
            for requirement in requirements
            if requirement.type == RequirementType.FILTER
        ]
        mapped_filters = dict(filter_mappings or {})
        missing_filter_mappings = [
            requirement.id
            for requirement in filter_requirements
            if requirement.id not in mapped_filters
        ]
        if missing_filter_mappings:
            raise ValueError(
                "Filter requirements need explicit, analyst-confirmed field mappings: "
                + ", ".join(missing_filter_mappings)
            )
        filters = []
        for requirement in filter_requirements:
            mapped_filter = mapped_filters[requirement.id]
            requirement_ids = list(
                dict.fromkeys(mapped_filter.requirement_ids + [requirement.id])
            )
            filters.append(mapped_filter.model_copy(update={"requirement_ids": requirement_ids}))

        widgets = []
        widget_index = 1
        for metric in metrics:
            if not metric.requirement_ids:
                raise ValueError(
                    f"Metric '{metric.name}' must trace to at least one approved requirement."
                )
            widgets.append(
                WidgetSpec(
                    id=f"widget-{widget_index}",
                    title=metric.label,
                    type=WidgetType.KPI_CARD,
                    metric=metric.name,
                    width=3,
                    requirement_ids=metric.requirement_ids,
                )
            )
            widget_index += 1

            if metric.dimensions or metric.time_dimension:
                time_grain = self._requested_time_grain(metric, requirements)
                recommendation = self.chart_recommender.recommend(
                    metric=metric,
                    dimensions=metric.dimensions,
                    time_dimension=metric.time_dimension,
                    profiles=list(profiles),
                )
                chart_dimensions = list(recommendation.dimensions)
                chart_requirement_ids = list(
                    dict.fromkeys(
                        metric.requirement_ids
                        + dimension_requirement_ids_by_metric.get(metric.name, [])
                    )
                )
                widgets.append(
                    WidgetSpec(
                        id=f"widget-{widget_index}",
                        title=self._chart_title(metric, chart_dimensions, recommendation.time_dimension),
                        type=recommendation.chart_type,
                        metric=metric.name,
                        dimensions=chart_dimensions,
                        time_dimension=recommendation.time_dimension,
                        time_grain=time_grain,
                        width=6,
                        requirement_ids=chart_requirement_ids,
                    )
                )
                widget_index += 1

        dashboard = DashboardSpec(
            id=dashboard_id or self._slug(title),
            title=title.strip(),
            description="Generated from approved requirements and metrics.",
            project_id=project_id,
            global_filters=filters,
            pages=[DashboardPage(id="overview", title="Overview", widgets=widgets)],
        )
        result = self.spec_validator.validate(
            spec=dashboard,
            metrics=metrics,
            requirements=requirements,
            profiles=profiles,
            schema_graph=schema_graph,
        )
        if not result.is_valid:
            details = "; ".join(
                f"{issue.path}: {issue.message}" for issue in result.issues
            )
            raise ValueError(f"Generated DashboardSpec failed validation: {details}")
        return dashboard

    @staticmethod
    def _requested_time_grain(
        metric: MetricDefinition,
        requirements: Sequence[Requirement],
    ) -> str | None:
        linked_text = " ".join(
            requirement.text.lower()
            for requirement in requirements
            if requirement.id in metric.requirement_ids
        )
        for phrase, grain in (
            (r"\b(year|yearly|annual|annually)\b", "year"),
            (r"\b(quarter|quarterly)\b", "quarter"),
            (r"\b(month|monthly)\b", "month"),
            (r"\b(week|weekly)\b", "week"),
            (r"\b(day|daily)\b", "day"),
        ):
            if re.search(phrase, linked_text):
                return grain
        return None

    @staticmethod
    def _chart_title(
        metric: MetricDefinition,
        dimensions: Sequence[str],
        time_dimension: str | None,
    ) -> str:
        grouped_by = list(dimensions)
        if time_dimension:
            grouped_by.insert(0, time_dimension)
        if not grouped_by:
            return metric.label
        return f"{metric.label} by {', '.join(grouped_by)}"

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "dashboard"
