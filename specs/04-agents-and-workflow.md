# 04 — Agents & Workflow

## Run state machine
`CREATED → INTAKE → REQS_DRAFTED → CLARIFYING ⇄ → [GATE1: REQS_APPROVED] → PLANNED → DATA_DISCOVERED → METRICS_DRAFTED → [GATE2: METRICS_APPROVED] → QUERIES_BUILT → DASHBOARD_BUILT → TESTING → (FIXING ⇄ TESTING) → [GATE3: SIGNED_OFF] → DELIVERED`
Failure states: `NEEDS_HUMAN`, `FAILED`, `CANCELLED`. Every transition is logged and resumable.

## Agents (each = prompt + input schema + output schema + tools + eval set)
| # | Agent | Input → Output | Tools |
|---|---|---|---|
| 1 | **Intake Parser** | raw files/text → normalized text chunks + metadata | file parsers |
| 2 | **Requirement Analyst** | chunks → list of atomic `Requirement` (type, text, source ref, confidence) | glossary lookup |
| 3 | **Clarifier** | requirements → `Question[]` (ambiguity, conflicts, missing info) with suggested defaults | — |
| 4 | **Planner** | approved requirements → `Task` DAG | template search |
| 5 | **Data Profiler** (mostly deterministic) | connection → `DataProfile` | warehouse, profiler |
| 6 | **Semantic Mapper** | requirement terms + profile → term→column mappings + confidence | profile, glossary |
| 7 | **Metric Designer** | requirements + mappings → `MetricDefinition[]` | template search |
| 8 | **SQL Generator** | metric defs → SQL per metric/dataset | SQLGlot, dry-run |
| 9 | **Dashboard Designer** | metrics + requirements → `DashboardSpec` | chart recommender |
| 10 | **Test Designer** | requirements + metrics + spec → `TestCase[]` | — |
| 11 | **Verifier** (deterministic runner) | tests → `TestResult[]` | warehouse, DuckDB, Playwright |
| 12 | **Fixer** | failed tests + context → patch proposal (SQL/metric/spec) | all |
| 13 | **Reporter** | all results → Evidence Report + delivery package | templating |

## Task execution contract
```
id, name, agent, inputs[], outputs[], depends_on[], requirement_ids[],
acceptance_criteria[], status, attempts, max_attempts, cost, artifacts[]
```
Rules: run when dependencies done → validate output schema → run task-level acceptance checks → persist → next. On failure: repair (≤2) → Fixer (≤3) → escalate `NEEDS_HUMAN`.

## Typical task plan (auto-generated, example)
1. Parse brief → 2. Extract requirements → 3. Clarify → 4. Search templates → 5. Connect & profile data → 6. Map terms → 7. Define metrics (per KPI) → 8. Build SQL (per KPI) → 9. Static-check & dry-run SQL → 10. Design dashboard spec → 11. Publish to BI → 12. Generate tests → 13. Run tests → 14. Fix loop → 15. Report → 16. Sign-off → 17. Package & template-promote.

## Prompt/Agent engineering rules
- System prompt per agent stored in `prompts/<agent>/vN.md`; versioned and eval-gated.
- Structured output only; schema validation; auto-repair loop.
- Few-shot examples from template library & approved past projects.
- Agents receive **minimal context** (profile summaries, not raw data); PII masked.
- No agent may execute DML/DDL; tools enforce read-only.
- Self-critique step for Metric Designer & SQL Generator ("explain formula in plain English, check against requirement").

## Clarification protocol
Ambiguity categories: metric definition, time period/time zone, filters/exclusions, data source choice, currency/units, granularity, access rules, refresh. Each question includes: why asked, options, recommended default, impact if wrong. Unanswered questions block the gate (or require explicit "accept default").

## Phase 4 — Dashboard Build contract

### Entry conditions
- Gate 1 requirements are approved and have no unresolved blocking ambiguity.
- Gate 2 metric definitions are approved.
- SQL artifacts for the dashboard's metrics have passed the Phase 3 static checks and dry-run.
- The Phase 2 schema graph and data profiles are available to the designer; the designer does not infer or invent warehouse fields.

### Build flow
1. Validate the input requirements, approved metrics, generated SQL references, and schema metadata.
2. Recommend chart types deterministically from the metric's available dimensions, time dimension, and data shape. Any LLM-generated rationale is advisory and cannot override an unsupported chart/data combination.
3. Design a `DashboardSpec` that references existing metric names and requirement IDs and satisfies the layout and filter constraints in spec 05.
4. Validate the completed spec before it is rendered or published. Invalid references or layout must be reported as validation errors, not silently dropped or repaired into a success.
5. Render a local review preview in the existing Streamlit app. For MVP BI publication, pass the same validated spec to the Apache Superset adapter; Streamlit preview is not a substitute for publication.

### Phase 4 deliverables and boundaries
- **T-401:** Complete and validate the tool-agnostic dashboard/page/widget/filter model, including 12-column row layout rules.
- **T-402:** Rule-based chart recommender with testable decisions; optional LLM rationale is non-authoritative.
- **T-403:** Dashboard Designer using approved requirements, approved metrics, Phase 2 schema metadata, analyst-confirmed dimension/filter mappings, and SQL validation results; produces a validated spec with requirement traceability.
- **T-404:** Apache Superset BI adapter for spec validation, publication, update, and widget data retrieval.
- **T-405:** Theme and number-format handling that respects metric units and configured display preferences; unsafe format/color strings are rejected.
- **T-406:** Query-backed Streamlit preview in UI Screen 7 and Superset dashboard-thumbnail retrieval. The Streamlit preview and Superset publication are distinct targets using the same spec.

### Exit criteria
- Dashboard specs round-trip through the canonical schema and reject invalid metric/requirement references, filter references, and row widths.
- Supported chart recommendations and unsupported/ambiguous data shapes have deterministic, tested outcomes.
- Every generated widget links to one or more source requirements and an approved metric; no metric values are authored by an LLM.
- The same validated spec can be previewed in Streamlit and published/updated through the Superset adapter.
- Phase 0–3 tests remain passing. Phase 4 does not claim independent correctness evidence or final sign-off; those are Phase 5 responsibilities.
