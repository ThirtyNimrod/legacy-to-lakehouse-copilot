# Legacy-to-Lakehouse Migration Copilot: Project State & Implementation Overview

- **Timestamp**: 2026-10-11 01:29:31 (+05:30)
- **Environment**: Python 3.13.14 Virtual Environment (`.venv`)
- **Repository Root**: `d:\coding\github\legacy-to-lakehouse-copilot`
- **Orchestration**: LangGraph StateGraph (Deterministic Multi-Agent Architecture)
- **Local Compute & Storage**: Local DuckDB (Dual-Engine Source and Medallion Target)

---

## 1. Executive Summary & Objectives

The **Legacy-to-Lakehouse Migration Copilot** is an autonomous, deterministic multi-agent engineering system built with **LangGraph**. It automates the extraction, semantic profiling, dialect transpilation, Medallion structuring (Delta Lake / PySpark), deterministic parity reconciliation, and governance cataloging of legacy data warehouse workloads (Oracle, Netezza, Teradata) migrating to modern lakehouses (Databricks / Delta Lake).

### Key Architectural Tenets Implemented
1. **Deterministic Parity Validation**: Replaces subjective LLM evaluations with mathematical proofs computed by SQL execution engines (row counts, duplicate index checks, MD5 checksums, epsilon divergence $\le 10^{-6}$, null distributions).
2. **Decoupled Control and Compute Plane**: LangGraph coordinates logic while database interfaces are abstracted, enabling seamless switching between local DuckDB and Databricks Unity Catalog.
3. **Fail-Closed Self-Healing Loop**: Parity failures trigger diagnostic root-cause reports into a Fixer agent, which feeds back into the Translator agent up to a configurable maximum retry limit ($N=3$).
4. **Human-in-the-Loop (HITL) Governance Gate**: LangGraph native interruption (`interrupt_before=["human_approval"]`) checkpointed into SQLite (`SqliteSaver`), requiring human sign-off before governance assets are finalized.

---

## 2. Environment & Project Setup

### 2.1 Python Virtual Environment
- Initialized Python 3.13 virtual environment at `.venv`:
  ```powershell
  py -3.13 -m venv .venv
  ```
- Configured Python path in `pyproject.toml` (`pythonpath = ["."]`).

