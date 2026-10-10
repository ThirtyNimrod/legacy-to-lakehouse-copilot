# Legacy-to-Lakehouse Migration Copilot
## Architectural Blueprint & Theoretical Plan

---

## 1. Executive Summary & Problem Framing

Enterprise data migrations from legacy relational data warehouses (e.g., Teradata, Netezza, Oracle, Exadata) to modern lakehouses (Databricks / Delta Lake) are fraught with semantic drift, undocumented business logic, hidden data quality degradation, and significant manual translation overhead. 

The **Legacy-to-Lakehouse Migration Copilot** is a deterministic, multi-agent system built on **LangGraph**. It automates the extraction, dialect translation, data structuring (Medallion Architecture), quantitative validation, and governance cataloging of legacy workloads. By decoupling business logic analysis, code compilation, mathematical validation, and governance enforcement into specialized agents, the system achieves a verifiable, closed-loop migration pipeline with human-in-the-loop (HITL) safety controls.

---

## 2. Core Architectural Principles

1. **Deterministic Ground-Truth Validation**: LLMs are nondeterministic code generators; they cannot be trusted to verify their own outputs. Validation is outsourced to deterministic SQL execution engines that compute mathematical parity proofs between source and target systems.
2. **Decoupled Control and Compute Plane**: The orchestration graph (LangGraph) maintains clean tool interfaces for source databases, target databases, and logging backends. This permits seamless transitions from a 100% local mock runtime (DuckDB + SQLite) to a hybrid cloud configuration (Databricks Serverless + Unity Catalog) without refactoring graph topology.
3. **Fail-Closed Safety with Capped Repair Loops**: Faulty code generation triggers diagnostic feedback cycles capped at $N$ iterations. If reconciliation checks fail after $N$ iterations, the state machine halts and escalates to human review.
4. **Governed by Design**: Documentation, data masking, and Unity Catalog metadata tags are treated as first-class migration artifacts generated concurrently with the transformed data pipelines.

---

## 3. Mathematical State Machine Formulation

The migration system is formalized as a finite state machine $(S, \Sigma, T, s_0, F)$ governed by a structured shared state.

```
                              ┌──────────────────────┐
                              │      [START]         │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │    Profiler Node     │
                              └──────────┬───────────┘
                                         │
                                         ▼
                    ┌────────►┌──────────────────────┐
                    │         │   Translator Node    │
                    │         └──────────┬───────────┘
                    │                    │
                    │                    ▼
                    │         ┌──────────────────────┐
                    │         │    Validator Node    │
                    │         └──────────┬───────────┘
                    │                    │
      [Fix Attempts < Max]               │
                    │                    ▼
             ┌──────┴───────┐      Conditional
             │  Fixer Node  │◄──── Parity Split
             └──────────────┘            │
                                         │ [Passed OR Attempts >= Max]
                                         ▼
                              ┌──────────────────────┐
                              │ Human Approval Gate  │  <-- LangGraph Interrupt
                              └──────────┬───────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         │ Approved                      │ Rejected
                         ▼                               ▼
              ┌──────────────────────┐        ┌──────────────────────┐
              │     Steward Node     │        │     ABORT / HALT     │
              └──────────┬───────────┘        └──────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │        [END]         │
              └──────────────────────┘
```

### 3.1 State Schema Definition

The shared state space $S$ contains conversational history, structural metadata, code artifacts, numeric verification metrics, and lifecycle flags:

