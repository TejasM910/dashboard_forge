# 09 — Observability & Evals

## Telemetry
- Trace per run → span per task/agent/tool call (OpenTelemetry). Store prompt version, model, tokens, latency, cost, retries.
- Structured logs with `run_id, task_id, requirement_id`.
- Warehouse query log: SQL hash, bytes scanned, duration.

## Meta-dashboard (dashboard about our own system)
Runs/day · success rate · first-pass success · avg cost/run · avg time/run · human override rate · requirement coverage · metric accuracy · template reuse rate · top failure causes · LLM latency/cost by agent.

## LLM eval suites (CI-gated)
| Suite | Measures | Gate |
|---|---|---|
| Requirement extraction | recall/precision vs. labeled briefs | ≥ 0.9 / ≥ 0.85 |
| Ambiguity detection | planted ambiguities found | ≥ 0.85 |
| Term→column mapping | accuracy | ≥ 0.9 |
| Metric/SQL generation | reconciliation pass on golden datasets | ≥ 0.95 first-pass |
| Chart recommendation | agreement with analyst gold | ≥ 0.8 |
| Injection robustness | malicious brief content ignored | 100% |

## Alerts
Budget overrun · repeated fixer failures · drift in regression tests · connector failures · eval regression.
