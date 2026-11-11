# 01 — Requirements

Priority: **P0** = MVP, **P1** = v1, **P2** = later.

## Functional Requirements

### A. Requirement Intake
| ID | Requirement | Pri |
|---|---|---|
| FR-01 | Accept requirements as free text, uploaded files (PDF, DOCX, XLSX, MD, TXT), pasted emails/meeting notes | P0 |
| FR-02 | Accept structured intake form (business goal, audience, KPIs, filters, refresh frequency, deadline) | P0 |
| FR-03 | Support audio/meeting transcript ingestion | P2 |
| FR-04 | Create a project per client engagement; multiple dashboards per project | P0 |

### B. Requirement Understanding
| ID | Requirement | Pri |
|---|---|---|
| FR-10 | Extract atomic requirements: KPIs, dimensions, filters, time grain, comparisons, visual preferences, refresh rate, audience, access rules | P0 |
| FR-11 | Classify each requirement (metric / dimension / filter / layout / data-quality / non-functional) | P0 |
| FR-12 | Detect ambiguity, conflicts, and missing info; produce clarifying questions with suggested answers | P0 |
| FR-13 | Maintain a glossary of business terms per client (e.g. "active user") | P1 |
| FR-14 | Analyst can edit, merge, split, reject requirements in the UI; all edits versioned | P0 |
| FR-15 | Each requirement gets a stable ID, source citation (which sentence/file produced it) and confidence score | P0 |
| FR-16 | Requirement approval gate before planning starts | P0 |

### C. Planning & Task Decomposition
| ID | Requirement | Pri |
|---|---|---|
| FR-20 | Convert approved requirements into a task DAG (dependencies, order, owner=agent/human) | P0 |
| FR-21 | Each task has: goal, inputs, outputs, acceptance criteria, linked requirement IDs | P0 |
| FR-22 | Execute tasks one by one (or parallel where independent); persist state; resumable after failure | P0 |
| FR-23 | Show live plan/progress; allow analyst to pause, skip, re-run, or edit a task | P1 |
| FR-24 | Replan automatically when a task fails validation (bounded retries, then escalate to human) | P1 |

### D. Data Discovery
| ID | Requirement | Pri |
|---|---|---|
| FR-30 | Connect to data sources (BigQuery first; Postgres, Snowflake, Databricks SQL, CSV/Parquet upload next) read-only | P0 |
| FR-31 | Profile schema: tables, columns, types, row counts, null %, distinct counts, min/max, freshness | P0 |
| FR-32 | Infer grain, primary keys, candidate joins and relationships (with confidence) | P0 |
| FR-33 | Map requirement terms → tables/columns (semantic mapping) with analyst confirmation | P0 |
| FR-34 | Detect data quality issues (duplicates, nulls, orphan keys, time-zone issues, outliers) and report | P1 |
| FR-35 | Mask/exclude PII columns from LLM context | P0 |

### E. Metric & Query Generation
| ID | Requirement | Pri |
|---|---|---|
| FR-40 | Generate a **metric definition** per KPI (name, formula, grain, filters, dimensions, unit, owner) in a semantic-layer YAML | P0 |
| FR-41 | Metric approval gate: analyst confirms definitions before SQL is finalized | P0 |
| FR-42 | Generate SQL (dialect-aware) for each metric/dataset; store as versioned files | P0 |
| FR-43 | SQL must pass static checks (parse, lint, no DDL/DML, cost estimate via dry-run) | P0 |
| FR-44 | Support period comparisons (YoY, MoM, WoW), rolling windows, cohorts, funnels, ratios | P1 |

### F. Dashboard Generation
| ID | Requirement | Pri |
|---|---|---|
| FR-50 | Produce a tool-agnostic **Dashboard Spec** (pages, charts, filters, layout, interactions) | P0 |
| FR-51 | Chart-type recommendation by data shape & requirement (with rationale) | P0 |
| FR-52 | BI adapter to publish the spec into target tool: Apache Superset (MVP); then Looker Studio/Metabase/Power BI/Tableau | P0 / P2 |
| FR-53 | Apply consistent theme/branding, number formats, currency, time zone, accessibility basics | P1 |
| FR-54 | Generate preview (screenshots) for client review | P1 |
| FR-55 | Regenerate/patch dashboard from changed requirements without rebuilding everything | P1 |

