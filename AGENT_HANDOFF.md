# Agent Handoff Document — Dashboard Forge

**Date:** 2026-11-13  
**Project:** Dashboard Forge (Spec-Driven AI BI Pipeline)  
**Repository:** https://github.com/TejasM910/dashboard_forge.git  
**Branch:** `main` (clean, all current work tested and pushed)

---

## 1. Project Overview & Architectural Invariants

Dashboard Forge is an AI-assisted co-pilot that converts unstructured client dashboard briefs into verified, production-ready BI dashboards.

### Core Constitution Principles (Must NEVER be violated):
1. **LLMs plan; databases compute:** No metric number shown on a dashboard may come from an LLM. All calculations originate from executed SQL against the client warehouse.
2. **Every requirement is traceable:** Requirement $\rightarrow$ task $\rightarrow$ artifact (metric/query/chart) $\rightarrow$ test $\rightarrow$ result.
3. **Verify independently:** The builder $\neq$ verifier (generated SQL is reconciled against an independent computation path in DuckDB/pandas).
4. **Ambiguity is asked, not guessed:** If a requirement is ambiguous (e.g., gross vs net revenue, time zones), the system formulates clarifying questions with options and defaults; it never assumes silently.
5. **3 Human Gates:**
   - **Gate 1:** Requirement & Ambiguity Approval (before planning/profiling)
   - **Gate 2:** Metric Definition & Semantic Layer Approval (before finalizing SQL)
   - **Gate 3:** Final Dashboard Sign-off & Evidence Report (before delivery)
6. **Zero-Cost / Local-First Stack ($0 Budget):**
   - **Warehouse Engine:** DuckDB (embedded, read-only, fast, local)
   - **LLM Abstraction:** Supports Google Gemini API Free Tier (Google AI Studio) and local Ollama (`qwen2.5-coder:7b`, `llama3.1:8b`), plus deterministic `MockLLMProvider` for tests/CI.
   - **UI:** Streamlit local web application (`ui/app.py`).

---

## 2. Current Implementation Status

All code is fully tested with **16/16 unit and integration tests passing 100% green**.

| Phase | Deliverable | Status | Files Implemented |
|---|---|---|---|
| **Phase 0: Foundations** | Repo layout, models, LLM abstraction, golden dataset | ✅ Done | `src/dforge/core/models.py`<br>`src/dforge/llm/provider.py`<br>`src/dforge/llm/free_providers.py`<br>`evals/datasets/create_golden_dataset.py`<br>`evals/datasets/golden_ecommerce.duckdb` |
| **Phase 1: Requirements Engine** | Document parser, Requirement Analyst, Clarifier, Gate 1 logic | ✅ Done | `src/dforge/tools/parsers/document_parser.py`<br>`src/dforge/agents/requirement_analyst.py`<br>`src/dforge/agents/clarifier.py`<br>`src/dforge/agents/requirements_service.py` |
| **Phase 2: Data Understanding** | Warehouse connector, Profiler, Inferrer, PII Masker, EDA & Null-handling, Semantic Mapper | ✅ Done | `src/dforge/tools/connectors/duckdb_connector.py`<br>`src/dforge/tools/profiling/profiler.py`<br>`src/dforge/tools/profiling/inferrer.py`<br>`src/dforge/tools/profiling/pii_masker.py`<br>`src/dforge/tools/profiling/eda_analyzer.py`<br>`src/dforge/agents/semantic_mapper.py` |
| **Phase 3: Metrics & SQL** | Semantic Layer YAML, Metric Designer with self-critique, SQL Generator with joins, SQLGlot AST validator | ✅ Done | `src/dforge/semantic/layer.py`<br>`src/dforge/agents/metric_designer.py`<br>`src/dforge/agents/sql_generator.py`<br>`src/dforge/tools/sql/sql_validator.py` |
| **Interactive UI** | Unified Streamlit Web App (Screens 1, 2, 3, 5, 6) | ✅ Done | `ui/app.py`<br>`UI_INSTRUCTIONS.md` |
| **Phase 4: Dashboard Build** | DashboardSpec, Chart Recommender, Dashboard Designer, BI rendering | ⏳ **NEXT UP** | To be implemented in `src/dforge/tools/bi/`, `src/dforge/agents/` |
| **Phase 5: Test & Evidence** | L1–L6 tests, reconciliation engine, Evidence Report, Gate 3 | ⏳ Pending | `src/dforge/validation/` |
| **Phase 6: Orchestration** | LangGraph DAG execution, state persistence, resumability | ⏳ Pending | `src/dforge/orchestrator/` |

