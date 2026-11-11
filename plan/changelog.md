# Spec Changelog
- v0.1 (2026-11-11): Initial spec set created (planning only; no implementation started).
- v0.2 (2026-11-11): Adjusted tech stack in `specs/03-tech-stack.md` to a 100% Zero-Cost / Local-First architecture ($0 budget: Gemini free tier / local Ollama, DuckDB as local warehouse, local Postgres/Docker, and local Streamlit preview).
- v0.3 (2026-11-11): Phase 0 completed. Initialized project directory structure, pyproject.toml, virtual environment, core Pydantic schemas (`models.py`), LLM provider abstraction with Gemini free tier and Ollama providers (`provider.py`, `free_providers.py`), synthetic golden e-commerce dataset in DuckDB (`evals/datasets/golden_ecommerce.duckdb`), and passing Phase 0 test suite.
