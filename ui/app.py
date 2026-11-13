"""Dashboard Forge — Unified Streamlit Web Application (MVP Screens 1, 2, 3, 5, 6)."""

import asyncio
from pathlib import Path

import streamlit as st
import yaml

from dforge.agents.dashboard_designer import DashboardDesigner, DimensionBinding
from dforge.agents.metric_designer import MetricDesigner
from dforge.agents.requirements_service import RequirementsService
from dforge.agents.semantic_mapper import SemanticMappingPlan
from dforge.agents.sql_generator import SQLGenerator
from dforge.core.models import (
    FilterSpec,
    RequirementStatus,
    RequirementType,
)
from dforge.llm.provider import MockLLMProvider
from dforge.semantic.layer import SemanticLayer
from dforge.tools.bi.streamlit_renderer import StreamlitDashboardRenderer
from dforge.tools.connectors.duckdb_connector import DuckDBConnector

# Core and Phase services
from dforge.tools.parsers.document_parser import DocumentParser
from dforge.tools.profiling.eda_analyzer import QualityAndEDAAnalyzer
from dforge.tools.profiling.inferrer import RelationshipInferrer
from dforge.tools.profiling.profiler import DataProfiler
from dforge.tools.sql.sql_validator import SQLValidator

st.set_page_config(
    page_title="Dashboard Forge",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "project_id" not in st.session_state:
    st.session_state.project_id = "proj-retailco"
if "brief_text" not in st.session_state:
    st.session_state.brief_text = ""
if "requirements" not in st.session_state:
    st.session_state.requirements = []
if "gate1_approved" not in st.session_state:
    st.session_state.gate1_approved = False
if "gate2_approved" not in st.session_state:
    st.session_state.gate2_approved = False
if "metrics" not in st.session_state:
    st.session_state.metrics = []
if "dashboard_spec" not in st.session_state:
    st.session_state.dashboard_spec = None

DB_PATH = Path("evals/datasets/golden_ecommerce.duckdb")
if not DB_PATH.exists():
    from evals.datasets.create_golden_dataset import create_golden_ecommerce_dataset
    create_golden_ecommerce_dataset(DB_PATH)

connector = DuckDBConnector(DB_PATH)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("⚡ Dashboard Forge")
st.sidebar.caption("Spec-Driven AI BI Pipeline ($0 Local Stack)")
selected_screen = st.sidebar.radio(
    "Navigation",
    [
        "1. Intake & Brief (Screen 1 & 2)",
        "2. Requirements Board & Gate 1 (Screen 3)",
        "3. Data Profiling & EDA (Screen 5)",
        "4. Metric Dictionary & Gate 2 (Screen 6)",
        "5. Live SQL & Warehouse Query",
        "6. Dashboard Preview (Screen 7)",
    ],
)

st.sidebar.divider()
st.sidebar.subheader("Pipeline Gates")
st.sidebar.write(f"**Gate 1 (Requirements):** {'✅ APPROVED' if st.session_state.gate1_approved else '⏳ PENDING'}")
st.sidebar.write(f"**Gate 2 (Metrics & SQL):** {'✅ APPROVED' if st.session_state.gate2_approved else '⏳ PENDING'}")

# --- SCREEN 1 & 2: INTAKE & BRIEF ---
if selected_screen == "1. Intake & Brief (Screen 1 & 2)":
    st.header("📄 Client Brief Intake (Screen 1 & 2)")
    st.write("Upload a brief file (.txt, .md) or paste unstructured client requirements, meeting notes, or emails.")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader("Upload Brief Document", type=["txt", "md"])
        if uploaded_file is not None:
            st.session_state.brief_text = uploaded_file.read().decode("utf-8")

        pasted_text = st.text_area(
            "Or Paste Client Brief Text",
            value=st.session_state.brief_text,
            height=250,
            placeholder="Client: RetailCo. Need a sales dashboard tracking net revenue, completed orders, and product category...",
        )
        st.session_state.brief_text = pasted_text

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Load Sample Client Brief (RetailCo)", use_container_width=True):
                sample_path = Path("examples/sample-client-brief.md")
                st.session_state.brief_text = DocumentParser.parse_file(sample_path)
                st.rerun()

        with col_btn2:
            if st.button("Analyze & Decompose Brief 🚀", type="primary", use_container_width=True):
                if not st.session_state.brief_text.strip():
                    st.error("Please enter or upload a client brief first.")
                else:
                    # Run Extraction using Requirement Analyst and Clarifier Agent
                    mock_responses = {
                        "RequirementAnalysisResult": {
                            "project_id": st.session_state.project_id,
                            "summary": "Decomposed RetailCo brief into atomic requirements",
                            "requirements": [
                                {
                                    "id": "REQ-001",
                                    "text": "Calculate Net Revenue (excluding cancelled/test orders, refunds reduce revenue)",
                                    "type": "metric",
                                    "priority": "must",
                                    "source_citation": "Bullet 1 & 4",
                                    "confidence": 0.98,
                                },
                                {
                                    "id": "REQ-002",
                                    "text": "Count Total Completed Orders",
                                    "type": "metric",
                                    "priority": "must",
                                    "source_citation": "Bullet 1 & 4",
                                    "confidence": 0.99,
                                },
                                {
                                    "id": "REQ-003",
                                    "text": "Dimension slice: Product Category",
                                    "type": "dimension",
                                    "priority": "must",
                                    "source_citation": "Bullet 2",
                                    "confidence": 0.97,
                                },
                                {
                                    "id": "REQ-004",
                                    "text": "Interactive filter: Customer Region",
                                    "type": "filter",
                                    "priority": "should",
                                    "source_citation": "Bullet 2",
                                    "confidence": 0.95,
                                },
                            ],
                        },
                        "ClarificationReport": {
                            "has_ambiguity": True,
                            "questions": [
                                {
                                    "requirement_id": "REQ-001",
                                    "category": "business_definition",
                                    "question": "Does Net Revenue include tax and shipping?",
                                    "suggested_answers": [
                                        "Exclude tax and shipping (Product subtotal only)",
                                        "Include shipping, exclude tax",
                                        "Include both tax and shipping",
                                    ],
                                    "default_assumption": "Exclude tax and shipping",
                                }
                            ],
                        },
                    }
                    provider = MockLLMProvider(canned_responses=mock_responses)
                    service = RequirementsService(llm_provider=provider)
                    st.session_state.requirements = asyncio.run(
                        service.process_brief(st.session_state.project_id, st.session_state.brief_text)
                    )
                    st.session_state.gate1_approved = False
                    st.session_state.gate2_approved = False
                    st.session_state.metrics = []
                    st.session_state.dashboard_spec = None
                    st.success("Successfully decomposed into atomic requirements! Proceed to the Requirements Board.")

    with col2:
        st.subheader("Intake Info")
        st.info(f"**Project ID:** `{st.session_state.project_id}`\n\n**Source Warehouse:** DuckDB (Local $0)\n\n**Status:** Intake Active")

# --- SCREEN 3: REQUIREMENTS BOARD & GATE 1 ---
elif selected_screen == "2. Requirements Board & Gate 1 (Screen 3)":
    st.header("📋 Requirements Board & Gate 1 (Screen 3)")

    if not st.session_state.requirements:
        st.warning("No requirements found. Please ingest a brief in Screen 1 first.")
    else:
        st.write("Review extracted requirements, resolve any ambiguities, and approve Gate 1 to proceed.")

        for i, r in enumerate(st.session_state.requirements):
            with st.expander(f"{r.id} [{r.type.value.upper()}] — {r.text[:60]}...", expanded=True):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**Description:** {r.text}")
                    st.caption(f"**Source Citation:** {r.source_citation} | **Confidence:** {r.confidence * 100:.0f}%")
                with col_b:
                    st.write(f"**Priority:** `{r.priority.value}`")
                    st.write(f"**Status:** `{r.status.value}`")

                # Ambiguity handling
                if r.ambiguities:
                    st.warning("⚠️ **Ambiguity Detected (Constitution Principle 4: Ask, Don't Guess):**")
                    for amb in r.ambiguities:
                        st.write(f"**Question:** {amb.question}")
                        chosen_res = st.radio(
                            "Select Resolution:",
                            amb.suggested_answers,
                            key=f"amb_{r.id}",
                        )
                        if st.button(f"Resolve Ambiguity for {r.id}", key=f"btn_res_{r.id}"):
                            amb.resolution = chosen_res
                            r.status = RequirementStatus.APPROVED
                            st.success(f"Resolved {r.id} with '{chosen_res}'")
                            st.rerun()

        st.divider()
        st.subheader("Gate 1 Human Approval")
        if st.session_state.gate1_approved:
            st.success("✅ Gate 1 is Approved! Ready for Data Understanding and Metric Formulation.")
        else:
            if st.button("Approve Gate 1 (Requirements Sign-off) ✍️", type="primary"):
                approved = RequirementsService.approve_gate_1(st.session_state.requirements)
                if approved:
                    st.session_state.gate1_approved = True
                    st.success("✅ Gate 1 Approved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Gate 1 Blocked! You have unresolved ambiguities on 'must' priority requirements.")

# --- SCREEN 5: DATA PROFILING & EDA ---
elif selected_screen == "3. Data Profiling & EDA (Screen 5)":
    st.header("🔍 Data Profiling & Exploratory Data Analysis (Screen 5)")
    st.write("Discovered tables, schema definitions, null-handling diagnosis, and IQR outlier summaries.")

    profiler = DataProfiler(connector)
    eda = QualityAndEDAAnalyzer(connector)
    profiles = profiler.profile_all()

    tab_tables, tab_relationships = st.tabs(["Table Profiles & Quality", "Inferred Relationships & Joins"])

    with tab_tables:
        for tp in profiles:
            with st.expander(f"Table: {tp.table_name} ({tp.row_count} rows)", expanded=False):
                col_data = []
                for c in tp.columns:
                    col_data.append({
                        "Column": c.name,
                        "Type": c.data_type,
                        "Null Count": c.null_count,
                        "Null %": f"{c.null_percentage}%",
                        "Distinct": c.distinct_count,
                        "Candidate PK": "✅" if c.is_candidate_pk else "—",
                    })
                st.dataframe(col_data, use_container_width=True)

                # EDA Report
                eda_rep = eda.analyze_table_eda(tp)
                if eda_rep.null_diagnoses:
                    st.subheader("Null-Handling Diagnosis")
                    for nd in eda_rep.null_diagnoses:
                        st.info(f"**{nd.column_name}**: {nd.null_count} nulls ({nd.null_percentage}%). Strategy: `{nd.suggested_strategy}`. SQL: `{nd.recommended_sql}`")

                if eda_rep.outliers:
                    st.subheader("EDA Outliers (IQR Method)")
                    for o in eda_rep.outliers:
                        st.warning(f"**{o.column_name}**: Median {o.median}, IQR Bounds [{o.lower_bound}, {o.upper_bound}]. Found {o.outlier_count} outliers.")

    with tab_relationships:
        graph = RelationshipInferrer.infer_schema_graph(profiles)
        st.subheader("Inferred Join Paths")
        for rel in graph.relationships:
            st.write(f"🔗 `{rel.from_table}.{rel.from_column}` ➡️ `{rel.to_table}.{rel.to_column}` (Confidence: {rel.confidence})")

# --- SCREEN 6: METRIC DICTIONARY & GATE 2 ---
elif selected_screen == "4. Metric Dictionary & Gate 2 (Screen 6)":
    st.header("📐 Metric Dictionary & Gate 2 Approval (Screen 6)")
    st.write("Declarative YAML Semantic Layer and formula review before finalizing SQL.")

    if not st.session_state.gate1_approved:
        st.warning("Approve Gate 1 before generating metric definitions.")
    elif not st.session_state.metrics:
        if st.button("Generate Metric Definitions from Approved Requirements ⚙️", type="primary"):
            mock_metric_output = {
                "MetricDesignerOutput": {
                    "metrics": [
                        {
                            "name": "net_revenue",
                            "label": "Net Revenue ($)",
                            "description": "Total revenue subtracting refunds and line discounts",
                            "formula": "ROUND(SUM(line_total - COALESCE(discount_amount, 0)), 2)",
                            "dataset": "order_items",
                            "grain": "order_id",
                            "dimensions": ["products.category"],
                            "unit": "USD",
                            "requirement_ids": ["REQ-001", "REQ-003"],
                            "status": "draft",
                        },
                        {
                            "name": "total_completed_orders",
                            "label": "Completed Orders",
                            "description": "Distinct count of completed orders",
                            "formula": "COUNT(DISTINCT orders.order_id)",
                            "dataset": "orders",
                            "grain": "order_id",
                            "unit": "count",
                            "requirement_ids": ["REQ-002"],
                            "status": "draft",
                        },
                    ],
                    "self_critique": "Verified: Net revenue properly null-coalesces discount_amount and uses order grain.",
                }
            }
            provider = MockLLMProvider(canned_responses=mock_metric_output)
            designer = MetricDesigner(llm_provider=provider)
            mapping = SemanticMappingPlan(
                project_id=st.session_state.project_id,
                mappings=[
                    {"requirement_id": "REQ-001", "term": "Net Revenue", "target_table": "order_items", "target_column": "line_total", "transformation": "sum"},
                    {"requirement_id": "REQ-002", "term": "Completed Orders", "target_table": "orders", "target_column": "order_id", "transformation": "count"},
                ],
            )
            designer_res = asyncio.run(designer.design_metrics(st.session_state.requirements, mapping))
            st.session_state.metrics = designer_res.metrics
            st.rerun()
    else:
        for m in st.session_state.metrics:
            with st.expander(f"Metric: {m.label} (`{m.name}`)", expanded=True):
                st.write(f"**Formula:** `{m.formula}`")
                st.write(f"**Dataset / Grain:** `{m.dataset}` (grain: `{m.grain}`)")
                st.write(f"**Linked Requirements:** `{', '.join(m.requirement_ids)}`")

        st.subheader("Semantic Layer YAML Representation")
        layer = SemanticLayer()
        for m in st.session_state.metrics:
            layer.register_metric(m)
        st.code(layer.to_yaml(), language="yaml")

        st.divider()
        st.subheader("Gate 2 Metric Definition Approval")
        if st.session_state.gate2_approved:
            st.success("✅ Gate 2 Approved! Metric formulas and semantic contracts are locked.")
        else:
            if st.button("Approve Gate 2 (Metrics Sign-off) ✍️", type="primary"):
                for metric in st.session_state.metrics:
                    metric.status = "approved"
                st.session_state.gate2_approved = True
                st.session_state.dashboard_spec = None
                st.success("✅ Gate 2 Approved! Ready for Phase 4 Dashboard Build.")
                st.rerun()

# --- LIVE SQL & WAREHOUSE QUERY ---
elif selected_screen == "5. Live SQL & Warehouse Query":
    st.header("⚡ Live Dialect-Aware SQL & Dry-Run Execution")
    st.write("Generate dialect-aware SQL, run SQLGlot AST validation, and query DuckDB warehouse live.")

    if not st.session_state.metrics:
        st.info("Please generate metrics in Screen 6 first.")
    else:
        metric = st.session_state.metrics[0]
        schema_graph = RelationshipInferrer.infer_schema_graph(DataProfiler(connector).profile_all())
        generator = SQLGenerator(schema_graph=schema_graph, dialect="duckdb")

        dims = st.multiselect(
            "Select Dimensions to slice by:",
            ["products.category", "customers.region"],
            default=["products.category"],
        )
        flts = st.multiselect(
            "Select Filters:",
            ["orders.status = 'completed'"],
            default=["orders.status = 'completed'"],
        )

        gen_query = generator.generate_metric_query(metric=metric, dimensions=dims, filters=flts)

        st.subheader("Generated Dialect-Aware SQL")
        st.code(gen_query.sql, language="sql")

        validator = SQLValidator(connector=connector)
        val_res = validator.validate_sql(gen_query.sql)

        c1, c2, c3 = st.columns(3)
        c1.metric("AST Parsed", "✅ Yes" if val_res.ast_parsed else "❌ No")
        c2.metric("Read-Only Safety", "✅ Safe" if val_res.is_read_only else "❌ Forbidden")
        c3.metric("Dry-Run Warehouse", "✅ Success" if val_res.dry_run_success else "❌ Failed")

        st.subheader("Live DuckDB Execution Result")
        cols, rows = connector.execute_query(gen_query.sql)
        st.dataframe([dict(zip(cols, r)) for r in rows], use_container_width=True)

# --- SCREEN 7: DASHBOARD PREVIEW ---
elif selected_screen == "6. Dashboard Preview (Screen 7)":
    st.header("📊 Dashboard Preview (Screen 7)")
    st.write(
        "Design a validated, traceable DashboardSpec from approved metrics, then preview "
        "query-backed widgets in Streamlit."
    )
    if not st.session_state.gate1_approved or not st.session_state.gate2_approved:
        st.warning("Approve Gate 1 and Gate 2 before creating a dashboard.")
    elif not st.session_state.metrics:
        st.warning("Generate and approve metric definitions before creating a dashboard.")
    else:
        profiles = DataProfiler(connector).profile_all()
        schema_graph = RelationshipInferrer.infer_schema_graph(profiles)
        field_options = [
            f"{profile.table_name}.{column.name}"
            for profile in profiles
            for column in profile.columns
        ]
        approved_requirements = [
            requirement
            for requirement in st.session_state.requirements
            if requirement.status == RequirementStatus.APPROVED
        ]
        dimension_requirements = [
            requirement
            for requirement in approved_requirements
            if requirement.type == RequirementType.DIMENSION
        ]
        filter_requirements = [
            requirement
            for requirement in approved_requirements
            if requirement.type == RequirementType.FILTER
        ]
        dimension_options = [
            (metric.name, dimension)
            for metric in st.session_state.metrics
            for dimension in metric.dimensions
        ]
        dimension_mappings = {}
        if dimension_requirements:
            st.subheader("Confirm dashboard dimension mappings")
            for requirement in dimension_requirements:
                options = ["-- select approved metric dimension --", *dimension_options]
                selection = st.selectbox(
                    f"{requirement.text} ({requirement.id})",
                    options,
                    format_func=lambda value: (
                        value
                        if isinstance(value, str)
                        else f"{value[0]} — {value[1]}"
                    ),
                    key=f"dashboard_dimension_mapping_{requirement.id}",
                )
                if isinstance(selection, tuple):
                    dimension_mappings[requirement.id] = DimensionBinding(
                        metric_name=selection[0],
                        dimension=selection[1],
                    )

        filter_mappings = {}
        if filter_requirements:
            st.subheader("Confirm dashboard filter fields")
            for requirement in filter_requirements:
                options = ["-- select field --", *field_options]
                selected_field = st.selectbox(
                    f"{requirement.text} ({requirement.id})",
                    options,
                    key=f"dashboard_filter_mapping_{requirement.id}",
                )
                if selected_field != "-- select field --":
                    filter_mappings[requirement.id] = FilterSpec(
                        id=requirement.id.lower().replace("_", "-"),
                        label=requirement.text,
                        column=selected_field,
                        type="multi_select",
                        requirement_ids=[requirement.id],
                    )

        if st.button("Generate Dashboard Preview", type="primary"):
            validated_queries = {}
            generator = SQLGenerator(schema_graph=schema_graph, dialect="duckdb")
            query_validator = SQLValidator(connector=connector)
            for metric in st.session_state.metrics:
                generated = generator.generate_metric_query(metric=metric, dimensions=[])
                validated_queries[metric.name] = query_validator.validate_sql(generated.sql)
            try:
                st.session_state.dashboard_spec = DashboardDesigner().design_dashboard(
                    project_id=st.session_state.project_id,
                    title="RetailCo Dashboard",
                    requirements=approved_requirements,
                    metrics=st.session_state.metrics,
                    schema_graph=schema_graph,
                    profiles=profiles,
                    validated_queries=validated_queries,
                    dimension_mappings=dimension_mappings,
                    filter_mappings=filter_mappings,
                )
            except ValueError as exc:
                st.error(f"Dashboard design blocked: {exc}")

        if st.session_state.dashboard_spec is not None:
            dashboard_spec = st.session_state.dashboard_spec
            with st.expander("Validated DashboardSpec", expanded=False):
                st.code(
                    yaml.safe_dump(
                        dashboard_spec.model_dump(mode="json"),
                        sort_keys=False,
                        allow_unicode=True,
                    ),
                    language="yaml",
                )
            StreamlitDashboardRenderer(
                connector=connector,
                schema_graph=schema_graph,
                profiles=profiles,
            ).render(
                dashboard_spec,
                metrics=st.session_state.metrics,
                requirements=approved_requirements,
            )
