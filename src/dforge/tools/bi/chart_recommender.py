"""Deterministic chart recommendations from metric dimensionality and profiles."""


from pydantic import BaseModel

from dforge.core.models import MetricDefinition, WidgetType
from dforge.tools.profiling.profiler import TableProfile


class ChartRecommendation(BaseModel):
    chart_type: WidgetType
    dimensions: list[str]
    time_dimension: str | None = None
    rationale: str


class ChartRecommender:
    """Recommend supported visualizations without asking an LLM to choose chart semantics."""

    LOW_CARDINALITY_LIMIT = 20

    @classmethod
    def recommend(
        cls,
        metric: MetricDefinition,
        dimensions: list[str] | None = None,
        time_dimension: str | None = None,
        profiles: list[TableProfile] | None = None,
    ) -> ChartRecommendation:
        selected_dimensions = list(dict.fromkeys(dimensions if dimensions is not None else metric.dimensions))
        selected_time_dimension = time_dimension or metric.time_dimension
        if selected_time_dimension in selected_dimensions:
            selected_dimensions.remove(selected_time_dimension)

        if selected_time_dimension:
            return ChartRecommendation(
                chart_type=WidgetType.LINE,
                dimensions=selected_dimensions,
                time_dimension=selected_time_dimension,
                rationale=f"Use a line chart to show {metric.label} over {selected_time_dimension}.",
            )

        if not selected_dimensions:
            return ChartRecommendation(
                chart_type=WidgetType.KPI_CARD,
                dimensions=[],
                rationale=f"Show {metric.label} as a single aggregate value.",
            )

        cardinalities = [
            cls._distinct_count(dimension, profiles)
            for dimension in selected_dimensions
        ]
        if len(selected_dimensions) == 1:
            if cardinalities[0] is not None and cardinalities[0] > cls.LOW_CARDINALITY_LIMIT:
                return ChartRecommendation(
                    chart_type=WidgetType.TABLE,
                    dimensions=selected_dimensions,
                    rationale=(
                        f"{selected_dimensions[0]} has high cardinality; a table avoids an "
                        "overcrowded categorical chart."
                    ),
                )
            return ChartRecommendation(
                chart_type=WidgetType.BAR,
                dimensions=selected_dimensions,
                rationale=f"Compare {metric.label} across {selected_dimensions[0]}.",
            )

        if len(selected_dimensions) == 2 and all(
            count is None or count <= cls.LOW_CARDINALITY_LIMIT for count in cardinalities
        ):
            return ChartRecommendation(
                chart_type=WidgetType.HEATMAP,
                dimensions=selected_dimensions,
                rationale="Use a heatmap to compare a metric across two categorical dimensions.",
            )

        return ChartRecommendation(
            chart_type=WidgetType.TABLE,
            dimensions=selected_dimensions,
            rationale="Use a table for multiple or high-cardinality dimensions.",
        )

    @staticmethod
    def _distinct_count(dimension: str, profiles: list[TableProfile] | None) -> int | None:
        if not profiles:
            return None
        table_name, column_name = ChartRecommender._split_field(dimension)
        matches = [
            column
            for profile in profiles
            if table_name is None or profile.table_name == table_name
            for column in profile.columns
            if column.name == column_name
        ]
        if len(matches) == 1:
            return matches[0].distinct_count
        return None

    @staticmethod
    def _split_field(field: str) -> tuple[str | None, str]:
        parts = field.split(".", maxsplit=1)
        return (parts[0], parts[1]) if len(parts) == 2 else (None, parts[0])
