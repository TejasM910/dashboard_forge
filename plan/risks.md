# Risks & Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| LLM misreads requirement / invents metric meaning | Wrong dashboard | Clarifier + Gate 1/2, source citations, confidence scores |
| Wrong joins (fan-out) inflate numbers | Silent inaccuracy | Join-cardinality checks, L3 reconciliation, L5 consistency tests |
| Verifier shares same bug as builder | False pass | Independent reference path, golden values from humans |
| Hallucinated columns/tables | Broken SQL | Schema-grounded prompts, SQLGlot validation, dry-run |
| Cost blowup (LLM/warehouse) | Budget | Dry-run, limits, caching, small models for easy tasks |
| PII leakage to LLM | Compliance | Masking, aggregates only, log scans |
| Prompt injection via client docs | Security | Docs as data, tool allowlist, schema outputs, injection evals |
| BI tool API limits/changes | Rework | Adapter abstraction, tool-agnostic spec |
| Over-automation reduces analyst trust | Adoption | Transparent evidence, gates, easy overrides |
| Requirement scope creep | Delay | MVP cut, change log, spec-first discipline |