---

## 3. How to Run & Verify Existing Work

### Environment Setup
Python 3.11+ using the existing `.venv`:
```powershell
# Set PYTHONPATH
$env:PYTHONPATH="src"
```

### Run the Full Automated Test Suite
```powershell
.\.venv\Scripts\python.exe -m pytest -v
# Output: 16 passed in ~5s
```

### Run Phase-Specific Verification Scripts
Each completed phase has an interactive demo script:
```powershell
.\.venv\Scripts\python.exe scripts\verify_phase0.py
.\.venv\Scripts\python.exe scripts\verify_phase1.py
.\.venv\Scripts\python.exe scripts\verify_phase2.py
.\.venv\Scripts\python.exe scripts\verify_phase3.py
```

### Run the Interactive Web UI
```powershell
.\.venv\Scripts\streamlit.exe run ui/app.py
# Opens at http://localhost:8501
```

---

## 4. Exact Instructions for the Incoming Agent

The incoming agent should proceed with **Phase 4: Dashboard Build**.

### Objective of Phase 4 (from `plan/tasks.md` and `specs/04-agents-and-workflow.md`):
Turn approved metrics and requirements into a tool-agnostic `DashboardSpec` and render it visually.

### Tasks to Implement in Phase 4:
1. **`T-401`: Dashboard Spec Schema & Validator (`src/dforge/core/models.py`)**
   - The basic `DashboardSpec`, `WidgetSpec`, `FilterSpec`, and `DashboardPage` are already in `models.py`.
   - Add layout grid validation (12-column grid system, widget width rules).
2. **`T-402`: Chart Recommender (`src/dforge/tools/bi/chart_recommender.py`)**
   - Rule-based + LLM rationale engine that maps data shapes to chart types:
     - Single value, no dimensions $\rightarrow$ `KPI_CARD`
     - Time dimension (e.g. `order_date`, `month`) $\rightarrow$ `LINE` chart
     - Low-cardinality categorical dimension (e.g. `category`, `region`) $\rightarrow$ `BAR` or `STACKED_BAR`
     - Multi-dimension comparison $\rightarrow$ `TABLE` or `HEATMAP`
3. **`T-403`: Dashboard Designer Agent (`src/dforge/agents/dashboard_designer.py`)**
   - Agent that accepts approved `Requirement` list, `MetricDefinition` list, and `SchemaGraph`, and produces a coherent, multi-page or multi-row `DashboardSpec`.
4. **`T-404` / `T-406`: Streamlit BI Preview Adapter (`src/dforge/tools/bi/streamlit_renderer.py` / update `ui/app.py`)**
   - Renders the generated `DashboardSpec` directly inside the Streamlit app (Screen 7: Dashboard Preview) with live interactive filters, Altair/Plotly/Streamlit native charts, and KPI metric cards.

### Critical Guidelines for the Incoming Agent:
- **Test thoroughly BEFORE pushing to GitHub.** The user explicitly stated: *"before pushing the code to github test thoroughly because once pushing it is difficult to revert if any mistakes happen, so test and let me know when to push."*
- Always maintain backwards compatibility with existing Phase 0–3 tests.
- Keep to the $0 zero-cost stack (DuckDB, local Streamlit, Gemini free tier / Ollama / Mock).
