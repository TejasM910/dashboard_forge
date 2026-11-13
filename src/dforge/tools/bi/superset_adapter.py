"""Apache Superset REST API adapter for dashboard publication."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx
import pandas as pd
import sqlglot
from sqlglot import exp

from dforge.core.models import DashboardSpec, WidgetSpec, WidgetType
from dforge.tools.bi.adapter import (
    BIValidationIssue,
    PublishedDashboardRef,
    SupersetDatasetRef,
)


class BIAdapterError(RuntimeError):
    """Raised when a BI adapter operation fails."""


class SupersetBIAdapter:
    """Publish validated dashboard specs using Superset's REST API."""

    VIZ_TYPES = {
        WidgetType.KPI_CARD: "big_number_total",
        WidgetType.LINE: "echarts_timeseries_line",
        WidgetType.BAR: "dist_bar",
        WidgetType.STACKED_BAR: "echarts_timeseries_bar",
        WidgetType.PIE: "pie",
        WidgetType.TABLE: "table",
        WidgetType.HEATMAP: "heatmap_v2",
    }

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        access_token: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Superset base_url must use http:// or https://.")
        if not access_token and not (username and password):
            raise ValueError("Provide either an access_token or a username and password.")
        self.username = username
        self.password = password
        self.access_token = access_token
        self._csrf_token: str | None = None
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def validate(
        self,
        spec: DashboardSpec,
        datasets: Sequence[SupersetDatasetRef],
    ) -> list[BIValidationIssue]:
        dataset_by_metric = {dataset.metric_name: dataset for dataset in datasets}
        issues: list[BIValidationIssue] = []
        if len(dataset_by_metric) != len(datasets):
            issues.append(
                BIValidationIssue(
                    code="duplicate_dataset_binding",
                    message="Each metric must have exactly one Superset dataset binding.",
                    path="datasets",
                )
            )
        for page_index, page in enumerate(spec.pages):
            for widget_index, widget in enumerate(page.widgets):
                path = f"pages[{page_index}].widgets[{widget_index}]"
                if widget.metric not in dataset_by_metric:
                    issues.append(
                        BIValidationIssue(
                            code="missing_dataset_binding",
                            message=f"No Superset dataset binding for metric '{widget.metric}'.",
                            path=f"{path}.metric",
                        )
                    )
                if widget.type not in self.VIZ_TYPES:
                    issues.append(
                        BIValidationIssue(
                            code="unsupported_visualization",
                            message=f"Superset visualization for '{widget.type.value}' is unsupported.",
                            path=f"{path}.type",
                        )
                    )
        for dataset_index, dataset in enumerate(datasets):
            if dataset.datasource_id is None and not (
                dataset.database_id and dataset.table_name
            ):
                issues.append(
                    BIValidationIssue(
                        code="incomplete_dataset_binding",
                        message=(
                            "A dataset binding needs datasource_id or both database_id and table_name."
                        ),
                        path=f"datasets[{dataset_index}]",
                    )
                )
            if not dataset.metric_expression.strip():
                issues.append(
                    BIValidationIssue(
                        code="empty_metric_expression",
                        message="Metric expression must not be blank.",
                        path=f"datasets[{dataset_index}].metric_expression",
                    )
                )
            else:
                try:
                    expressions = sqlglot.parse(dataset.metric_expression, read="duckdb")
                    if len(expressions) != 1 or expressions[0] is None:
                        raise ValueError("Expected one SQL expression.")
                    forbidden = (
                        exp.Select,
                        exp.Subquery,
                        exp.Command,
                        exp.Insert,
                        exp.Update,
                        exp.Delete,
                        exp.Create,
                        exp.Drop,
                        exp.Alter,
                    )
                    if any(expressions[0].find(expression) for expression in forbidden):
                        raise ValueError("Only a scalar, read-only SQL expression is supported.")
                    allowed_functions = {
                        "ABS",
                        "AVG",
                        "COALESCE",
                        "COUNT",
                        "DATE_TRUNC",
                        "MAX",
                        "MIN",
                        "NULLIF",
                        "ROUND",
                        "SUM",
                    }
                    for function in expressions[0].find_all(exp.Func):
                        if function.sql_name().upper() not in allowed_functions:
                            raise ValueError(
                                f"Function '{function.sql_name()}' is not allowed in a metric."
                            )
                except (ValueError, sqlglot.errors.ParseError) as exc:
                    issues.append(
                        BIValidationIssue(
                            code="invalid_metric_expression",
                            message=f"Metric expression is invalid: {exc}",
                            path=f"datasets[{dataset_index}].metric_expression",
                        )
                    )
        for filter_index, dashboard_filter in enumerate(spec.global_filters):
            if not any(
                self._dataset_has_column(dataset, dashboard_filter.column)
                for dataset in datasets
            ):
                issues.append(
                    BIValidationIssue(
                        code="unbound_filter_column",
                        message=(
                            f"Filter column '{dashboard_filter.column}' is not declared in any "
                            "Superset dataset binding."
                        ),
                        path=f"global_filters[{filter_index}].column",
                    )
                )
        return issues

    def publish(
        self,
        spec: DashboardSpec,
        datasets: Sequence[SupersetDatasetRef],
    ) -> PublishedDashboardRef:
        issues = self.validate(spec, datasets)
        if issues:
            raise BIAdapterError(
                "Dashboard cannot be published: "
                + "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
            )
        datasource_by_metric = self._ensure_datasets(datasets)
        chart_ids: list[int] = []
        widget_chart_ids: dict[str, int] = {}
        widget_queries: dict[str, dict[str, Any]] = {}
        chart_positions: list[dict[str, Any]] = []

        dataset_by_metric = {dataset.metric_name: dataset for dataset in datasets}
        for page in spec.pages:
            for widget in page.widgets:
                dataset = dataset_by_metric[widget.metric]
                datasource = datasource_by_metric[widget.metric]
                chart_payload, query = self._chart_payload(widget, dataset, datasource)
                response = self._request("POST", "/api/v1/chart/", json=chart_payload)
                chart_id = self._response_id(response, "chart")
                chart_ids.append(chart_id)
                widget_chart_ids[widget.id] = chart_id
                widget_queries[widget.id] = query
                chart_positions.append(
                    {
                        "chart_id": chart_id,
                        "widget_id": widget.id,
                        "width": widget.width,
                        "page_id": page.id,
                        "page_title": page.title,
                    }
                )

        position_json = self._position_json(chart_positions)
        metadata = self._dashboard_metadata(spec, datasets, datasource_by_metric)
        dashboard_response = self._request(
            "POST",
            "/api/v1/dashboard/",
            json={
                "dashboard_title": spec.title,
                "slug": self._slug(spec.id),
                "published": True,
                "position_json": json.dumps(position_json),
                "json_metadata": json.dumps(metadata),
            },
        )
        dashboard_id = self._response_id(dashboard_response, "dashboard")
        return PublishedDashboardRef(
            dashboard_id=dashboard_id,
            dashboard_url=f"{self.base_url}/superset/dashboard/{dashboard_id}/",
            page_ids=[page.id for page in spec.pages],
            chart_ids=chart_ids,
            widget_chart_ids=widget_chart_ids,
            widget_queries=widget_queries,
        )

    def update(
        self,
        published_ref: PublishedDashboardRef,
        spec: DashboardSpec,
        datasets: Sequence[SupersetDatasetRef],
    ) -> PublishedDashboardRef:
        issues = self.validate(spec, datasets)
        if issues:
            raise BIAdapterError(
                "Dashboard cannot be updated: "
                + "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
            )
        datasource_by_metric = self._ensure_datasets(datasets)
        chart_ids: list[int] = []
        widget_chart_ids: dict[str, int] = {}
        widget_queries: dict[str, dict[str, Any]] = {}
        chart_positions: list[dict[str, Any]] = []
        dataset_by_metric = {dataset.metric_name: dataset for dataset in datasets}

        for page in spec.pages:
            for widget in page.widgets:
                dataset = dataset_by_metric[widget.metric]
                chart_payload, query = self._chart_payload(
                    widget, dataset, datasource_by_metric[widget.metric]
                )
                chart_response = self._request("POST", "/api/v1/chart/", json=chart_payload)
                chart_id = self._response_id(chart_response, "chart")
                chart_ids.append(chart_id)
                widget_chart_ids[widget.id] = chart_id
                widget_queries[widget.id] = query
                chart_positions.append(
                    {
                        "chart_id": chart_id,
                        "widget_id": widget.id,
                        "width": widget.width,
                        "page_id": page.id,
                        "page_title": page.title,
                    }
                )

        self._request(
            "PUT",
            f"/api/v1/dashboard/{published_ref.dashboard_id}",
            json={
                "dashboard_title": spec.title,
                "position_json": json.dumps(self._position_json(chart_positions)),
                "json_metadata": json.dumps(
                    self._dashboard_metadata(spec, datasets, datasource_by_metric)
                ),
                "published": True,
            },
        )
        return PublishedDashboardRef(
            dashboard_id=published_ref.dashboard_id,
            dashboard_url=published_ref.dashboard_url,
            page_ids=[page.id for page in spec.pages],
            chart_ids=chart_ids,
            widget_chart_ids=widget_chart_ids,
            widget_queries=widget_queries,
        )

    def fetch_widget_data(
        self,
        published_ref: PublishedDashboardRef,
        widget_id: str,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        query = published_ref.widget_queries.get(widget_id)
        if query is None:
            raise KeyError(f"Widget '{widget_id}' is not part of this published dashboard.")
        query_payload = dict(query)
        query_payload["filters"] = self._query_filters(filters or {})
        response = self._request(
            "POST",
            "/api/v1/chart/data",
            json={
                "datasource": query_payload.pop("datasource"),
                "queries": [query_payload],
                "result_format": "json",
                "result_type": "full",
            },
        )
        results = response.get("result")
        if not isinstance(results, list) or not results:
            raise BIAdapterError("Superset chart-data response did not contain a result set.")
        rows = results[0].get("data")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise BIAdapterError("Superset chart-data response returned an invalid data shape.")
        return pd.DataFrame(rows)

    def screenshot(self, published_ref: PublishedDashboardRef, page_id: str) -> bytes:
        if page_id not in published_ref.page_ids:
            raise ValueError(f"Unknown dashboard page '{page_id}'.")
        if len(published_ref.page_ids) > 1:
            raise BIAdapterError(
                "Superset's thumbnail endpoint does not select a dashboard tab. Use the "
                "Phase 5 rendered-test screenshot service for multi-page screenshots."
            )
        response = self._request(
            "GET",
            f"/api/v1/dashboard/{published_ref.dashboard_id}/thumbnail/",
            expect_json=False,
        )
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise BIAdapterError(
                "Superset did not return a dashboard thumbnail. Configure Superset thumbnail "
                "generation or use the Streamlit preview."
            )
        return bytes(response.content)

    def _ensure_datasets(
        self, datasets: Sequence[SupersetDatasetRef]
    ) -> dict[str, dict[str, Any]]:
        bindings: dict[str, dict[str, Any]] = {}
        for dataset in datasets:
            if dataset.datasource_id is not None:
                bindings[dataset.metric_name] = {
                    "id": dataset.datasource_id,
                    "type": dataset.datasource_type,
                }
                continue
            response = self._request(
                "POST",
                "/api/v1/dataset/",
                json={
                    "database": dataset.database_id,
                    "schema": dataset.schema_name,
                    "table_name": dataset.table_name,
                },
            )
            bindings[dataset.metric_name] = {
                "id": self._response_id(response, "dataset"),
                "type": dataset.datasource_type,
            }
        return bindings

    def _chart_payload(
        self,
        widget: WidgetSpec,
        dataset: SupersetDatasetRef,
        datasource: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        datasource_id = int(datasource["id"])
        datasource_type = str(datasource["type"])
        metric = {
            "expressionType": "SQL",
            "sqlExpression": dataset.metric_expression,
            "label": dataset.metric_label,
            "hasCustomLabel": True,
        }
        groupby = list(widget.dimensions)
        if widget.time_dimension:
            groupby.insert(0, widget.time_dimension)
        query = {
            "datasource": {"id": datasource_id, "type": datasource_type},
            "columns": groupby,
            "metrics": [metric],
            "filters": [],
            "row_limit": 1000,
            "time_range": "No filter",
        }
        params = {
            "viz_type": self.VIZ_TYPES[widget.type],
            "datasource": f"{datasource_id}__{datasource_type}",
            "metrics": [metric],
            "groupby": groupby,
            "x_axis": groupby[0] if groupby else None,
            "time_grain_sqla": widget.time_grain,
            "row_limit": 1000,
        }
        payload = {
            "slice_name": widget.title,
            "viz_type": self.VIZ_TYPES[widget.type],
            "datasource_id": datasource_id,
            "datasource_type": datasource_type,
            "params": json.dumps(params),
            "dashboards": [],
        }
        return payload, query

    @staticmethod
    def _position_json(charts: Sequence[dict[str, Any]]) -> dict[str, Any]:
        position: dict[str, Any] = {
            "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
            "GRID_ID": {"id": "GRID_ID", "type": "GRID", "children": []},
        }
        charts_by_page: dict[str, list[dict[str, Any]]] = {}
        for chart in charts:
            charts_by_page.setdefault(chart["page_id"], []).append(chart)

        pages = list(charts_by_page.items())
        tab_ids = {
            page_id: f"TAB-{index}-{SupersetBIAdapter._slug(page_id)}"
            for index, (page_id, _) in enumerate(pages)
        }
        if len(pages) > 1:
            position["GRID_ID"]["children"] = ["TABS_ID"]
            position["TABS_ID"] = {
                "id": "TABS_ID",
                "type": "TABS",
                "children": [tab_ids[page_id] for page_id, _ in pages],
            }

        row_index = 0
        for page_id, page_charts in pages:
            row_ids: list[str] = []
            row_children: list[str] = []
            row_width = 0
            for chart in page_charts:
                width = chart["width"]
                if row_children and row_width + width > 12:
                    row_id = f"ROW-{row_index}"
                    row_ids.append(row_id)
                    position[row_id] = {
                        "id": row_id,
                        "type": "ROW",
                        "children": row_children,
                    }
                    row_index += 1
                    row_children = []
                    row_width = 0
                chart_id = f"CHART-{chart['chart_id']}"
                row_children.append(chart_id)
                position[chart_id] = {
                    "id": chart_id,
                    "type": "CHART",
                    "children": [],
                    "meta": {
                        "chartId": chart["chart_id"],
                        "width": width,
                        "height": 50,
                    },
                }
                row_width += width
            if row_children:
                row_id = f"ROW-{row_index}"
                row_ids.append(row_id)
                position[row_id] = {
                    "id": row_id,
                    "type": "ROW",
                    "children": row_children,
                }
                row_index += 1

            if len(pages) == 1:
                position["GRID_ID"]["children"] = row_ids
            else:
                tab_id = tab_ids[page_id]
                position[tab_id] = {
                    "id": tab_id,
                    "type": "TAB",
                    "children": row_ids,
                    "meta": {"text": page_charts[0]["page_title"]},
                }
        return position

    @staticmethod
    def _dashboard_metadata(
        spec: DashboardSpec,
        datasets: Sequence[SupersetDatasetRef],
        datasource_by_metric: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        filters = []
        for dashboard_filter in spec.global_filters:
            target_refs = []
            seen_targets = set()
            for dataset in datasets:
                if not SupersetBIAdapter._dataset_has_column(
                    dataset, dashboard_filter.column
                ):
                    continue
                datasource_id = int(datasource_by_metric[dataset.metric_name]["id"])
                target_key = (datasource_id, dashboard_filter.column.rsplit(".", maxsplit=1)[-1])
                if target_key in seen_targets:
                    continue
                seen_targets.add(target_key)
                target_refs.append(
                    {
                        "datasetId": datasource_id,
                        "column": {"name": target_key[1]},
                    }
                )
            filter_type = (
                "filter_time" if dashboard_filter.type == "date_range" else "filter_select"
            )
            filters.append(
                {
                    "id": (
                        f"NATIVE_FILTER-{uuid5(NAMESPACE_URL, spec.id + dashboard_filter.id)}"
                    ),
                    "name": dashboard_filter.label,
                    "filterType": filter_type,
                    "targets": target_refs,
                    "defaultDataMask": {
                        "extraFormData": {"filters": []},
                        "filterState": {"value": dashboard_filter.default_value},
                        "ownState": {},
                    },
                    "controlValues": {"enableEmptyFilter": False},
                    "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                    "type": "NATIVE_FILTER",
                }
            )
        return {
            "show_native_filters": bool(filters),
            "native_filter_configuration": filters,
        }

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> Any:
        headers = self._auth_headers()
        if method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and self._csrf_token:
            headers["X-CSRFToken"] = self._csrf_token
        response = self.client.request(
            method,
            f"{self.base_url}{path}",
            json=json,
            headers=headers,
        )
        if response.is_error:
            body = response.text[:500]
            raise BIAdapterError(
                f"Superset {method.upper()} {path} failed with HTTP {response.status_code}: {body}"
            )
        if not expect_json:
            return response
        if not response.content:
            return {}
        try:
            payload = response.json()
        except ValueError as exc:
            raise BIAdapterError(
                f"Superset {method.upper()} {path} returned invalid JSON."
            ) from exc
        if not isinstance(payload, dict):
            raise BIAdapterError(f"Superset {method.upper()} {path} returned an invalid response.")
        return payload

    def _auth_headers(self) -> dict[str, str]:
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
        else:
            if not self._csrf_token:
                login = self.client.post(
                    f"{self.base_url}/api/v1/security/login",
                    json={
                        "username": self.username,
                        "password": self.password,
                        "provider": "db",
                        "refresh": True,
                    },
                )
                if login.is_error:
                    raise BIAdapterError(
                        f"Superset login failed with HTTP {login.status_code}."
                    )
                try:
                    self.access_token = login.json()["access_token"]
                except (ValueError, KeyError, TypeError) as exc:
                    raise BIAdapterError("Superset login returned no access token.") from exc
            headers = {"Authorization": f"Bearer {self.access_token}"}
        if not self._csrf_token and self.username and self.password:
            csrf = self.client.get(
                f"{self.base_url}/api/v1/security/csrf_token/",
                headers=headers,
            )
            if csrf.is_error:
                raise BIAdapterError(
                    f"Superset CSRF token request failed with HTTP {csrf.status_code}."
                )
            try:
                self._csrf_token = csrf.json()["result"]
            except (ValueError, KeyError, TypeError) as exc:
                raise BIAdapterError("Superset returned no CSRF token.") from exc
        return headers

    @staticmethod
    def _response_id(payload: Mapping[str, Any], kind: str) -> int:
        result = payload.get("result")
        value = result.get("id") if isinstance(result, dict) else payload.get("id")
        if not isinstance(value, (int, str)):
            raise BIAdapterError(f"Superset did not return a valid {kind} ID.")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise BIAdapterError(f"Superset did not return a valid {kind} ID.") from exc

    @staticmethod
    def _query_filters(filters: Mapping[str, Any]) -> list[dict[str, Any]]:
        query_filters = []
        for column, value in filters.items():
            if value is None or value == "":
                continue
            if isinstance(value, tuple) and len(value) == 2:
                query_filters.extend(
                    [
                        {"col": column, "op": ">=", "val": value[0]},
                        {"col": column, "op": "<=", "val": value[1]},
                    ]
                )
            else:
                query_filters.append(
                    {
                        "col": column,
                        "op": "IN",
                        "val": value if isinstance(value, list) else [value],
                    }
                )
        return query_filters

    @staticmethod
    def _dataset_has_column(dataset: SupersetDatasetRef, column: str) -> bool:
        unqualified_column = column.rsplit(".", maxsplit=1)[-1]
        return any(
            candidate == column
            or candidate == unqualified_column
            or candidate.endswith(f".{unqualified_column}")
            for candidate in dataset.columns
        )

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
        return slug or "dashboard"
