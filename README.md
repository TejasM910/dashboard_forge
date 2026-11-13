# Dashboard Forge ⚡

An AI-assisted, spec-driven system that transforms unstructured client dashboard briefs into verified, production-ready BI dashboards.

**End-to-End Flow:**  
Client Brief $\rightarrow$ Structured Requirements $\rightarrow$ Ambiguity Resolution $\rightarrow$ Human Gate 1 $\rightarrow$ Data Discovery & Profiling $\rightarrow$ Semantic Layer Metric Definitions $\rightarrow$ Human Gate 2 $\rightarrow$ Dialect-Aware SQL $\rightarrow$ Verification & Human Gate 3.

---

## 🏛️ Constitution Principles (Non-Negotiable)

1. **LLMs plan; databases compute.** Numbers shown on a dashboard never originate from an LLM; all values come from executed SQL against the warehouse.
2. **Every requirement is traceable.** Requirement $\rightarrow$ task $\rightarrow$ artifact (metric/query/chart) $\rightarrow$ test $\rightarrow$ result.
3. **Verify independently.** Two independent calculation paths (SQL vs. reference engine).
4. **Ambiguity is asked, not guessed.** Detects business definition, time boundary, or currency ambiguities and presents clarifying questions.
5. **3 Human Gates:** Requirement approval (Gate 1), Metric definition approval (Gate 2), Final sign-off (Gate 3).
6. **Zero-Cost / Local-First Stack ($0 Budget):** Designed to run 100% locally on Python, DuckDB, and Streamlit, with pluggable support for Google Gemini Free Tier / local Ollama models.

---

## 🚀 Quickstart & Interactive Web UI

### 1. Prerequisites & Environment
Ensure you have Python 3.11+ installed. Activate the project virtual environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

### 2. Launch the Streamlit Web UI
Run the following command to start the unified web application:

```powershell
$env:PYTHONPATH="src"
.\.venv\Scripts\streamlit.exe run ui/app.py
```
Open **`http://localhost:8501`** in your browser.

See detailed instructions in [UI_INSTRUCTIONS.md](UI_INSTRUCTIONS.md).

---

## 📦 Project Implementation Progress

| Phase | Description | Status | Key Deliverables |
|---|---|---|---|
| **Phase 0** | **Foundations & Architecture** | ✅ Completed | Repository structure, Core Pydantic Models (`models.py`), $0 LLM Provider abstraction (`provider.py`, `free_providers.py`), Golden DuckDB dataset generator (`golden_ecommerce.duckdb`). |
| **Phase 1** | **Requirements Engine & Gate 1** | ✅ Completed | Document intake parser (`document_parser.py`), Requirement Analyst Agent (`requirement_analyst.py`), Clarifier Agent (`clarifier.py`), and Human Gate 1 approval logic. |
| **Phase 2** | **Data Understanding & EDA** | ✅ Completed | Read-only DuckDB connector (`duckdb_connector.py`), Schema Profiler (`profiler.py`), Key/Grain/Join inferrer (`inferrer.py`), PII Masker (`pii_masker.py`), Semantic Mapper Agent (`semantic_mapper.py`), and deep EDA / Null-Handling diagnostics (`eda_analyzer.py`). |
| **Phase 3** | **Metrics & SQL Engine** | ✅ Completed | Semantic Layer YAML compiler (`layer.py`), Metric Designer Agent with self-critique (`metric_designer.py`), Dialect-aware SQL Generator (`sql_generator.py`), and SQLGlot AST static safety linter with dry-runs (`sql_validator.py`). |
| **Interactive UI** | **Web Application** | ✅ Completed | Streamlit multi-screen app (`ui/app.py`) uniting intake, Gate 1, data profiling, Gate 2, and live SQL execution. |
| **Phase 4** | **Dashboard Build** | ✅ Implemented | Validated `DashboardSpec`, deterministic Chart Recommender, traceable Dashboard Designer, query-backed Streamlit Screen 7, and Apache Superset REST adapter. Superset publication needs a configured Superset instance. |
| **Phase 5** | **Test & Evidence** | ⏳ Next | Independent reconciliation runner (SQL vs. DuckDB reference), Playwright rendered tests, traceability coverage, and Evidence Report. |
| **Phase 6** | **LangGraph Orchestrator** | ⏳ Pending | End-to-end task DAG state machine with checkpoint interrupts at Gates 1, 2, and 3. |

---

## 🧪 Testing

To run the automated unit and end-to-end integration test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The Phase 0–4 unit and integration suite currently passes 28 tests.

Run the Phase 4 dashboard build and query-backed filter demo:

```powershell
$env:PYTHONPATH="src"
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe scripts\verify_phase4.py
```

---

## 📂 Repository Map

```text
dashboard-forge/
├── specs/                 # Source-of-truth specifications (00 to 11)
├── plan/                  # Roadmap, tasks, risks, and changelog
├── examples/              # Sample client briefs and dashboard specs
├── evals/                 # Synthetic golden datasets & benchmark briefs
├── src/dforge/
│   ├── core/              # Pydantic schemas (Requirement, Metric, Task, Spec)
│   ├── llm/               # Zero-cost LLM provider abstraction (Gemini, Ollama, Mock)
│   ├── agents/            # Requirement Analyst, Clarifier, Semantic Mapper, Metric Designer, SQL Generator
│   ├── tools/             # Connectors (DuckDB), Profiler, Inferrer, PII Masker, EDA Analyzer, SQL Validator
│   └── semantic/          # Semantic Layer YAML compiler
├── ui/                    # Streamlit web application
├── tests/                 # Unit and end-to-end integration tests
├── scripts/               # Interactive verification scripts (Phases 0–4)
└── UI_INSTRUCTIONS.md     # UI launch and user guide
```
