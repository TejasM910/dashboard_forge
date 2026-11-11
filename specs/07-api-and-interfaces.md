# 07 — API & Interfaces

## REST API (v1)
```
POST   /projects                          create project
POST   /projects/{id}/briefs              upload brief(s)/text
GET    /projects/{id}/requirements        list (versioned)
PATCH  /requirements/{id}                 edit / approve / reject
GET    /projects/{id}/questions           clarifying questions
POST   /questions/{id}/answer
POST   /projects/{id}/data-sources        register source (read-only creds ref)
GET    /data-sources/{id}/profile
POST   /dashboards/{id}/runs              start run
GET    /runs/{id}                         state, tasks, cost
POST   /runs/{id}/gates/{gate}/approve    GATE1|GATE2|GATE3 (+comments / waivers)
POST   /runs/{id}/tasks/{tid}/retry|skip
GET    /dashboards/{id}/spec              DashboardSpec (versions)
GET    /runs/{id}/report                  Evidence Report (html/pdf/json)
GET    /templates?domain=&q=              search library
POST   /artifacts/{id}/promote-to-template
GET    /audit?project=
```
Auth: OIDC/JWT; RBAC roles `admin, analyst, reviewer, client_viewer`. Streaming: SSE/WebSocket for live task progress.

## UI screens (MVP → v1)
1. Projects list
2. Intake — upload/paste + structured form
3. Requirements board — extracted items with source highlight, confidence, edit/merge/split, questions panel → **Approve (Gate 1)**
4. Plan view — task DAG with live status, cost
5. Data & mapping — profile summary, term→column mapping confirm
6. Metric dictionary — definitions, plain-English formula, SQL, diff vs. template → **Approve (Gate 2)**
7. Dashboard preview — screenshots / embedded BI link
8. Test & evidence — traceability matrix, failures with diffs → **Sign-off (Gate 3)**
9. Template library
10. Admin — connectors, budgets, models, audit

## CLI (for engineers)
`dforge init | ingest brief.docx | run --until gate1 | approve gate1 | test | report | promote`

## BI Adapter Interface
```python
class BIAdapter(Protocol):
    def validate(spec: DashboardSpec) -> list[Issue]
    def publish(spec: DashboardSpec, datasets: list[Dataset]) -> PublishedRef
    def update(ref, spec) -> PublishedRef
    def fetch_widget_data(ref, widget_id, filters) -> DataFrame
    def screenshot(ref, page) -> bytes
```
## Warehouse Connector Interface
`connect(readonly) · list_tables · profile(table) · dry_run(sql) · execute(sql, limit, timeout) · dialect`