### 2.2 Package Manifest & Dependencies
- [pyproject.toml](file:///d:/coding/github/legacy-to-lakehouse-copilot/pyproject.toml) and [requirements.txt](file:///d:/coding/github/legacy-to-lakehouse-copilot/requirements.txt):
  - `langgraph>=0.2.20`: Multi-agent graph state orchestration.
  - `langchain-core>=0.3.0`: Base messages, prompts, runnables.
  - `langgraph-checkpoint-sqlite>=3.1.1`: SQLite-backed state persistence for HITL resume.
  - `sqlglot>=25.20.0`: AST parsing and dialect transpilation (Oracle $\to$ Spark SQL / DuckDB).
  - `duckdb>=1.1.0`: High-performance local SQL database engine for legacy emulation and Medallion tables.
  - `networkx>=3.4.0`: Directed acyclic graph (DAG) topological sorting for table dependencies.
  - `jinja2>=3.1.4`: Structural code generation templates for Databricks PySpark notebooks.
  - `pydantic>=2.9.0` & `pydantic-settings>=2.5.0`: Validated configuration management.
  - `rich>=13.9.0`: Terminal UI formatting for CLI run feedback.
  - `pytest>=8.3.0` & `pytest-asyncio>=0.24.0`: Automated test suite.

### 2.3 Configuration Files
- [configs/settings.yaml](file:///d:/coding/github/legacy-to-lakehouse-copilot/configs/settings.yaml): Application settings (tolerances, retries, database paths).
- [.env.example](file:///d:/coding/github/legacy-to-lakehouse-copilot/.env.example): Environment template for LLM provider configuration and paths.
- [.gitignore](file:///d:/coding/github/legacy-to-lakehouse-copilot/.gitignore): Excludes `.venv`, DuckDB databases (`*.duckdb`), SQLite checkpoint files (`checkpoints.db`), and cache directories.

---

## 3. Core Architecture & State Machine

### 3.1 State Space Definition ([src/core/state.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/core/state.py))
The system formalizes migration as a typed state machine over `MigrationState`:
- `messages: Annotated[List[BaseMessage], add_messages]`: Agent communication history.
- `source_dialect: str`: Source database engine dialect (`"Oracle"`).
- `raw_ddl_map: Dict[str, str]`: Mapping of table/view names to raw source DDL statements.
- `profiles: Dict[str, List[ColumnProfile]]`: Column datatypes, nullability, sensitivity flags, sample values.
- `lineage_graph: Dict[str, TableLineage]`: Table dependency adjacency mapping and depth.
- `execution_order: List[str]`: Topologically sorted sequence of tables to migrate.
- `current_table: str`: Table currently traversing the migration lifecycle.
- `artifacts: Dict[str, CodeArtifact]`: Generated PySpark notebook code (Bronze, Silver, Gold).
- `validation_metrics: List[ParityMetric]`: Quantitative divergence proofs.
- `validation_passed: bool`: Flag indicating whether all parity assertions succeeded.
- `fix_attempts: int` & `max_retries: int`: Bounded repair loop counters.
- `diagnostic_feedback: Optional[str]`: Structured root-cause payload from the Fixer.
- `human_approved: bool` & `human_feedback: Optional[str]`: Operator review state.
- `catalog_metadata: Dict[str, Dict[str, str]]`: Unity Catalog tagging and documentation scripts.
- `final_migration_report: Optional[str]`: Comprehensive Markdown runbook.

### 3.2 StateGraph Assembly ([src/core/graph.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/core/graph.py))
```
                      ┌───────────────┐
                      │    [START]    │
                      └───────┬───────┘
                              │
                              ▼
                      ┌───────────────┐
                      │   Profiler    │
                      └───────┬───────┘
                              │
                              ▼
            ┌────────►┌───────────────┐
            │         │  Translator   │
            │         └───────┬───────┘
            │                 │
            │                 ▼
            │         ┌───────────────┐
            │         │   Validator   │
            │         └───────┬───────┘
            │                 │
 [Fix Attempts < Max]         ▼
            │           Conditional
     ┌──────┴──────┐    Parity Split
     │    Fixer    │◄─────────┘
     └─────────────┘          │ [Passed OR Attempts >= Max]
                              ▼
                      ┌───────────────┐
                      │ HumanApproval │ (interrupt_before)
                      └───────┬───────┘
                              │
               ┌──────────────┴──────────────┐
               │ Approved                    │ Rejected / Abort
               ▼                             ▼
       ┌───────────────┐             ┌───────────────┐
       │    Steward    │             │   [ABORT]     │
       └───────┬───────┘             └───────────────┘
               │
               ▼
       ┌───────────────┐
       │     [END]     │
       └───────────────┘
```

---

## 4. Multi-Agent System Implementation

### 4.1 Profiler Agent ([src/agents/profiler.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/profiler.py))
- **AST Parsing**: Uses `sqlglot.parse_one(..., read="oracle")` to extract columns, primary keys, and table references.
- **Topological Lineage**: Builds a `networkx.DiGraph()` of table relationships and computes valid execution order via `nx.topological_sort()`.
- **Privacy Scanner**: Uses compiled regex patterns (`PII_EMAIL`, `PII_CPF`, `PII_PHONE`) to scan sample data rows and mark sensitive columns.
- **Semantic Inference**: Maps legacy datatypes to Lakehouse Delta types (e.g. `VARCHAR` $\to$ `STRING`, `DOUBLE` $\to$ `DECIMAL(18, 2)`).

### 4.2 Translator Agent ([src/agents/translator.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/translator.py))
- **PySpark Medallion Templates**: Renders production Databricks PySpark scripts via Jinja2:
  - **Bronze**: Auto Loader (`spark.readStream.format("cloudFiles")`) append-only ingestion with metadata columns (`_ingest_timestamp`, `_source_file`, `_rescued_data`).
  - **Silver**: Deterministic window deduplication (`row_number().over(Window.partitionBy(pk).orderBy(ingest_date.desc(), pk.asc()))`) and SHA-256 PII redaction (`F.sha2(col, 256)`).
- **Target Local Execution**: Replicates transformations into target DuckDB tables (`bronze_{table}` and `silver_{table}`) without file-locking conflicts, enabling local validation.

### 4.3 Validator Agent ([src/agents/validator.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/validator.py))
- Concurrently queries legacy DuckDB source and target Lakehouse DuckDB.
- Executes 5 mathematical parity assertions:
  1. **Row Cardinality / Deduplicated Entity Balance**: Checks expected unique entity counts match target rows.
  2. **Duplicate Index Parity**: Asserts target primary key duplicate count is zero: $(N_{\text{target}} - |\text{DISTINCT } K_{\text{pk}}|) = 0$.
  3. **Bitwise / MD5 Checksum Equivalence**: Computes hash of concatenated row attributes.
  4. **Numeric Epsilon Variance**: $\left|\frac{\sum x_{\text{target}} - \sum x_{\text{source}}}{\sum x_{\text{source}}}\right| \le 10^{-6}$.
  5. **Null Distribution Invariance**: Compares null ratios across attributes.

### 4.4 Fixer Agent ([src/agents/fixer.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/fixer.py))
- Discrepancy root-cause diagnostician:
  - Deduplication tie-breaker ambiguity $\to$ prescribes unique primary key tie-breaker.
  - Floating-point currency drift $\to$ prescribes `DECIMAL(18, 2)` casting.
  - Empty string vs. null semantics $\to$ prescribes `NULLIF(TRIM(col), '')`.
- Emits structured diagnostic payloads and increments `fix_attempts`.

### 4.5 Steward Agent ([src/agents/steward.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/steward.py))
- Generates Unity Catalog governance DDL statements:
  - `COMMENT ON TABLE lakehouse.silver.{table} IS '...';`
  - `ALTER TABLE ... ALTER COLUMN {col} SET TAGS ('classification' = 'pii', 'compliance' = 'gdpr');`
- Generates structured Markdown migration runbooks saved to `docs/runbooks/migration_runbook_{table}.md`.

---

## 5. Test Harness & Antipattern Emulation ([src/tools/harness.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/tools/harness.py))

Generates a synthetic Olist e-commerce database in DuckDB (`legacy_warehouse.duckdb`) embedding 6 historical data warehouse quirks:
1. `raw_customers`: Obfuscated column names (`CUST_LST_ADDR_ID_TX`, `CUST_NAT_DOC_NUM_ID`) with sensitive PII (tax IDs, emails, phone numbers).
2. `raw_categories`: Hierarchical self-referential categories (`parent_category_id`).
3. `raw_orders`: Mixed date format strings (`2023-01-15 10:20:00` vs. `16/01/2023`), delimited status histories (`NEW;PAID;SHIPPED`), and duplicate rows with identical ingest timestamps.
4. `raw_order_payments`: Unscaled `DOUBLE` floating-point currency amounts.
5. `raw_order_items`: Foreign key joins with item prices and freight values.
6. `v_order_summary`: Legacy Oracle view layer with `CASE/DECODE`, `NVL/COALESCE`, and string joins.

---

## 6. LLM Provider Factory & Offline Mock ([src/llm/factory.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/llm/factory.py))

Supports dynamic model switching configured via `.env` / `settings.yaml`:
- **Mock Mode (`provider: "mock"`)**: Deterministic offline model returning synthetic profiling mappings, root-cause diagnostics, and catalog tags. Enables 100% CI/CD test execution with 0 API tokens expended.
- **Google Gemini**: Uses `langchain-google-genai` (`gemini-2.5-flash`).
- **OpenAI**: Uses `langchain-openai` (`gpt-4o`).
- **Ollama**: Uses `langchain-community` for local offline models (`qwen2.5-coder`).

---

## 7. Interactive CLI Runner ([src/cli.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/cli.py))

Provides command-line operations:
```powershell
# 1. Seed legacy warehouse with synthetic tables & antipatterns
.\.venv\Scripts\python.exe -m src.cli seed

# 2. Run migration graph (executes Profiler, Translator, Validator, then halts at Human Gate)
.\.venv\Scripts\python.exe -m src.cli run --table raw_orders --thread-id demo01

# 3. Resume from checkpoint after human operator review
.\.venv\Scripts\python.exe -m src.cli resume --thread-id demo01 --action approve
```

---

## 8. Verification Results

### 8.1 Automated Test Suite
All 7 unit and integration tests passed:
```
tests/test_fixer.py::test_fixer_generates_diagnostic_report PASSED       [ 14%]
tests/test_graph_e2e.py::test_migration_graph_e2e_with_hitl PASSED       [ 28%]
tests/test_harness.py::test_harness_seeds_expected_entities PASSED       [ 42%]
tests/test_metrics.py::test_parity_metrics_assertions PASSED             [ 57%]
tests/test_profiler.py::test_profiler_detects_pii_and_lineage PASSED     [ 71%]
tests/test_translator.py::test_translator_generates_pyspark_artifacts PASSED [ 85%]
tests/test_validator.py::test_validator_detects_parity PASSED            [100%]

============================== 7 passed in 3.69s ==============================
```

### 8.2 End-to-End CLI Verification
1. **Seeding**: Successfully created 6 legacy tables and views.
2. **Graph Run**: Paused at `Human Approval Gate` with thread ID `demo01` with all parity metrics verified:
   - `duplicate_index_parity`: OK (divergence=0.0)
   - `null_distribution_order_purchase_date_str`: OK (divergence=0.0)
   - `deduplicated_cardinality_balance`: OK (divergence=0.0)
3. **Resume Run**: Approved checkpoint resumed state and invoked Steward Agent, producing the final migration runbook at [docs/runbooks/migration_runbook_raw_orders.md](file:///d:/coding/github/legacy-to-lakehouse-copilot/docs/runbooks/migration_runbook_raw_orders.md).

---

## 9. File Tree Summary

```
legacy-to-lakehouse-copilot/
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt
├── configs/
│   └── settings.yaml
├── data/
│   ├── legacy/
│   │   └── legacy_warehouse.duckdb (gitignored)
│   └── medallion/
│       └── lakehouse_medallion.duckdb (gitignored)
├── docs/
│   ├── plan/
│   │   └── initial-plan.md
│   ├── runbooks/
│   │   └── migration_runbook_raw_orders.md
│   ├── state/
│   │   └── legacy-lakehouse-copilot-state-202610110129.md
│   └── verify/
│       └── powershell.md
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── fixer.py
│   │   ├── profiler.py
│   │   ├── steward.py
│   │   ├── translator.py
│   │   └── validator.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── checkpointer.py
│   │   ├── graph.py
│   │   └── state.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── factory.py
│   └── tools/
│       ├── __init__.py
│       ├── database.py
│       ├── harness.py
│       └── metrics.py
└── tests/
    ├── conftest.py
    ├── test_fixer.py
    ├── test_graph_e2e.py
    ├── test_harness.py
    ├── test_metrics.py
    ├── test_profiler.py
    ├── test_translator.py
    └── test_validator.py
```
