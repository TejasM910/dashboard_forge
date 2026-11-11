# 08 — Security, Privacy & Governance

- **Access**: read-only warehouse service accounts; per-project credentials via Secret Manager; no creds in prompts/logs.
- **RBAC**: admin / analyst / reviewer / client_viewer; project-level isolation (row-level security on metadata DB).
- **PII handling**: column classifier (name, email, phone, ID, address, financial) → excluded/hashed in profiles; only aggregates and masked samples reach the LLM; automated scan of prompt logs (AC-06).
- **SQL safety**: parse AST; allow `SELECT` only; block DDL/DML, multi-statements, external functions; enforce LIMIT/timeouts/byte-scan caps; dry-run before run.
- **LLM safety**: treat all client documents as untrusted (prompt-injection defense: documents are data, not instructions; tool calls validated against allowlist; outputs schema-validated).
- **Data residency**: configurable region; option to use enterprise LLM endpoints with zero data retention.
- **Audit**: immutable `AuditEvent` log for approvals, waivers, edits, data access, model/prompt versions.
- **Cost guardrails**: per-run budgets for tokens and bytes scanned; alerts and hard stops.
- **Compliance readiness**: DPDP/GDPR deletion workflow for project data; retention policy.
- **Multi-tenancy**: templates are **sanitized** (no client data/names) before promotion; promotion requires reviewer approval.
