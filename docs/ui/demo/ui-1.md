# UI/UX Specification: Legacy-to-Lakehouse Migration Copilot
**Document Reference**: `ui-1.md`  
**Design System**: Nothing-Inspired Industrial Design System (v3.0.0)  
**Target Platform**: Web (HTML5 / Vanilla CSS / ES6 / FastAPI WebSocket Bridge)  
**Fonts Declared**: `Doto` (Display / Hero Matrix), `Space Grotesk` (UI / Body), `Space Mono` (Data / Telemetry)

---

## 1. Executive Summary & Design Rationale

### 1.1 Why a Dedicated UI Over a CLI?
The current pipeline operates via `python -m src.cli run` and pauses at `__interrupt__` for human approval via CLI commands. While the CLI is scriptable and deterministic, migrating enterprise data warehouses (Oracle, Teradata, Netezza) to Databricks/Delta Lake presents high-stakes risks that a terminal stream cannot safely handle:

1. **High-Stakes PII Verification**: Reviewing masked columns (`cust_nat_doc_num_id`, salted SHA-256 hashes) across dozens of attributes in a raw terminal printout risks human oversight. A structured UI renders deterministic side-by-side AST schema diffs with instant sensitivity tagging.
2. **Deterministic Parity Observability**: Dual-engine validation metrics (divergence scores, duplicate index checks, null distributions) need immediate perceptual comprehension. Discrete segmented bars and numeric readouts eliminate ambiguous log scanning.
3. **Human-in-the-Loop (HITL) Friction**: Halting at `__interrupt__` and requiring the engineer to copy/paste thread IDs and CLI resume flags (`--action reject --feedback "..."`) introduces workflow friction. An interactive approval gate provides 1-click approvals, structured repair feedback loops, and live cycle tracking.
4. **Agent State Machine Transparency**: The LangGraph DAG (`profiler` -> `translator` -> `validator` -> `fixer` -> `steward`) contains dynamic routing and self-healing cycles. Visualizing node activations and state transitions in real time provides confidence and complete traceability.

---

## 2. Design System Foundations: Nothing Design Language

The UI strictly adheres to the **Nothing Design System**: an industrial, Swiss-typographic aesthetic inspired by Dieter Rams, Teenage Engineering, and Nothing OS.

### 2.1 Core Principles
- **Subtract, Don't Add**: Zero extraneous borders, zero gradients, zero drop shadows, zero glassmorphism blurs.
- **Structure is Ornament**: The layout exposes the grid, the data, and the state machine directly.
- **Monochrome Canvas**: Pure OLED black (`#000000`) in dark mode and warm technical paper (`#F5F5F5`) in light mode.
- **Color as an Event**: Accent Red (`#D71921`) is reserved exclusively as a signal light (e.g., Human Approval Gate interrupt, parity breaches, destructive actions). Status colors (`#4A9E5C` success, `#D4A843` warning) apply strictly to data values, never to decorative backgrounds.
- **Typography Does the Heavy Lifting**:
  - `Doto`: Dot-matrix display typography for hero numbers, operational status badges, and telemetry headers.
  - `Space Grotesk`: High-contrast, clean sans-serif for UI labels and body text.
  - `Space Mono`: ALL CAPS technical labels, code artifacts, divergence readouts, and execution logs.

### 2.2 Design Tokens

```css
:root {
  /* Canvas & Surfaces */
  --black: #000000;
  --surface: #111111;
  --surface-raised: #1A1A1A;
  --border: #222222;
  --border-visible: #333333;

  /* Typography */
  --text-display: #FFFFFF;
  --text-primary: #E8E8E8;
  --text-secondary: #999999;
  --text-disabled: #666666;

  /* Signal & Data Status */
  --accent: #D71921;             /* Gate interrupt & errors */
  --accent-subtle: rgba(215, 25, 33, 0.15);
  --success: #4A9E5C;            /* Parity verified (0.0 divergence) */
  --warning: #D4A843;            /* Parity drift / retry active */

  /* Rhythm */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
}
```

---

## 3. Screen Architecture & Visual Hierarchy

The interface employs the strict **Three-Layer Visual Hierarchy**:
- **Layer 1 (Primary)**: The operational state and hero metric (`[GATE: APPROVAL REQUIRED]`, Divergence `0.000`, Active Table) rendered in `Doto` or display-scale `Space Grotesk`.
- **Layer 2 (Secondary)**: Supporting context (Parity metrics table, generated PySpark script, PII column catalog) in `Space Grotesk` and clean mono cards.
- **Layer 3 (Tertiary)**: Telemetry metadata, thread ID (`pii_test_01`), checkpoint timestamps, and CLI command sync displayed in `Space Mono` ALL CAPS.

