# Roadmap

| Phase | Goal | Key deliverables | Exit criteria |
|---|---|---|---|
| **0 — Foundations** (wk 1–2) | Repo, infra, contracts | Repo skeleton, CI, Postgres, schemas, LLM abstraction, golden dataset v1, 5 labeled briefs | CI green; schemas validated |
| **1 — Requirements Engine** (wk 3–4) | Brief → approved requirements | Intake parser, Requirement Analyst, Clarifier, review UI, Gate 1 | AC-01; extraction eval ≥ targets |
| **2 — Data Understanding** (wk 5–6) | Profile + map | BigQuery connector, profiler, PII masking, Semantic Mapper | mapping accuracy ≥ 0.9 |
| **3 — Metrics & SQL** (wk 7–8) | Definitions → verified SQL | Metric Designer, semantic YAML, SQL generator + safety, Gate 2 | L1 + L3 pass on golden data |
| **4 — Dashboard Build** (wk 9–10) | Spec → Superset dashboard | Dashboard Designer, chart recommender, Superset adapter, previews | dashboard published from spec |
| **5 — Test & Evidence** (wk 11–12) | Prove accuracy | Test Designer, runners L1–L6, traceability, Evidence Report, Fixer loop, Gate 3 | AC-02, AC-03, AC-04 |
| **6 — Orchestration & Resilience** (wk 13) | End-to-end | Task DAG executor, resume, budgets, observability | full E2E run on 3 sample briefs |
| **7 — Templates & Reuse** (wk 14–15) | Stop repeating | Library, retrieval, promotion, seed templates | AC-05 |
| **8 — Hardening & Pilot** (wk 16+) | Real client pilot | Security review, RBAC, cost caps, regression/drift, docs | pilot delivered; ≥60% time saved |
| **Later** | Scale | More connectors/BI tools, Slack bot, audio intake, self-improving prompts | — |

**MVP cut** = Phases 0–6 with BigQuery + Superset + Streamlit.