```python
from typing import Annotated, Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ColumnProfile(TypedDict):
    column_name: str
    legacy_type: str
    target_type: str
    is_nullable: bool
    is_primary_key: bool
    is_sensitive: bool
    sensitivity_type: Optional[Literal["PII", "PCI", "FINANCIAL", "INTERNAL"]]
    sample_values: List[str]

class TableLineage(TypedDict):
    table_name: str
    upstream_dependencies: List[str]
    downstream_dependents: List[str]
    transformation_depth: int

class CodeArtifact(TypedDict):
    source_entity: str
    target_entity: str
    layer: Literal["bronze", "silver", "gold"]
    pyspark_code: str
    ddl_statement: str
    execution_status: Literal["pending", "executed", "failed"]

class ParityMetric(TypedDict):
    metric_name: str
    source_metric: Any
    target_metric: Any
    divergence_score: float
    tolerance_threshold: float
    passed: bool
    error_message: Optional[str]

class MigrationState(TypedDict):
    # Message log for multi-agent LLM communication
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Static Profiling Context
    source_dialect: str                          # e.g., "Oracle", "Netezza", "Teradata"
    raw_ddl_map: Dict[str, str]                  # Table name -> Raw DDL statement
    profiles: Dict[str, List[ColumnProfile]]     # Table name -> Column metadata
    lineage_graph: Dict[str, TableLineage]       # NetworkX-compatible adjacency mapping
    execution_order: List[str]                   # Topologically sorted table list
    
    # Active Migration Workspace
    current_table: str                           # Active table under migration
    artifacts: Dict[str, CodeArtifact]           # Layer -> Generated PySpark artifacts
    
    # Verification & Error Recovery
    validation_metrics: List[ParityMetric]
    validation_passed: bool
    fix_attempts: int
    max_retries: int
    diagnostic_feedback: Optional[str]
    
    # Governance & Approval
    human_approved: bool
    human_feedback: Optional[str]
    catalog_metadata: Dict[str, Dict[str, str]]  # Table/Column descriptions and tags
    final_migration_report: Optional[str]
```

---

## 4. Multi-Agent System Specification

### 4.1 Profiler Agent
* **Role**: Structural Reverse Engineer & Data Privacy Assessor.
* **Inputs**: Raw legacy DDLs, system catalog metadata (`sqlite_master`, `information_schema`), sample data payloads.
* **Deterministic Tools**:
  * `SQLGlot` parser: Builds ASTs to extract source table relationships, column datatypes, and view dependencies.
  * `NetworkX` engine: Computes topological sorting to resolve table migration execution orders.
  * PII Regex Engine: Scans column identifiers and string contents against standard entity formats (e.g., Brazilian CPF/CNPJ, Email, Phone, Credit Card).
* **LLM Responsibility**: Infers semantic meaning for obfuscated column names (e.g., `CUST_LST_ADDR_ID_TX`) and maps them to descriptive lakehouse schemas.
* **Output State Mutation**: Populates `profiles`, `lineage_graph`, and `execution_order`.

### 4.2 Translator Agent
* **Role**: Polyglot Data Engineer (Legacy SQL to Delta Lake PySpark).
* **Inputs**: Profiler metadata, active table legacy DDL/view SQL, `diagnostic_feedback` (if in a repair cycle).
* **Deterministic Tools**:
  * AST Transpiler (`SQLGlot` dialect transpile): Pre-processes baseline ANSI conversions.
  * Template Engine (Jinja2): Enforces structural standards for Databricks notebooks.
* **LLM Responsibility**: Refactors non-transpilable procedural code, dialect-specific analytical expressions, and recursive subqueries into PySpark DataFrame transformations aligned to Medallion standards:
  * **Bronze Layer**: Appends raw ingestion schemas with append-only metadata (`_ingest_timestamp`, `_source_file`, `_rescued_data`).
  * **Silver Layer**: Applies deduplication via window functions (`row_number().over(...)`), schema casting, timestamp standardization, PII redaction/tokenization, and referential validation.
  * **Gold Layer**: Implements star-schema dimensional modeling, surrogate key assignments, and domain-level aggregation rollups.
* **Output State Mutation**: Populates `artifacts[layer]` with deployable PySpark script strings.

