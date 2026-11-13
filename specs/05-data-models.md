# 05 — Data Models (logical)

## Core entities (Postgres)
`Project, Dashboard, Requirement, Question, Task, Run, DataSource, DataProfile, Mapping, MetricDefinition, Dataset, QueryArtifact, DashboardSpec, TestCase, TestResult, Report, Template, GlossaryTerm, AuditEvent, User`

## Requirement
```yaml
id: REQ-014
project_id: ...
type: metric | dimension | filter | layout | refresh | access | data_quality | nfr
statement: "Show monthly net revenue by region with YoY comparison"
source: {file: brief.docx, locator: "p2 para3", quote: "..."}
priority: must | should | could
confidence: 0.87
status: draft | clarify | approved | rejected
version: 3
open_questions: [Q-021]
```

## MetricDefinition (semantic layer YAML)
```yaml
metric: net_revenue
label: Net Revenue
description: Gross sales minus discounts and refunds, excluding tax
type: simple | ratio | derived | cumulative | cohort
formula: sum(order_items.amount) - sum(discounts.amount) - sum(refunds.amount)
grain: order_item
time_dimension: orders.order_date
time_zone: Asia/Kolkata
dimensions: [region, product_category, channel]
filters: ["orders.status = 'completed'"]
unit: INR
format: "#,##0"
sources: [raw.orders, raw.order_items, raw.refunds]
requirement_ids: [REQ-014]
owner: analyst@...
status: draft | approved
version: 2
```

## Task / Run
```yaml
task: {id, run_id, agent, status, depends_on[], requirement_ids[], inputs_hash, outputs[], attempts, tokens, cost, started_at, ended_at, error}
run:  {id, dashboard_id, state, spec_versions{}, model_versions{}, budget, cost_to_date}
```

## DashboardSpec (tool-agnostic JSON/YAML)
The canonical model is the Pydantic contract in `src/dforge/core/models.py`; serialized examples must conform to it. A spec contains dashboard metadata, global filters (including the requirement IDs each filter satisfies), ordered pages, and ordered widgets. Widget placement uses a 12-column grid: each widget has an integer width from 1 through 12, and widgets flow left-to-right in declaration order, wrapping to a new row when the next widget would exceed 12 columns. Explicit coordinates are out of scope for Phase 4.

### Phase 4 validation rules
- Dashboard, page, widget, and filter IDs are non-empty and unique within their respective scopes.
- A dashboard has at least one page; an empty page is invalid.
- Widget widths are integers in `[1, 12]`; the ordered widths within each implicit row may not exceed 12.
- Every widget's `metric` resolves to an approved `MetricDefinition`, and its `requirement_ids` resolve to approved requirements.
- Every metric and dimension requirement is represented by at least one widget; every filter requirement is represented by an explicit global filter mapping.
- Dimension requirements must map to dimensions already approved on a metric; filter columns must be explicitly confirmed by the analyst. The designer does not infer a field mapping from requirement prose.
- Widget dimensions must resolve to fields available from the metric/dataset contract and discovered schema. Widget `filters`, when present, reference IDs in `DashboardSpec.global_filters`; unknown references are validation errors.
- Every global filter has a unique ID and a supported filter type; its column must resolve to a permitted field. Default values must be compatible with the filter type.
- A widget's chart type must be supported by its metric and dimensionality. The recommender's rationale is metadata, not a validation override.
- Validation returns actionable issues and does not remove, fabricate, or silently rewrite content.

Phase 4 does not add SQL expressions to widgets: widgets reference approved metrics, and their displayed values are sourced from executed queries. See `examples/sample-dashboard-spec.yaml` as an example to align with the canonical schema before implementation.

## TestCase / TestResult
```yaml
test: {id: T-101, requirement_id: REQ-014, metric: net_revenue,
       type: reconciliation | integrity | golden | render | filter | performance | regression,
       method: "sql_vs_duckdb", params: {slice: "2025-Q3", tolerance: {abs: 0.5, rel: 0.0001}}, expected: null}
result: {test_id, run_id, status: pass|fail|error|skipped, actual, expected, diff, evidence: [sql, screenshot, rows_sample], duration}
```

## Template
```yaml
template: {id, domain: sales, kind: metric|dataset|layout|dashboard, definition_ref, embedding, usage_count, success_rate, version, tags}
```
