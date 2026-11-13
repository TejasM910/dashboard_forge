"""Render validated DashboardSpecs in the local Streamlit review UI."""

import calendar
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import sqlglot
from sqlglot import exp

from dforge.agents.sql_generator import GeneratedQuery, SQLGenerator
from dforge.core.models import (
    DashboardSpec,
    FilterSpec,
    MetricDefinition,
    Requirement,
    WidgetSpec,
    WidgetType,
)
from dforge.tools.connectors.duckdb_connector import BaseConnector
from dforge.tools.profiling.inferrer import SchemaGraph
from dforge.tools.profiling.profiler import TableProfile
from dforge.tools.sql.sql_validator import SQLValidator
from dforge.validation.dashboard_spec_validator import DashboardSpecValidator


class StreamlitDashboardRenderer:
    """Render widgets from executed warehouse queries; never generate metric values."""

    def __init__(
        self,
        connector: BaseConnector,
        schema_graph: SchemaGraph,
        profiles: Sequence[TableProfile],
    ):
        self.connector = connector
        self.schema_graph = schema_graph
        self.profiles = list(profiles)
        self.sql_generator = SQLGenerator(schema_graph=schema_graph, dialect="duckdb")
        self.sql_validator = SQLValidator(connector=connector, dialect="duckdb")
        self.spec_validator = DashboardSpecValidator()

    def render(
        self,
        spec: DashboardSpec,
        metrics: Sequence[MetricDefinition],
        requirements: Sequence[Requirement],
    ) -> None:
        import streamlit as st

        validation = self.spec_validator.validate(
            spec=spec,
            metrics=metrics,
            requirements=requirements,
            profiles=self.profiles,
            schema_graph=self.schema_graph,
        )
        if not validation.is_valid:
            st.error("Dashboard preview blocked because the spec is invalid.")
            for issue in validation.issues:
                st.write(f"- `{issue.path}` — {issue.message}")
            return

        self._rendering_filters = spec.global_filters
        metric_by_name = {metric.name: metric for metric in metrics}
        theme = spec.theme
        st.title(spec.title)
        if spec.description:
            st.caption(spec.description)
        selected_filters = self._render_filters(st, spec.global_filters)

        for page in spec.pages:
            st.subheader(page.title)
            for row in self._layout_rows(page.widgets):
                columns = st.columns([widget.width for widget in row])
                for column, widget in zip(columns, row):
                    with column:
                        self._render_widget(
                            st,
                            widget,
                            metric_by_name[widget.metric],
                            selected_filters,
                            theme,
                        )

    def _render_filters(
        self,
        st: Any,
        filters: Sequence[FilterSpec],
    ) -> dict[str, Any]:
        selected: dict[str, Any] = {}
        if not filters:
            return selected
        st.subheader("Dashboard filters")
        columns = st.columns(min(len(filters), 4))
        for index, dashboard_filter in enumerate(filters):
            with columns[index % len(columns)]:
                if dashboard_filter.type == "date_range":
                    selected[dashboard_filter.id] = st.date_input(
                        dashboard_filter.label,
                        value=self._date_range_default(dashboard_filter),
                        key=f"dashboard_filter_{dashboard_filter.id}",
                    )
                elif dashboard_filter.type == "search":
                    selected[dashboard_filter.id] = st.text_input(
                        dashboard_filter.label,
                        value=str(dashboard_filter.default_value or ""),
                        key=f"dashboard_filter_{dashboard_filter.id}",
                    )
                else:
                    options = self._distinct_values(dashboard_filter.column)
                    if dashboard_filter.type == "multi_select":
                        default = dashboard_filter.default_value
                        if not isinstance(default, list):
                            default = []
                        selected[dashboard_filter.id] = st.multiselect(
                            dashboard_filter.label,
                            options,
                            default=[value for value in default if value in options],
                            key=f"dashboard_filter_{dashboard_filter.id}",
                        )
                    else:
                        choices = ["All", *options]
                        default_value = dashboard_filter.default_value
                        default_index = (
                            choices.index(default_value)
                            if default_value in choices
                            else 0
                        )
                        selected[dashboard_filter.id] = st.selectbox(
                            dashboard_filter.label,
                            choices,
                            index=default_index,
                            key=f"dashboard_filter_{dashboard_filter.id}",
                        )
        return selected

    def _distinct_values(self, field: str) -> list[Any]:
        table_name, column_name = self._resolve_field(field)
        table_sql = self._quote_identifier(table_name)
        column_sql = self._quote_identifier(column_name)
        _, rows = self.connector.execute_query(
            f"SELECT DISTINCT {column_sql} FROM {table_sql} "
            f"WHERE {column_sql} IS NOT NULL ORDER BY {column_sql} LIMIT 101"
        )
        return [row[0] for row in rows]

    def _date_range_default(self, dashboard_filter: FilterSpec) -> tuple[date, date] | None:
        default = dashboard_filter.default_value
        if isinstance(default, (list, tuple)) and len(default) == 2:
            return date.fromisoformat(default[0]), date.fromisoformat(default[1])
        if not isinstance(default, str):
            return None
        relative = re.fullmatch(r"last_(\d+)_(days|weeks|months)", default)
        if relative is None:
            return None
        table_name, column_name = self._resolve_field(dashboard_filter.column)
        column_profile = next(
            column
            for profile in self.profiles
            for column in profile.columns
            if column.name == column_name
            and profile.table_name == table_name
        )
        max_date = self._as_date(column_profile.max_value)
        if max_date is None:
            return None
        amount = int(relative.group(1))
        unit = relative.group(2)
        if unit == "days":
            start_date = max_date - timedelta(days=amount)
        elif unit == "weeks":
            start_date = max_date - timedelta(weeks=amount)
        else:
            month_index = max_date.year * 12 + max_date.month - 1 - amount
            year, month = divmod(month_index, 12)
            month += 1
            start_date = date(
                year,
                month,
                min(max_date.day, calendar.monthrange(year, month)[1]),
            )
        return start_date, max_date

    @staticmethod
    def _as_date(value: str | None) -> date | None:
        if value is None:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None

    def _render_widget(
        self,
        st: Any,
        widget: WidgetSpec,
        metric: MetricDefinition,
        selected_filters: Mapping[str, Any],
        theme: Mapping[str, Any],
    ) -> None:
        filter_ids = widget.filters or [
            item.id for item in self._current_spec_filters
        ]
        filters_by_id = {item.id: item for item in self._current_spec_filters}
        query = self.build_widget_query(
            metric=metric,
            widget=widget,
            filter_specs=[filters_by_id[filter_id] for filter_id in filter_ids if filter_id in filters_by_id],
            selected_filters=selected_filters,
        )
        validation = self.sql_validator.validate_sql(query.sql)
        if not validation.is_valid or not validation.dry_run_success:
            st.error(f"{widget.title}: generated query failed validation.")
            for error in validation.errors:
                st.caption(error)
            return
        columns, rows = self.connector.execute_query(query.sql)
        frame = pd.DataFrame(rows, columns=columns)
        if frame.empty:
            st.info(f"{widget.title}: no data for the current filters.")
            return
        if metric.name not in frame.columns:
            st.error(f"{widget.title}: query result is missing metric '{metric.name}'.")
            return
        try:
            frame[metric.name] = pd.to_numeric(frame[metric.name], errors="raise")
        except (TypeError, ValueError) as exc:
            st.error(f"{widget.title}: metric result is not numeric: {exc}")
            return
        st.markdown(f"**{widget.title}**")
        self._draw_chart(st, widget, metric, frame, theme)

    def build_widget_query(
        self,
        metric: MetricDefinition,
        widget: WidgetSpec,
        filter_specs: Sequence[FilterSpec],
        selected_filters: Mapping[str, Any],
    ) -> GeneratedQuery:
        query_filters = [
            condition
            for dashboard_filter in filter_specs
            if (
                condition := self._filter_expression(
                    dashboard_filter,
                    selected_filters.get(dashboard_filter.id),
                )
            )
        ]
        return self.sql_generator.generate_metric_query(
            metric=metric,
            dimensions=widget.dimensions,
            filters=query_filters,
            time_grain=widget.time_grain,
            time_dimension=widget.time_dimension,
        )

    @staticmethod
    def _draw_chart(
        st: Any,
        widget: WidgetSpec,
        metric: MetricDefinition,
        frame: pd.DataFrame,
        theme: Mapping[str, Any],
    ) -> None:
        primary_color = _theme_color(theme.get("primary_color"), "#4F46E5")
        if widget.type == WidgetType.KPI_CARD:
            st.metric(metric.label, format_metric_value(frame.iloc[0][metric.name], metric))
        elif widget.type == WidgetType.LINE:
            time_column = "time_period"
            if time_column not in frame.columns:
                st.error(f"{widget.title}: query did not return its time dimension.")
                return
            if widget.dimensions:
                dimension_columns = StreamlitDashboardRenderer._result_dimension_columns(
                    widget, frame, st
                )
                if dimension_columns is None:
                    return
                color = dimension_columns[0]
            else:
                color = primary_color
            st.line_chart(frame, x=time_column, y=metric.name, color=color)
        elif widget.type == WidgetType.BAR:
            dimension_columns = StreamlitDashboardRenderer._result_dimension_columns(
                widget, frame, st
            )
            if dimension_columns is None:
                return
            st.bar_chart(frame, x=dimension_columns[0], y=metric.name, color=primary_color)
        elif widget.type == WidgetType.STACKED_BAR:
            dimension_columns = StreamlitDashboardRenderer._result_dimension_columns(
                widget, frame, st
            )
            if dimension_columns is None:
                return
            st.bar_chart(
                frame,
                x=dimension_columns[0],
                y=metric.name,
                color=dimension_columns[1] if len(dimension_columns) > 1 else None,
                stack=True,
            )
        elif widget.type == WidgetType.PIE:
            dimension_columns = StreamlitDashboardRenderer._result_dimension_columns(
                widget, frame, st
            )
            if dimension_columns is None:
                return
            st.vega_lite_chart(
                frame,
                {
                    "mark": {"type": "arc", "innerRadius": 30},
                    "encoding": {
                        "theta": {"field": metric.name, "type": "quantitative"},
                        "color": {
                            "field": dimension_columns[0],
                            "type": "nominal",
                            "scale": {"range": [primary_color]},
                        },
                        "tooltip": [dimension_columns[0], metric.name],
                    },
                },
                use_container_width=True,
            )
        elif widget.type == WidgetType.HEATMAP:
            dimension_columns = StreamlitDashboardRenderer._result_dimension_columns(
                widget, frame, st
            )
            if dimension_columns is None:
                return
            st.vega_lite_chart(
                frame,
                {
                    "mark": "rect",
                    "encoding": {
                        "x": {"field": dimension_columns[0], "type": "ordinal"},
                        "y": {"field": dimension_columns[1], "type": "ordinal"},
                        "color": {
                            "field": metric.name,
                            "type": "quantitative",
                            "scale": {
                                "range": [
                                    theme.get("secondary_color", "#DBEAFE"),
                                    primary_color,
                                ]
                            },
                        },
                        "tooltip": [*dimension_columns, metric.name],
                    },
                    "config": {"range": {"category": [primary_color]}},
                },
                use_container_width=True,
            )
        else:
            st.dataframe(frame, use_container_width=True)

    @staticmethod
    def _result_dimension_columns(
        widget: WidgetSpec,
        frame: pd.DataFrame,
        st: Any,
    ) -> list[str] | None:
        columns = []
        for dimension in widget.dimensions:
            result_name = dimension.rsplit(".", maxsplit=1)[-1]
            if result_name not in frame.columns:
                st.error(
                    f"{widget.title}: query result is missing dimension "
                    f"'{dimension}' (expected column '{result_name}')."
                )
                return None
            columns.append(result_name)
        return columns

    def _filter_expression(self, dashboard_filter: FilterSpec, value: Any) -> str | None:
        if value is None or value == "" or value == "All" or value == []:
            return None
        table_name, column_name = self._resolve_field(dashboard_filter.column)
        column = exp.column(column_name, table=table_name)
        if dashboard_filter.type == "date_range":
            values = value if isinstance(value, tuple) else (value, value)
            if len(values) != 2 or values[0] is None or values[1] is None:
                return None
            condition: exp.Expr = exp.Between(
                this=column,
                low=exp.Literal.string(values[0].isoformat()),
                high=exp.Literal.string(values[1].isoformat()),
            )
        elif isinstance(value, list):
            condition = exp.In(this=column, expressions=[self._literal(item) for item in value])
        elif dashboard_filter.type == "search":
            condition = exp.Like(
                this=column,
                expression=exp.Literal.string(f"%{value}%"),
            )
        else:
            condition = exp.EQ(this=column, expression=self._literal(value))
        return condition.sql(dialect="duckdb")

    def _resolve_field(self, field: str) -> tuple[str, str]:
        parts = field.split(".", maxsplit=1)
        if len(parts) == 2:
            table_name, column_name = parts
            if not self._field_exists(table_name, column_name):
                raise ValueError(f"Unknown dashboard filter field '{field}'.")
            return table_name, column_name
        matches = [
            profile.table_name
            for profile in self.profiles
            if any(column.name == field for column in profile.columns)
        ]
        if len(matches) != 1:
            raise ValueError(f"Dashboard filter field '{field}' must resolve to one table.")
        return matches[0], field

    def _field_exists(self, table_name: str, column_name: str) -> bool:
        return any(
            profile.table_name == table_name
            and any(column.name == column_name for column in profile.columns)
            for profile in self.profiles
        )

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        parsed = sqlglot.parse_one(identifier, into=exp.Identifier)
        return parsed.sql(dialect="duckdb")

    @staticmethod
    def _literal(value: Any) -> exp.Expr:
        if isinstance(value, (date,)):
            return exp.Literal.string(value.isoformat())
        return exp.convert(value)

    @staticmethod
    def _layout_rows(widgets: Sequence[WidgetSpec]) -> list[list[WidgetSpec]]:
        rows: list[list[WidgetSpec]] = []
        current_row: list[WidgetSpec] = []
        width = 0
        for widget in widgets:
            if current_row and width + widget.width > 12:
                rows.append(current_row)
                current_row = []
                width = 0
            current_row.append(widget)
            width += widget.width
        if current_row:
            rows.append(current_row)
        return rows

    @property
    def _current_spec_filters(self) -> Sequence[FilterSpec]:
        return self._rendering_filters

    @_current_spec_filters.setter
    def _current_spec_filters(self, filters: Sequence[FilterSpec]) -> None:
        self._rendering_filters = list(filters)


def format_metric_value(value: Any, metric: MetricDefinition) -> str:
    """Format warehouse values with a conservative display rule based on metric metadata."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if metric.format:
        integer_pattern, _, decimal_pattern = metric.format.partition(".")
        decimals = len(decimal_pattern)
        grouping = "," in integer_pattern
    else:
        unit = metric.unit.lower()
        decimals = (
            2
            if unit in {"currency", "usd", "inr", "eur", "gbp", "percent", "percentage"}
            else 0 if number.is_integer() else 2
        )
        grouping = True
    format_string = f"{',' if grouping else ''}.{decimals}f"
    rendered = format(number, format_string)
    unit = metric.unit.lower()
    currency_symbols = {"usd": "$", "inr": "₹", "eur": "€", "gbp": "£"}
    if unit in currency_symbols:
        return f"{currency_symbols[unit]}{rendered}"
    if unit in {"percent", "percentage"}:
        return f"{rendered}%"
    return rendered


def _theme_color(value: Any, default: str) -> str:
    return default if value is None else str(value)