### 4.3 Validator Agent
* **Role**: Deterministic Reconciliation Engine.
* **Inputs**: Executable artifacts, legacy source database, target Lakehouse environment.
* **Deterministic Tools**:
  * Dual-Engine Query Runner: Concurrently fires analytical queries against DuckDB (Legacy) and the Lakehouse Target (DuckDB local or Unity Catalog Delta).
* **Parity Assertions**:
  1. *Row Cardinality Balance*:
     $$\Delta_{\text{count}} = \left| N_{\text{source}} - N_{\text{target}} \right| = 0$$
  2. *Duplicate Index Parity*:
     $$\delta_{\text{dup}} = \left( N_{\text{target}} - \left| \text{DISTINCT } \mathbf{K}_{\text{pk}} \right| \right) = 0$$
  3. *Bitwise/MD5 Checksum Equivalence*:
     $$\sum_{i=1}^N \text{MD5}(c_{i, 1} \parallel c_{i, 2} \parallel \dots \parallel c_{i, k})_{\text{source}} - \sum_{i=1}^N \text{MD5}(c_{i, 1}' \parallel c_{i, 2}' \parallel \dots \parallel c_{i, k}')_{\text{target}} = 0$$
  4. *Numeric Metric Epsilon Variance*:
     $$\epsilon = \left| \frac{\sum_{i=1}^N x_{i, \text{target}} - \sum_{i=1}^N x_{i, \text{source}}}{\sum_{i=1}^N x_{i, \text{source}}} \right| \le 10^{-6}$$
  5. *Null Distribution Invariance*:
     $$\left| \frac{\text{NullCount}(c)_{\text{source}}}{N_{\text{source}}} - \frac{\text{NullCount}(c')_{\text{target}}}{N_{\text{target}}} \right| = 0$$
* **Output State Mutation**: Produces `validation_metrics` and sets boolean flag `validation_passed`.

### 4.4 Fixer Agent
* **Role**: Dialect Discrepancy & Semantic Root-Cause Diagnostician.
* **Inputs**: Failed `validation_metrics`, execution error traces, failing PySpark code, original legacy source SQL.
* **Analysis Taxonomy**:
  * *Null Semantics Mismatch*: Resolves divergences caused by Oracle treating empty strings `''` as `NULL`, whereas Spark distinguishes between empty strings and `NULL`.
  * *Integer Division & Truncation*: Identifies differences where legacy engines perform integer floor division (`5 / 2 = 2`) while Spark returns floating points (`5 / 2 = 2.5`).
  * *Datetime/Timezone Conversions*: Resolves variances between Oracle `DATE` (which includes times) and Spark `DATE` (dates only) vs `TIMESTAMP`.
  * *Sorting Order in Window Framing*: Fixes `NULLS FIRST` vs `NULLS LAST` ambiguities in window functions producing non-deterministic rank assignments.
* **Output State Mutation**: Increments `fix_attempts += 1`, writes detailed code modification guidance to `diagnostic_feedback`, and routes control back to `Translator`.

### 4.5 Human Approval Gate (Breakpoint)
* **Role**: Operational Oversight & Production Deployment Governor.
* **Mechanics**: Implemented using LangGraph native `interrupt_before=["human_approval"]`. The state graph persists to the SQLite checkpointer and awaits an external `update_state` payload.
* **Operator Decision**:
  * **Approve**: Persists state to `Steward`.
  * **Reject with Feedback**: Operator inputs corrective text, routed into `Fixer`.
  * **Abort**: Terminates migration run for manual engineering takeover.

### 4.6 Steward Agent
* **Role**: Data Governance Specialist & Audit Reporter.
* **Inputs**: Lineage graph, data profiles, validated PySpark transformations, parity verification audit logs.
* **Outputs**:
  * Unity Catalog DDL Scripts: Generates `COMMENT ON TABLE`, `COMMENT ON COLUMN`, and tag assignments (`SET TAGS ('classification' = 'pii')`).
  * Markdown Migration Runbook: Executive and technical summary detailing schema mapping, legacy code antipatterns resolved, parity checks executed, and retry telemetry.
* **Output State Mutation**: Populates `catalog_metadata` and `final_migration_report`.

---

## 5. Legacy Antipattern Simulation (Olist E-Commerce)

The local test harness builds an enterprise-style legacy schema in DuckDB utilizing the Brazilian E-Commerce public dataset (Olist), artificially degraded with historical warehouse antipatterns.

### 5.1 Legacy Quirks Injection Matrix

| Antipattern Category | Synthetic Implementation | Target Lakehouse Pattern (Medallion) |
| :--- | :--- | :--- |
| **Vendor Dialect SQL** | Stored view with Oracle `DECODE()`, `NVL2()`, and string concatenation operator `\|\|`. | Standard Spark SQL conditional expressions (`CASE WHEN`, `coalesce()`, `concat()`). |
| **Hierarchical Queries** | Category taxonomy represented as parent-child self-joins using Oracle `CONNECT BY PRIOR`. | Transpiled into PySpark recursive DataFrame joins or path-enumerated arrays. |
| **Dirty Types & Casting** | Timestamps stored as irregular strings: `YYYY-MM-DD HH:MI:SS` mixed with `DD/MM/YYYY`. | Bronze retains raw string; Silver parses via `to_timestamp()` with conditional format masks. |
| **Implicit Truncation** | Money amounts stored as unscaled `DOUBLE` or non-standard fixed-width strings. | Standardized to `DECIMAL(18, 2)` to eliminate floating-point drift. |
| **Denormalized Arrays** | Delimited strings stored in a single column (e.g., status changes: `"NEW;PAID;SHIPPED"`). | Silver extracts strings via `split()`; Gold transforms arrays into tabular transaction events. |
| **Non-Deterministic Deduplication** | Vendor-specific `QUALIFY ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY ingest_date)` missing explicit tie-breakers. | Explicit tie-breaker logic added in Silver layer to guarantee deterministic replayability. |

---

## 6. Three-Phase Migration Strategy

```
Phase 1: Pure Local Sandbox
┌──────────────────────────────────────────────────────────┐
│ Machine / Host Runtime                                   │
│  - Orchestrator: LangGraph Engine                        │
│  - Legacy DB: DuckDB ("legacy_warehouse.db")             │
│  - Target DB: DuckDB ("lakehouse_medallion.db")          │
│  - LLM: Local Ollama / External API                      │
│  - Tracking: Local MLflow Instance                       │
│  - Checkpointing: Local SQLite DB                        │
└──────────────────────────────────────────────────────────┘
                            │
                            ▼
Phase 2: Hybrid Lakehouse Backend
┌──────────────────────────────────────────────────────────┐
│ Machine / Host Runtime                                   │
│  - Orchestrator: LangGraph Engine                        │
│  - Legacy DB: DuckDB (Source)                            │
│  - Target Execution: databricks-sql-connector            │
│  - LLM: External Model API                               │
│  - Tracking: MLflow Tracking URI -> Databricks Workspace │
└───────────────────────────┬──────────────────────────────┘
                            │ (Direct Delta Execution)
                            ▼
┌──────────────────────────────────────────────────────────┐
│ Databricks Free Workspace (Target & Governance)          │
│  - Unity Catalog: Catalog.Schema.Delta_Tables            │
│  - MLflow: Experiment Tracking & Agent Traces            │
└──────────────────────────────────────────────────────────┘
                            │
                            ▼
Phase 3: Native Databricks Execution
┌──────────────────────────────────────────────────────────┐
│ Databricks Free Workspace (Unified Lakehouse)            │
│  - Workflows: Generated PySpark deployed as Jobs Tasks   │
│  - Compute: Serverless Notebook Execution                │
│  - Catalog: Unity Catalog Lineage & Tagging Engine       │
│  - Observability: MLflow Trace UI & Run Evaluation       │
└──────────────────────────────────────────────────────────┘
```

### 6.1 Phase 1: Pure Local Sandbox
* **Objective**: Validate multi-agent state graphs, AST parsing, parity engines, and the repair loop without cloud friction or network latency.
* **Data Layer**: DuckDB holds both legacy source schemas and output Medallion tables in local `.duckdb` files.
* **Execution**: Local Python processes run LangGraph. Source and target queries execute across independent DuckDB connections.
* **Observability**: A local SQLite-backed MLflow tracking server captures prompt tokens, run latencies, and node transitions.

### 6.2 Phase 2: Hybrid Lakehouse Backend
* **Objective**: Bridge the local LangGraph supervisor with remote Databricks compute and Unity Catalog governance.
* **Storage & Governance**: Connect to Databricks Free Tier via `databricks-sql-connector`. PySpark DDL and Delta table writes execute directly in Unity Catalog.
* **Telemetry**: Redirect experiment tracking by configuring environment parameters:
  ```python
  import mlflow
  mlflow.set_tracking_uri("databricks")
  mlflow.set_experiment("/Users/user@domain.com/legacy_migration_copilot")
  ```
* **LLM Architecture**: Run the LLM orchestrator outside Databricks on the local host. This bypasses the Foundation Model Serving / GPU limits present on the Databricks Free Tier while capitalizing on remote Delta storage and Unity Catalog governance.

### 6.3 Phase 3: Native Databricks Execution
* **Objective**: Automate the execution of generated assets using native Databricks platform capabilities.
* **Production Deployment**: Compile the verified PySpark scripts generated by the Translator into a Databricks Workflow (Multi-Task Job):
  * Task 1: `bronze_ingestion_job`
  * Task 2: `silver_cleaning_job` (depends on Task 1)
  * Task 3: `gold_aggregation_job` (depends on Task 2)
* **Agent Operations**: Run the LangGraph orchestration notebook interactively inside the workspace or wrap it as an automated setup job.
* **Governance Application**: The Steward agent executes SQL scripts to register tags and documentation directly to Unity Catalog:
  ```sql
  ALTER TABLE main.lakehouse.silver_orders 
  SET TAGS ('confidentiality' = 'restricted', 'pipeline' = 'migration_copilot');
  ```

---

## 7. Observability, Evaluation & Error Feedback Loops

### 7.1 Quantitative Evaluation Metric Suite

The system does not evaluate migration quality via subjective text analysis. It evaluates outcomes across four objective operational dimensions:

1. **Parity Success Rate ($PSR$)**:
   $$PSR = \frac{\sum \text{Passed Assertions}}{\sum \text{Total Executed Assertions}} \times 100\%$$
2. **First-Pass Translation Rate ($FPTR$)**:
   $$FPTR = \frac{N_{\text{tables}}(\text{Passing with } 0 \text{ retries})}{N_{\text{total tables}}}$$
3. **Repair Loop Convergence ($RLC$)**:
   $$RLC = \frac{1}{|T_{\text{repaired}}|} \sum_{t \in T_{\text{repaired}}} \text{fix\_attempts}_t \quad (\text{Target} \le 2.0)$$
4. **Token Cost to Parity ($TCP$)**:
   Total cost in USD (calculated via token counts in MLflow) expended to achieve 100% parity per individual pipeline entity.

### 7.2 Error Feedback Loop Dynamics

When the Validator reports broken reconciliation metrics, the Fixer constructs structured diagnostic payloads rather than sending raw error dumps:

```
┌────────────────────────────────────────────────────────┐
│                   DIAGNOSTIC PAYLOAD                   │
├────────────────────────────────────────────────────────┤
│ • Failure Target: silver_orders.total_amount           │
│ • Root Cause: Metric Divergence > Epsilon              │
│ • Source Aggregate: 1,542,320.50                       │
│ • Target Aggregate: 1,539,110.20                       │
│ • Delta: -3,210.30 (-0.208%)                           │
│ • Suspected Mechanism:                                 │
│   Legacy Oracle NVL(freight_value, 0) was omitted      │
│   during PySpark null-handling in joining orders       │
│   with order_items, leading to row drops.              │
│ • Prescribed Fix:                                      │
│   Replace inner join with left_outer join and enforce  │
│   coalesce(col("freight_value"), lit(0.0)).            │
└────────────────────────────────────────────────────────┘
```

The Translator parses this diagnostic context, rewrites the affected PySpark logic, and re-triggers validation without modifying unaffected code blocks.

---

## 8. Databricks Certification & Competency Matrix

This project directly maps to the testing objectives of the Databricks professional certification track:

| Functional Module | Databricks Exam Objective | Practical Implementation Detail |
| :--- | :--- | :--- |
| **Bronze Layer Pipelines** | *Data Engineer Associate / Professional* | Raw schema-on-read ingestion, preserving metadata columns (`_rescued_data`, timestamps), and handling dirty types. |
| **Silver Deduplication & Quality** | *Data Engineer Professional* | Window-based deduplication (`row_number()`), type casting, handling schema drift, and implementing referential integrity. |
| **Gold Star-Schema Aggregations** | *Data Engineer Associate* | Dimensional modeling, star-schema rollups, fact table joins, and performance-tuned aggregations. |
| **Unity Catalog Governance** | *Data Engineer Professional* | 3-level namespace management (`catalog.schema.table`), column comments, business metadata tagging, and data masking. |
| **Databricks Workflows** | *Data Engineer Associate* | Building multi-task DAG jobs, configuring upstream task dependencies, and parameterizing notebook runs. |
| **MLflow Agent Tracing** | *Generative AI Engineer* | Utilizing MLflow Tracing to record tool calls, tracking multi-agent graph state transitions, and measuring token costs. |
| **Deterministic Compound AI Evaluation** | *Generative AI Engineer* | Creating deterministic evaluation frameworks, automated guardrails, and human-in-the-loop review systems. |

---

## 9. Phased Implementation Roadmap

```
Week 1: Local Foundation & Data Emulation
 ├─ Step 1.1: Download Olist dataset; load into DuckDB source instance.
 ├─ Step 1.2: Write messy legacy SQL scripts (Oracle/Netezza styles, view layers).
 ├─ Step 1.3: Define LangGraph MigrationState and typed structures.
 └─ Step 1.4: Implement Profiler node (SQLGlot AST analysis + NetworkX lineage).

Week 2: Core Agent Feedback Loop (Local)
 ├─ Step 2.1: Implement Translator node with Medallion prompt templates.
 ├─ Step 2.2: Implement Validator node (DuckDB source vs. DuckDB target checks).
 ├─ Step 2.3: Implement Fixer node with structured diagnostic feedback.
 ├─ Step 2.4: Integrate SqliteSaver checkpointer and human-in-the-loop breakpoint.
 └─ Step 2.5: Implement Steward node (Markdown runbook + metadata output).

Week 3: Hybrid Databricks Integration
 ├─ Step 3.1: Provision Databricks Free Workspace and configure Unity Catalog.
 ├─ Step 3.2: Swap Validator/Translator write targets to databricks-sql-connector.
 ├─ Step 3.3: Point MLflow tracking URI to Databricks workspace.
 └─ Step 3.4: Validate end-to-end migration runs from local LangGraph into Delta Lake.

Week 4: Lakehouse-Native Assets & Hardening
 ├─ Step 4.1: Convert validated PySpark code into modular Databricks Multi-Task Jobs.
 ├─ Step 4.2: Execute Steward metadata scripts to apply tags and documentation in UC.
 ├─ Step 4.3: Package migration run metrics, evaluation graphs, and test harnesses.
 └─ Step 4.4: Document public GitHub repository portfolio piece.
```