### G. Testing & Accuracy
| ID | Requirement | Pri |
|---|---|---|
| FR-60 | Generate test cases per requirement automatically (see spec 06) | P0 |
| FR-61 | Run **reconciliation tests**: dashboard query result vs. independent reference calculation | P0 |
| FR-62 | Run data-integrity tests: row counts, null rates, uniqueness, totals = sum of parts, filter consistency | P0 |
| FR-63 | Run **rendered tests**: dashboard loads, charts populated, filters work, no errors (headless browser) | P1 |
| FR-64 | Run requirement-coverage check: every requirement mapped to ≥1 passing test | P0 |
| FR-65 | Produce an **Accuracy & Evidence Report** (pass/fail per requirement, diffs, SQL, screenshots) | P0 |
| FR-66 | Allow analyst to supply "expected values" (e.g. "Q3 revenue should be ₹4.2 Cr") as golden tests | P0 |
| FR-67 | Regression suite: re-run on data refresh/spec change; alert on drift | P1 |
| FR-68 | LLM-as-judge review of requirement-vs-dashboard fit (advisory only; never sole pass criterion) | P2 |

### H. Reuse & Learning
| ID | Requirement | Pri |
|---|---|---|
| FR-70 | Template library of metrics, datasets, dashboard layouts by domain (sales, marketing, finance, ops, HR, product) | P1 |
| FR-71 | Retrieve similar past requirements/metrics via embeddings; propose reuse with diff | P1 |
| FR-72 | Promote an approved project artifact to a template with one click | P1 |
| FR-73 | Capture analyst corrections as feedback to improve prompts/few-shot examples | P2 |

### I. Collaboration & Delivery
| ID | Requirement | Pri |
|---|---|---|
| FR-80 | Review UI: requirements, plan, metrics, SQL, preview, test report; comment & approve | P0 |
| FR-81 | Versioning and diff of all artifacts; rollback | P1 |
| FR-82 | Export delivery package: dashboard link, metric dictionary, test report, SQL, runbook | P1 |
| FR-83 | Notifications (email/Slack) for questions, approvals, completion | P2 |

## Non-Functional Requirements
| ID | Requirement | Target |
|---|---|---|
| NFR-01 | **Accuracy**: no unverified number is presented as verified | 0 tolerance |
| NFR-02 | **Reproducibility**: same inputs + pinned versions → same artifacts (modulo LLM variance, mitigated by caching & structured output) | Required |
| NFR-03 | **Performance**: standard run (≤10 metrics, ≤5 tables) | ≤ 30 min |
| NFR-04 | **Cost control**: per-run LLM + warehouse budget caps; query dry-run before execute | Configurable |
| NFR-05 | **Security**: read-only creds, secrets in vault, PII masking, RBAC, audit log | Required |
| NFR-06 | **Observability**: trace every agent step, prompt, token cost, query | Required |
| NFR-07 | **Extensibility**: pluggable data connectors, BI adapters, LLM providers | Required |
| NFR-08 | **Resilience**: idempotent, resumable tasks; bounded retries | Required |
| NFR-09 | **Explainability**: every metric shows definition, lineage, and SQL | Required |
| NFR-10 | **Privacy**: client data isolation (multi-tenant separation) | Required |

## Acceptance Criteria (system-level)
- **AC-01**: Given a sample brief with 10 KPIs, system extracts ≥ 9 correct atomic requirements and asks clarifying questions for all planted ambiguities.
- **AC-02**: Given a golden dataset, every generated metric matches the reference calc within tolerance.
- **AC-03**: Requirement coverage report shows 100% requirements mapped to tests; any uncovered one is flagged red.
- **AC-04**: Pipeline resumes from last successful task after a forced crash.
- **AC-05**: Second similar project reuses ≥ 50% of metrics/layout from templates.
- **AC-06**: Sensitive columns never appear in any LLM prompt log (verified by automated scan).
