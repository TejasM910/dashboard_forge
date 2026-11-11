# Dashboard Forge — Spec-Driven Project

An AI-assisted system that turns client dashboard requirements into verified, production-ready dashboards.
**Flow:** Client requirements → structured requirements → task plan → data discovery → metric definitions → queries → dashboard build → automated verification → human approval → delivery.

## How to use this folder (spec-driven rules)
1. **Specs are the source of truth.** Code is written *from* specs, never the other way round.
2. Read in order: `constitution.md` → `specs/00` … `specs/11` → `plan/`.
3. Every implementation task in `plan/tasks.md` references spec IDs (FR-xx, NFR-xx, AC-xx). A task is "done" only when its acceptance criteria pass.
4. If implementation reveals a spec gap, **update the spec first** (add a line in `plan/changelog.md`), then code.
5. Nothing is implemented until the owner says "start implementation" (currently: planning only).

## Folder map
| Path | Purpose |
|---|---|
| `constitution.md` | Non-negotiable principles (accuracy, traceability, human gates) |
| `specs/00-overview.md` | Vision, problem, goals, non-goals, personas, success metrics |
| `specs/01-requirements.md` | Functional + non-functional requirements with acceptance criteria |
| `specs/02-architecture.md` | Components, data flow, diagrams |
| `specs/03-tech-stack.md` | Chosen technologies and why, alternatives |
| `specs/04-agents-and-workflow.md` | AI agent pipeline, state machine, prompts contract |
| `specs/05-data-models.md` | Schemas for requirements, tasks, metrics, dashboard spec, tests |
| `specs/06-validation-and-accuracy.md` | How we prove the dashboard is correct |
| `specs/07-api-and-interfaces.md` | REST API, UI screens, CLI |
| `specs/08-security-and-governance.md` | Access, PII, audit, LLM safety |
| `specs/09-observability-and-evals.md` | Logging, tracing, LLM evals, KPIs |
| `specs/10-template-library.md` | Reuse of repeated requirements (the "stop repeating work" engine) |
| `specs/11-repo-structure.md` | Code layout, conventions, CI/CD |
| `plan/roadmap.md` | Phases and milestones |
| `plan/tasks.md` | Ordered task breakdown with dependencies |
| `plan/risks.md` | Risks and mitigations |
| `plan/changelog.md` | Spec change log |
| `examples/` | Sample client brief and sample generated dashboard spec |
