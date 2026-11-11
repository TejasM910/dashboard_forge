# 10 — Template Library (kills the repetitive work)

## What is reusable
| Kind | Example |
|---|---|
| Metric | Net revenue, MRR, churn, CAC, conversion rate, AOV, retention cohort |
| Dataset pattern | orders+items+customers star, events sessionization |
| Layout | Executive overview, funnel page, cohort page, regional drill-down |
| Dashboard | Sales performance, Marketing funnel, SaaS metrics, Finance P&L, Ops SLA, HR attrition |
| Requirement patterns | "monthly X by Y with YoY" → known task plan |
| Clarifying-question sets | per domain (e.g., revenue definition checklist) |

## Mechanics
1. After extraction, embed each requirement; retrieve top-k similar templates (vector + keyword + domain filter).
2. Present match with similarity, definition diff, and past success rate → analyst accepts / adapts / rejects.
3. Adapting = parameterize (column mappings, filters, currency) rather than regenerate.
4. Promotion: approved artifacts → sanitize → reviewer approves → versioned template.
5. Feedback loop: usage count, pass rate, and analyst edits update template score.

## Seed library (v1)
Sales · Marketing/Funnel · SaaS subscription · E-commerce · Finance · Operations/SLA · HR · Customer support.
