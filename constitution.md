# Constitution — Non-Negotiable Principles

1. **LLMs plan; databases compute.** No number shown on a dashboard may come from an LLM. All values come from executed SQL against the client's data.
2. **Every requirement is traceable.** Requirement → task → artifact (metric/query/chart) → test → result. A requirement with no passing test is *unverified* and must be flagged, never silently shipped.
3. **Verify independently.** The component that builds a metric must not be the only one that checks it (builder ≠ verifier; two independent computation paths).
4. **Ambiguity is asked, not guessed.** If a requirement is ambiguous (e.g. "revenue" – gross/net? currency? time zone?), the system asks the analyst/client; it never assumes silently.
5. **Human gates at 3 points:** requirement approval, metric-definition approval, final dashboard sign-off.
6. **Everything is a versioned artifact.** Requirements, metric definitions, queries, dashboard specs are stored as declarative, diff-able files (YAML/JSON/SQL).
7. **Deterministic where possible.** Structured outputs (JSON schema), temperature low, pinned model versions, cached results, reproducible runs.
8. **Least privilege & privacy by default.** Read-only warehouse access, PII masked from LLM context, full audit log.
9. **Reuse before generate.** Search the template/metric library first; generate only the delta.
10. **Measure ourselves.** Track accuracy, rework rate and time saved; regressions block release.
