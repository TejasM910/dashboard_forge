# 03 — Tech Stack

Configured for a **Zero-Cost, Local-First MVP** ($0 budget), fully runnable on a developer laptop without requiring paid cloud services, while maintaining clean abstractions to swap in enterprise cloud services (BigQuery, Snowflake, Databricks) later.

| Layer | Choice (Zero-Cost / Local-First) | Why | Cloud / Scale Alternative |
|---|---|---|---|
| Language | **Python 3.11+** | Data + AI ecosystem | — |
| API | **FastAPI + Pydantic v2** | Typed schemas = structured LLM I/O | Flask |
| Orchestration (agents) | **LangGraph** (state graph, checkpoints, human-in-loop interrupts) | Pauses at gates, resumable, runs fully local | Custom state machine, Temporal |
| Job queue | **In-process / BackgroundTasks (MVP)** or **Local Redis + Celery** | Zero-cost local async execution | Cloud Tasks |
| LLM | **Provider Abstraction:**<br>1. **Google Gemini API Free Tier** (generous free RPM/TPD via Google AI Studio)<br>2. **Ollama / Local LLM** (Qwen 2.5 Coder, Llama 3 - 100% free offline)<br>3. OpenRouter / Groq free tiers | $0 token cost for development and local testing | Claude (Anthropic), OpenAI API |
| Embeddings / search | **pgvector in local Postgres** (or local **sqlite-vec / Chroma / DuckDB VSS**) | Zero-cost local vector storage | Qdrant, Vertex Vector Search |
| Metadata DB | **Local PostgreSQL 15 (Docker or local service)** + SQLAlchemy + Alembic (fallback: SQLite) | Reliable, relational, $0 cost | Cloud SQL |
| Semantic layer | **Own YAML spec (MetricFlow/dbt-metrics compatible)** | Single source of metric truth | Cube, LookML |
| Warehouse (MVP) | **DuckDB (local embedded)** + **Local PostgreSQL** | Blisteringly fast, embedded, zero setup, $0 cloud cost; can read CSV/Parquet directly | BigQuery, Snowflake, Databricks SQL |
| Query abstraction | **SQLGlot (+ ibis)** | Dialect transpile, parse, lint, AST safety checks | raw SQL strings |
| Reference compute | **DuckDB + pandas/Polars** | Independent second calculation path for verification | Spark for large data |
| Data validation | **Pandera / Great Expectations** | Integrity tests | dbt tests |
| BI target (MVP) | **Apache Superset** for dashboard publication; **Streamlit native visualizations** for the local preview in the existing app | Superset is the FR-52 publication target; Streamlit provides a zero-cost review surface without replacing the BI adapter | Metabase, Looker Studio |
| Rendered tests | **Playwright** (headless) | Screenshots + DOM assertions | Selenium |
| Frontend | **Streamlit** (MVP) | Fast iteration, interactive UI for gates, zero hosting costs | Next.js/React |
| File parsing | `pypdf`, `python-docx`, `openpyxl`, `unstructured` | Briefs in any format | — |
| Observability | **Local structured logging + OpenTelemetry** (Optional local Langfuse via Docker) | Free prompt/run inspection without cloud subscription | Langfuse Cloud, LangSmith |
| LLM evals | **pytest + custom harness** | Prompt regression tests | promptfoo |
| Secrets | **Local `.env` / python-dotenv** | Simple, local, safe | GCP Secret Manager, Vault |
| Infra / Deploy | **Local Docker Compose / Localhost** | $0 infrastructure spend | Cloud Run, GKE |
| CI/CD | **GitHub Actions** (Free tier for public/private repos) | Standard automation | Cloud Build |
| Code quality | `ruff`, `mypy`, `pytest`, `pre-commit` | Open-source code standards | — |
| Packaging | `uv` (recommended) or `poetry` | Fast, modern Python package manager | pip |

## Model usage policy ($0 Budget Strategy)
- Primary Free Cloud Option: **Gemini Flash via Google AI Studio API** (free tier quota provides high-volume structured outputs at zero cost).
- Offline / 100% Air-Gapped Option: **Ollama** (e.g., `qwen2.5-coder:7b` or `llama3.1:8b`) for local development without internet or API keys.
- Temperature: 0–0.2; JSON-schema outputs via Pydantic; prompt + model version stored with each artifact.
- Token budget tracking per run to maintain awareness of usage limits.

### Phase 4 BI boundary
- The Streamlit app is the Dashboard Forge UI and may render a local preview from a `DashboardSpec`.
- Apache Superset remains the MVP BI publication target. A local Streamlit preview does not satisfy the Superset adapter or publication requirement.
- Both paths consume the same validated, tool-agnostic `DashboardSpec`; metric values must come from executed queries, never LLM output.
