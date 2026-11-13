# Task Breakdown (implementation starts only on owner's go-ahead)

Format: `T-id [Pri] title — specs — depends`.

## Phase 0 — Foundations
- T-001 [P0] Init repo, tooling (uv, ruff, mypy, pre-commit, CI) — 11
- T-002 [P0] Docker compose: Postgres+pgvector, Redis, Superset, MinIO — 03 — T-001
- T-003 [P0] DB schema + migrations for core entities — 05 — T-002
- T-004 [P0] LLM provider abstraction (structured output, retries, caching, budget) — 03,04 — T-001
- T-005 [P0] Pydantic models for Requirement/Task/Metric/DashboardSpec/Test — 05 — T-001
- T-006 [P0] Golden dataset v1 (synthetic e-commerce in DuckDB + BigQuery) with known answers — 06 — T-001
- T-007 [P0] Label 5 sample briefs (expected requirements, ambiguities) — 06,09
- T-008 [P0] Telemetry baseline (OpenTelemetry + Langfuse) — 09 — T-004

## Phase 1 — Requirements Engine
- T-101 File parsers (pdf/docx/xlsx/txt) — FR-01 — T-001
- T-102 Intake API + project model — FR-02,04 — T-003
- T-103 Requirement Analyst agent + prompt v1 — FR-10,11,15 — T-004,T-005
- T-104 Clarifier agent (ambiguity categories) — FR-12 — T-103
- T-105 Glossary store — FR-13 — T-003
- T-106 Requirements board UI + edit/merge/split + versioning — FR-14,80 — T-103
- T-107 Gate 1 approval flow — FR-16 — T-106
- T-108 Eval: extraction/ambiguity — 09 — T-007,T-103

## Phase 2 — Data Understanding
- T-201 Connector interface + BigQuery connector (read-only, dry-run) — FR-30 — T-001
- T-202 Profiler (schema, stats, freshness) — FR-31 — T-201
- T-203 Key/grain/join inference — FR-32 — T-202
- T-204 PII classifier + masking layer — FR-35 — T-202
- T-205 Semantic Mapper agent + confirm UI — FR-33 — T-203,T-103
- T-206 Data quality checks — FR-34 — T-202

## Phase 3 — Metrics & SQL
- T-301 Semantic layer YAML spec + loader/compiler — FR-40 — T-005
- T-302 Metric Designer agent (+ self-critique) — FR-40 — T-205,T-301
- T-303 Gate 2 + metric dictionary UI — FR-41 — T-302
- T-304 SQL Generator agent (dialect-aware via SQLGlot) — FR-42 — T-302
- T-305 SQL safety/static checks + dry-run — FR-43 — T-304
- T-306 Advanced metrics (YoY, rolling, cohort, funnel) — FR-44 — T-304

## Phase 4 — Dashboard Build
- T-401 [x] Dashboard Spec schema + validator (canonical Pydantic contract; 12-column flow layout; reference validation) — FR-50 — T-005
- T-402 [x] Chart recommender (deterministic rules; optional non-authoritative LLM rationale) — FR-51 — T-401
- T-403 [x] Dashboard Designer (approved requirements/metrics + schema metadata + confirmed mappings + validated SQL → traceable spec) — FR-50 — T-402,T-304
- T-404 [x] Apache Superset adapter (dataset bindings, charts, dashboards, filters; publish/update) — FR-52 — T-401
- T-405 [x] Theme/format layer (safe colors, units, number formats) — FR-53 — T-404
- T-406 [x] Query-backed Streamlit preview and Superset thumbnail retrieval — FR-54 — T-401,T-403,T-404

## Phase 5 — Test & Evidence
- T-501 Test Designer (requirement→tests, edge-case catalog) — FR-60 — T-403
- T-502 Reference calc engine (DuckDB/pandas from metric def) — FR-61 — T-301,T-006
- T-503 Reconciliation runner with tolerances/slices — FR-61 — T-502
- T-504 Integrity & consistency tests — FR-62 — T-202
- T-505 Golden-value tests from analyst input — FR-66 — T-501
- T-506 Rendered tests (Playwright) — FR-63 — T-404
- T-507 Traceability matrix + coverage check — FR-64 — T-501
- T-508 Evidence Report generator (HTML/PDF/JSON) — FR-65 — T-507
- T-509 Fixer agent + bounded fix loop — FR-24 — T-503
- T-510 Gate 3 + waiver audit — FR-16 — T-508

## Phase 6 — Orchestration
- T-601 LangGraph workflow: states, gates, checkpoints, resume — 04 — T-107,T-303,T-510
- T-602 Task DAG executor + Planner agent — FR-20..24 — T-601
- T-603 Live progress API/UI (SSE) — FR-23 — T-602
- T-604 Budget enforcement (tokens, bytes) — NFR-04 — T-004
- T-605 E2E tests on 3 sample briefs (AC-01..04) — T-602

## Phase 7 — Templates
- T-701 Template store + embeddings — FR-70 — T-003
- T-702 Retrieval + reuse/diff UI — FR-71 — T-701
- T-703 Promote/sanitize workflow — FR-72 — T-701
- T-704 Seed library (sales, marketing, SaaS, finance) — T-703
- T-705 Feedback capture — FR-73 — T-702

## Phase 8 — Hardening
- T-801 AuthN/Z (OIDC, RBAC), audit log — 08
- T-802 Prompt-injection & PII scan tests (AC-06) — 08
- T-803 Regression/drift scheduler — FR-67
- T-804 Delivery package export — FR-82
- T-805 Terraform + Cloud Run deploy — 03
- T-806 Pilot with real brief; collect metrics vs. targets — 00
