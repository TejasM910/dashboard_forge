# 06 — Validation & Accuracy ("prove it's right")

## Principle
A dashboard is **verified** only when each requirement maps to passing tests built from evidence independent of the generator.

## Test layers
| Layer | What | How | Gate |
|---|---|---|---|
| **L0 Spec checks** | Requirements well-formed; every requirement has mapped metric/widget | schema + traceability matrix | blocks build |
| **L1 SQL static** | Parses, read-only, no cartesian join, partition filter present, cost under budget | SQLGlot + BigQuery dry-run | blocks execute |
| **L2 Data integrity** | Row counts vs. source, null % thresholds, PK uniqueness, join fan-out detection, orphan keys, freshness | Pandera/GE + SQL | blocks |
| **L3 Reconciliation** | Dashboard query result == independent reference (DuckDB/pandas recompute from raw extract, or alternative SQL formulation) across several slices | automated | blocks |
| **L4 Golden values** | Analyst/client-supplied expected numbers ("Q3 revenue = X") | exact/tolerance compare | blocks |
| **L5 Consistency** | Total = sum of parts; filters narrow results correctly; KPI card = chart total; period comparisons coherent | property tests | blocks |
| **L6 Rendered** | Loads < N s, no error widgets, every widget has data, filters change data, screenshots captured | Playwright | blocks (P1) |
| **L7 Requirement-fit review** | LLM-as-judge compares requirement text vs. widget/metric; flags mismatches | advisory | warns |
| **L8 Regression** | Re-run L2–L6 on refresh/spec changes; alert on drift | scheduled | alerts |

## Reconciliation detail (L3)
1. Pull a small, **deterministic sample/aggregated extract** from the source (or full for small data).
2. Recompute the metric in DuckDB/pandas **from the metric definition** (not from the generated SQL).
3. Compare with the generated SQL result per slice.
4. Tolerance: integers exact; money abs ≤ 0.01 or rel ≤ 1e-6; ratios rel ≤ 1e-4 (configurable per metric).
5. Slices: total, last full period, first period, month-end boundary, each dimension top-N, empty-filter edge case, time-zone boundary.

## Edge-case catalog (auto-added to tests)
duplicates & fan-out joins · NULLs in dimensions · late-arriving data · time-zone/month-boundary · currency mixes · cancelled/refunded records · division by zero · incomplete current period · leap years · slowly changing dimensions.

## Accuracy metrics we report
- **Requirement coverage** = requirements with ≥1 passing test / total
- **Metric accuracy** = metrics passing L3+L4 / total metrics
- **Extraction recall/precision** (offline eval vs. labeled briefs)
- **Mapping accuracy** (term→column vs. gold)
- **First-pass success rate** (no fixer/human edits), **fix-loop rate**, **human override rate**

## Evidence Report (output)
Executive summary → traceability matrix (REQ → metric → widget → tests → status) → per-metric definition, SQL, reference result, diff → data quality findings → open risks / assumptions (e.g. defaults accepted) → screenshots → sign-off block.
Status per requirement: ✅ Verified · ⚠️ Verified with assumptions · ❌ Failed · ⬜ Unverified.

## Release rule
Cannot reach `DELIVERED` if any **must** requirement is ❌ or ⬜ unless the analyst records an explicit waiver (audited).

## Eval harness for the AI itself
- `evals/briefs/` labeled briefs with expected requirements, ambiguities, mappings.
- `evals/datasets/` golden datasets (synthetic e-commerce, SaaS, finance) with known answers.
- CI runs evals on every prompt/model change; thresholds block merge.
