# 11 — Repo Structure & Engineering Conventions

```
dashboard-forge/
├─ specs/ plan/ examples/ constitution.md
├─ src/dforge/
│  ├─ api/            # FastAPI routers, auth, schemas
│  ├─ core/           # config, db, models, events
│  ├─ orchestrator/   # graph, state machine, gates, checkpoints
│  ├─ agents/         # one module per agent (+ versioned prompts)
│  ├─ tools/
│  │  ├─ parsers/     # pdf/docx/xlsx
│  │  ├─ connectors/  # bigquery, postgres, duckdb...
│  │  ├─ sql/         # sqlglot lint, safety, dry-run
│  │  ├─ profiling/
│  │  └─ bi/          # superset adapter, base protocol
│  ├─ semantic/       # metric/dataset YAML loader, compiler
│  ├─ validation/     # test generator, runners, reconciliation, reports
│  ├─ templates/      # library, retrieval, promotion
│  └─ llm/            # provider abstraction, caching, budgets
├─ ui/                # streamlit (MVP) → web app
├─ evals/             # briefs, golden datasets, eval runners
├─ tests/             # unit, integration, e2e
├─ infra/             # docker, terraform, CI
└─ docs/
```

## Conventions
- Typed Python (mypy strict on core), ruff, pre-commit.
- Every agent: `prompt.md`, `input.py`, `output.py`, `run.py`, `eval.py`.
- Every PR links a task ID and spec IDs; spec changes in the same PR update `plan/changelog.md`.
- CI: lint → types → unit → integration (docker compose: postgres, redis, superset, duckdb) → evals → build.
- Trunk-based branching; semantic versioning for prompts, specs, templates.
- Definition of Done: acceptance criteria met, tests + evals pass, docs updated, telemetry present.
