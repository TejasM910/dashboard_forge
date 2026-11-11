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
See `examples/sample-dashboard-spec.yaml`. Contains: dashboard meta, global filters, pages → rows → widgets, each widget linked to `metric` and `requirement_ids`.

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
