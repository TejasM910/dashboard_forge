# 00 — Overview

## Problem
Data analysts repeatedly receive similar dashboard requests (sales, funnel, retention, ops, finance). Each time they: gather requirements → clarify → find data → define metrics → write SQL → build charts → test against expectations → rework. This is slow, repetitive, and error-prone.

## Vision
An "AI analyst co-pilot" that automates this loop end-to-end with human approval gates, reuses past work, and **proves** correctness before delivery.

## Goals
- G1: Convert free-form client requirements (text, docs, meeting notes, emails) into a structured requirement set.
- G2: Auto-split into tasks and execute them one by one with a visible plan.
- G3: Discover and understand the client's data (schema, grain, joins, quality).
- G4: Generate metric definitions, SQL and dashboards in a chosen BI tool.
- G5: Automatically test results against requirements and report accuracy.
- G6: Reuse templates/metrics across clients to cut repeat work by ≥70%.
- G7: Reduce analyst time per standard dashboard from days to hours.

## Non-Goals (v1)
- Not a replacement for the analyst's judgment on business meaning.
- Not building a new BI/visualization engine (we generate into existing tools).
- Not real-time streaming dashboards.
- Not automatic data cleaning/ETL of client sources (we detect & report issues).

## Personas
| Persona | Needs |
|---|---|
| **Analyst (primary)** | Fast intake, review/edit requirements, approve metrics, see test evidence |
| **Client / Stakeholder** | Answer clarifying questions, view/approve preview |
| **Admin / Data Engineer** | Connect data sources, manage templates, governance, cost |

## Success Metrics
| Metric | Target (v1) |
|---|---|
| Requirement coverage (requirements with ≥1 passing test) | ≥ 95% |
| Metric accuracy vs. independent reference calc | 100% within tolerance (see spec 06) |
| Analyst time saved on standard dashboards | ≥ 60% |
| Rework cycles after client review | ≤ 1 on average |
| Template reuse rate (requirements matched to library) | ≥ 50% after 20 projects |
| End-to-end run time (standard dashboard, ≤10 metrics) | ≤ 30 min machine time |
