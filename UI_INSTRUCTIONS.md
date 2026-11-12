# Dashboard Forge — UI Quickstart Guide

This guide explains how to launch and use the interactive **Dashboard Forge Web UI** on your local machine ($0 Zero-Cost Stack).

---

## 1. Quick Launch

Open PowerShell in the project root directory and run:

```powershell
# Set PYTHONPATH and start the Streamlit web app
$env:PYTHONPATH="src"
.\.venv\Scripts\streamlit.exe run ui/app.py
```

The browser will automatically open to:
👉 **`http://localhost:8501`**

---

## 2. Walkthrough of Available Screens

### Screen 1 & 2: Client Brief Intake
- **Upload or Paste**: Upload a `.txt` or `.md` brief, or click **"Load Sample Client Brief (RetailCo)"**.
- **Run Intake**: Click **"Analyze & Decompose Brief 🚀"**. The Requirement Analyst and Clarifier Agents will extract atomic requirements and detect ambiguities.

### Screen 3: Requirements Board & Gate 1
- **Review Cards**: Inspect extracted metrics, dimensions, filters, confidence scores, and source citations.
- **Resolve Ambiguities**: Select recommended answers for detected ambiguities (Principle 4: *Ambiguity is asked, not guessed*).
- **Gate 1 Approval**: Click **"Approve Gate 1"**. The pipeline validates that no "Must" requirements have open ambiguities before proceeding.

### Screen 5: Data Profiling & EDA
- **Table Catalog**: Browse discovered DuckDB tables (`customers`, `orders`, `order_items`, `products`), row counts, null %, and candidate primary keys.
- **Null-Handling Diagnosis**: View recommended SQL coalescing strategies (`COALESCE(col, 0)`, `COALESCE(col, 'Unknown')`).
- **Outlier Detection**: View statistical IQR distribution boundaries and detected anomaly counts.
- **Joins Graph**: View automatically inferred foreign key join relationships.

### Screen 6: Metric Dictionary & Gate 2
- **Metric Designer**: Review generated formulas with self-critique.
- **Semantic Layer YAML**: Inspect the versioned declarative metric contract.
- **Gate 2 Approval**: Click **"Approve Gate 2"** to lock metric definitions before SQL generation.

### Live Dialect-Aware SQL & Dry-Run
- Select dimensions (e.g. `products.category`, `customers.region`) and filters.
- View transpiled SQL with **SQLGlot AST Validation Badges** (`AST Parsed`, `Read-Only Safety`, `Dry-Run Warehouse`).
- View real-time query results executed against DuckDB.

---

## 3. Running Automated Tests

To run the complete test suite at any time:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