```
+---------------------------------------------------------------------------------------+
|  [NOTHING] LEGACY-TO-LAKEHOUSE COPILOT                     MODE: [DARK | LIGHT]        |
|  THREAD: pii_test_01  |  DIALECT: DUCKDB/ORACLE  |  LLM: OLLAMA llama3.2:latest       |
+---------------------------------------------------------------------------------------+
|  PIPELINE DAG (LANGGRAPH MULTI-AGENT STATE MACHINE)                                    |
|  [ PROFILER ] ===> [ TRANSLATOR ] ===> [ VALIDATOR ] ===> [ ! GATE ! ] ===> [ STEWARD ]|
|                                             ^                  |                       |
|                                             +=== [ FIXER ] <===+                       |
+---------------------------------------------------------------------------------------+
|  ACTIVE TABLE WORKSPACE                                                               |
|  [RAW_CUSTOMERS]   RAW_ORDERS   RAW_PRODUCTS                         REPAIR CYCLES: 01|
|                                                                                       |
|  HERO STATUS: [OPERATOR ACTION REQUIRED]                          PARITY: 100% MATCH  |
+----------------------------------------------------+----------------------------------+
|  PANEL A: VERIFICATION & PARITY MATRIX             |  PANEL B: ARTIFACT & PII STUDIO  |
|  - duplicate_index_parity: 0.0 DIV [PASSED]        |  TABS: [PYSPARK] [DDL] [PII MAP] |
|  - null_distribution_cust_nat: 0.0 DIV [PASSED]    |                                  |
|  - deduplicated_cardinality: 0.0 DIV [PASSED]      |  from pyspark.sql import ...     |
|  - Segmented Progress: [||||||||||||||||||||] 100% |  df = df.withColumn(             |
|                                                    |    "cust_nat_doc_num_id",        |
|                                                    |    sha256(concat(...)))          |
+----------------------------------------------------+----------------------------------+
|  HUMAN APPROVAL GATE (INTERRUPT RESOLUTION)                                           |
|  [ APPROVE & PROMOTE ]   [ REJECT WITH FEEDBACK ]   [ ABORT PIPELINE ]                |
|  Feedback input: "Fix PII masking pattern for tax IDs..."                             |
+---------------------------------------------------------------------------------------+
|  SYSTEM TELEMETRY CONSOLE (SPACE MONO / LIVE STREAM)                                  |
|  > [profiler] AST scan complete. Found 1 PII column: cust_nat_doc_num_id              |
|  > [translator] Staged silver_raw_customers in DuckDB lakehouse                       |
|  > [validator] All 3 assertions passed. Divergence: 0.0                               |
|  > [gate] Execution halted at checkpoint pii_test_01. Awaiting operator action.      |
+---------------------------------------------------------------------------------------+
```

---

## 4. Component Inventory & UX Workflows

### 4.1 Pipeline DAG Visualizer
- Discrete mechanical nodes rendered in monospace boxes with border indicators.
- **Node States**:
  - `IDLE`: `--text-disabled` border, dim text.
  - `RUNNING`: Pulsing dot indicator, `--text-display`.
  - `COMPLETED`: `--success` checkmark indicator.
  - `INTERRUPTED (GATE)`: `--accent` red border, signal light tag `[HALTED: AWAITING APPROVAL]`.
  - `REPAIRING`: Connected loop back to `fixer` node.

### 4.2 Parity Verification Dashboard
- **Discrete Segmented Bar**: 20 rectangular blocks with 2px gaps showing mathematical parity. Solid white/green blocks indicate verified parity.
- **Deterministic Metrics Table**:
  - Exact source metric vs. target metric.
  - Numerical divergence score (`0.0`).
  - Status chip: `[PASSED]` in `--success`.

### 4.3 PII & Security Governance Inspector
- Displays legacy source schema mapped to Lakehouse target schema.
- Sensitive columns tagged with strict monochrome badges (`[PII]`, `[PCI]`, `[FINANCIAL]`).
- Visual transformation rule explicitly shown (e.g., `sha256(concat(col, salt))` with format preservation).

### 4.4 Human-in-the-Loop Operator Gate
- Direct implementation of LangGraph's `interrupt_before=["human_approval"]`.
- Three clear, deliberate action buttons:
  1. **Primary Button**: `[ APPROVE & PROMOTE ]` (Pill, white background, black text). Advances graph directly to `steward` agent.
  2. **Secondary Button**: `[ REJECT WITH FEEDBACK ]` (Pill, transparent background, white border). Expands input field for prompt feedback (e.g., "Add masking for email domain"), then routes state to `fixer`.
  3. **Destructive Button**: `[ ABORT ]` (Pill, transparent background, red `--accent` border). Safely terminates execution.

### 4.5 Steward Report & Runbook Viewer
- Displays generated Markdown migration report upon steward completion.
- Reconciled parity metrics table, table lineage, and audit certification.

---

## 5. Implementation Roadmap

| Phase | Milestone | Deliverable |
| :--- | :--- | :--- |
| **Phase 1** | Standalone HTML/CSS/JS Prototype | `demo-1.html` complete with full Nothing design system tokens, interactive state simulator, and dark/light modes. |
| **Phase 2** | Backend Fast-API Engine Bridge | Expose LangGraph `CompiledStateGraph` via WebSocket / SSE streaming `/api/migrate/stream`. |
| **Phase 3** | Dual-Engine Parity Live Visualizer | Real-time DuckDB/DuckDB or DuckDB/Spark parity querying directly from browser UI. |
| **Phase 4** | Enterprise Catalog Sync | Direct export of generated metadata and runbooks to Unity Catalog / Apache Polaris. |
