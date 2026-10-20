# Legacy-to-Lakehouse Copilot: Verification & Testing Playbook

This playbook provides a hands-on guide for operators, data engineers, and evaluators to test every component of the **Legacy-to-Lakehouse Migration Copilot**. 

By completing these exercises, you will:
1. Understand how the multi-agent system uses **deterministic mathematical checks** instead of relying on LLMs to grade themselves.
2. Experience the **self-healing repair loop** resolving real legacy data antipatterns.
3. Verify that **staging schema isolation** protects production tables until human approval.
4. Become proficient in navigating both the **CLI** and the **Operator Console Web UI**.

---

## 📋 Test Matrix Overview

| Test ID | Environment | Target Feature | Antipattern / Scenario | Expected Result |
| :--- | :--- | :--- | :--- | :--- |
| **A-01** | Pytest | Full Test Suite | All modules | 19 / 19 tests pass |
| **A-02** | Pytest | Repair Benchmark | Duplicate ties & float drift | Self-healing convergence to `0.0` |
| **A-03** | Pytest | Staging Isolation | Abort & Promotion | Fail-closed staging cleanup |
| **C-01** | CLI | Seed Harness | 6 legacy entities | Legacy DuckDB warehouse initialized |
| **C-02** | CLI | Repair Loop | Tied duplicate updates (`raw_orders`) | Pass 0 fails $\rightarrow$ Fixer repairs $\rightarrow$ Pass 1 passes $\rightarrow$ Pause at gate |
| **C-03** | CLI | Promotion | Human approval | Staging promoted to `silver_raw_orders`, staging dropped |
| **C-04** | CLI | Abort Cleanup | Float currency drift (`raw_order_payments`) | Staging dropped, production untouched |
| **C-05** | CLI | Topological DAG | Multi-table pipeline (`--all`) | Traversal in dependency order |
| **U-01** | Web UI | Server Launch | Operator Console | FastAPI + React UI served at `http://127.0.0.1:8000` |
| **U-02** | Web UI | Migration Board | Dependency ordering & status chips | High-density operational overview |
| **U-03** | Web UI | PII Review | Salted CPF / Email redaction | Side-by-side masking & sample rows |
| **U-04** | Web UI | Mid-Repair Review | Window deduplication & Fixer diff | Segmented bar & diagnostic feedback |
| **U-05** | Web UI | Fail-Closed Abort | Numeric epsilon divergence | Divergence breakdown & staging drop |
| **U-06** | Web UI | Static Fixtures | Offline state demos | Passed, Mid-Repair, Failed-Closed inspection |

---

## 🛠️ Step 0: Prerequisites & Environment Setup

Open PowerShell in the repository root (`d:\coding\github\legacy-to-lakehouse-copilot`):

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Verify installed packages
pip list | Select-String -Pattern "langgraph|duckdb|fastapi|sqlglot"

# 3. Check local Ollama status (optional but recommended)
ollama list
```
*(If Ollama is not running, the system will seamlessly fall back to offline deterministic mock models).*

---

## 🔬 Suite 1: Automated Regression & Parity Benchmarks

### Test A-01: Run the Full Test Suite
Executes all 19 automated tests covering agent mechanics, API routes, security, and DAG scheduling:
```powershell
.\.venv\Scripts\pytest -v tests/
```
**Verification Points**:
- [x] All 19 tests report `PASSED`.
- [x] Zero regressions across unit, integration, and benchmark suites.

### Test A-02: Self-Healing Repair Loop Benchmark
Validates that naive Pass 0 translations deliberately fail on seeded edge cases and converge to mathematical parity on Pass 1:
```powershell
.\.venv\Scripts\pytest -v tests/test_repair_loop_benchmark.py
```
**Verification Points**:
- [x] `test_repair_loop_convergence_on_duplicate_ties`: Proves window deduplication without secondary tie-breakers fails cardinality parity and converges on Pass 1.
- [x] `test_repair_loop_convergence_on_float_drift`: Proves integer casting of 4-decimal currency amounts causes epsilon divergence $> 10^{-6}$ and converges to `0.0` with `DECIMAL(18, 4)`.

### Test A-03: Staging Schema Isolation & Abort Cleanup
Validates that unapproved writes remain quarantined in staging:
```powershell
.\.venv\Scripts\pytest -v tests/test_staging_promotion.py
```
**Verification Points**:
- [x] `test_staging_isolation_and_promotion`: Proves staging is promoted to production `silver_*` only upon operator approval.
- [x] `test_abort_drops_staging_and_preserves_clean_production`: Proves rejecting or aborting immediately drops staging and leaves production clean.

---

## 💻 Suite 2: Terminal / CLI Deep Dive

### Test C-01: Seed the Legacy Warehouse Test Harness
Populate the local legacy warehouse with real-world antipatterns:
```powershell
.\.venv\Scripts\python.exe -m src.cli seed
```
**What to observe**:
The CLI prints a Rich table listing 6 seeded entities:
- `raw_customers`: Obfuscated columns, 11-digit CPF national ID, email, empty strings `""`.
- `raw_categories`: Hierarchical self-joins (`parent_category_id`).
- `raw_orders`: Mixed dirty date strings, pipe-delimited status history, duplicate updates with identical timestamps.
- `raw_order_payments`: 4-decimal float currency values (`DOUBLE`).
- `raw_order_items`: Foreign-key dependencies and product prices.
- `v_order_summary`: Legacy Oracle constructs (`DECODE`, `NVL`, string concatenation `||`).

---

### Test C-02: Trigger the Self-Healing Repair Loop (`raw_orders`)
Run migration on `raw_orders` to observe the autonomous repair loop in real time:
```powershell
.\.venv\Scripts\python.exe -m src.cli run --table raw_orders
```

**What happens step-by-step**:
1. **Profiler Node**: Generates AST profile, detects primary key (`order_id`), and identifies dependencies.
2. **Translator Node (Pass 0)**: Deliberately generates naive ingestion into `staging_silver_raw_orders` without window deduplication.
3. **Validator Node (Pass 0)**: Executes deterministic checks and detects divergence:
   - `duplicate_index_parity: FAIL (divergence=1.0)`
   - `deduplicated_cardinality_balance: FAIL (divergence=1.0)`
4. **Fixer Node**: Intervenes, analyzes failure payload, categorizes error as `duplicate_records / cardinality_mismatch`, and issues diagnostic feedback.
5. **Translator Node (Pass 1)**: Ingests Fixer feedback and injects deterministic window deduplication (`ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY ingest_date DESC, order_id ASC)`).
6. **Validator Node (Pass 1)**: All checks reach mathematical parity (`divergence=0.0`).
7. **Human Approval Gate**: Execution halts before touching production `silver_raw_orders`.

**Take note of the generated Thread ID** (e.g. `8e3a8ede`).

---

### Test C-03: Resume with Approval & Verify Production Promotion
Approve the paused migration using the thread ID from Test C-02:
```powershell
.\.venv\Scripts\python.exe -m src.cli resume --thread-id <YOUR_THREAD_ID> --action approve
```

**Verification Points**:
1. The CLI confirms: `Human approval granted. Promoting staging table to production silver layer...`
2. **Steward Node** executes:
   - Promotes `staging_silver_raw_orders` to `silver_raw_orders`.
   - Purges `staging_silver_raw_orders`.
   - Generates Unity Catalog tags.
   - Writes a comprehensive runbook to `docs/runbooks/migration_runbook_raw_orders.md`.
3. Verify the generated runbook:
```powershell
Get-Content docs/runbooks/migration_runbook_raw_orders.md -TotalCount 25
```

---

### Test C-04: Test Fail-Closed Security on Abort (`raw_order_payments`)
Run migration on payments, observe the float currency repair pass, and then test the **abort cleanup path**:
```powershell
# 1. Run migration
.\.venv\Scripts\python.exe -m src.cli run --table raw_order_payments
```
*(Notice: Pass 0 fails on float currency drift with divergence `0.00138`, Pass 1 repairs with `DECIMAL(18, 4)` and passes, then halts at approval).*

Now, **abort** the migration to verify fail-closed isolation:
```powershell
.\.venv\Scripts\python.exe -m src.cli resume --thread-id <NEW_THREAD_ID> --action abort
```

**Verification Points**:
- The CLI confirms: `Migration aborted. Dropping unpromoted staging tables...`
- `abort_cleanup` node executes `DROP TABLE IF EXISTS staging_silver_raw_order_payments`.
- The production silver layer remains completely untouched.

---

### Test C-05: Run Full Topological DAG Migration
Execute all legacy tables in dependency order:
```powershell
.\.venv\Scripts\python.exe -m src.cli run --all
```
**Verification Points**:
- The copilot computes the topological sort: `raw_customers` and `raw_categories` first, followed by `raw_orders`, `raw_order_payments`, and `raw_order_items`.
- Each table is transformed into staging and evaluated before promotion.

---

## 🌐 Suite 3: Operator Console Web UI Hands-on

### Test U-01: Launch the Operator Console Server
Start the unified FastAPI server and web application:
```powershell
.\.venv\Scripts\python.exe -m src.cli serve --host 127.0.0.1 --port 8000
```
Open your browser to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

**Expected Screen**:
- Header shows: `LEGACY // LAKEHOUSE`, `TARGET: LOCAL · DUCKDB`, and `MODEL: llama3.2 (ollama)` (or mock model).
- The Migration Board displays **RUN 07** with 6 legacy entities.

---

### Test U-02: Exploring the Migration Board
Observe how the board prioritizes operational clarity over raw technical noise:
1. **Dependency Order**: Tables appear strictly in lineage order (`raw_categories`, `raw_customers`, `raw_orders`, `raw_order_payments`, `raw_order_items`, `v_order_summary`).
2. **Status Badges**:
   - `PROMOTED` (Green): Already reviewed, promoted to production, staging purged.
   - `NEEDS REVIEW` (Amber): Parity achieved, awaiting human decision.
   - `FIXING` (Cyan): Active self-healing repair loop in progress.
   - `QUEUED` / `BLOCKED` (Muted): Waiting on upstream dependencies.
3. **Filter Chips**: Click on `All (6)`, `Needs Review (2)`, or `Fixing (1)` to test real-time table filtering.
4. **Copy Thread ID**: Hover over the table rows and click the copy icon to copy thread IDs.

---

### Test U-03: Table Review — Clean Parity & Salted PII (`raw_customers`)
Click on the **`raw_customers`** row on the board to enter the Table Review screen.

1. **Segmented Checks Bar**:
   - Verify the top headline shows: `6 OF 6 CHECKS PASS`.
   - Verify all 6 segments in the segmented bar are bright green.
2. **Checks Tab**:
   - Inspect the checks table: row count balance, duplicate PK count, null ratio, and MD5 checksum.
   - Notice that every check displays **Source Value**, **Target Value**, and **Tolerance Threshold**.
3. **Schema & PII Tab**:
   - Click the **Schema & PII** tab.
   - Observe the side-by-side comparison between legacy columns and target Silver columns.
   - Look for sensitive columns tagged with **PII**: `cpf`, `customer_email`, `customer_phone_number`.
   - Verify the treatment shows: `SHA-256 + Secret Salt`.
   - Inspect the **Sample Data Preview**: Notice that national IDs and emails are masked with salted hashes on both source and target views.
4. **Decision Rail (Right-Hand Side)**:
   - Notice the checkbox: `[ ] I reviewed 3 sensitive columns`.
   - Try clicking `[ APPROVE ]` without checking the box. Notice that approval is disabled until the safety acknowledgment is confirmed.
   - Check the box, then click **`[ APPROVE ]`**.
   - Watch the status badge transition to **PROMOTED** and notice the staging table drop acknowledgment.

---

### Test U-04: Table Review — Mid-Repair Self-Healing (`raw_orders`)
Return to the board and click on **`raw_orders`** (or navigate to thread `thread_orders_02`):

1. **Evidence of Self-Healing**:
   - The headline reads: `Passed after 1 repair` with `ATTEMPTS: 1 of 3`.
2. **Attempts / Diagnostics Tab**:
   - Click the **Attempts / Repair History** tab.
   - Inspect the Pass 0 Failure breakdown:
     - `duplicate_index_parity: FAILED (divergence = 1.0)`
     - `deduplicated_cardinality_balance: FAILED (divergence = 1.0)`
   - Read the Fixer Diagnostic Report:
     - Root cause: Identical timestamp updates detected; window deduplication without tie-breakers failed.
     - Correction: Injected `ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY ingest_date DESC, order_id ASC)`.
3. **Code Tab**:
   - Click the **PySpark Code** tab.
   - Inspect the generated Bronze readStream and Silver window deduplication queries.

---

### Test U-05: Table Review — Fail-Closed Rejection Flow (`raw_order_payments`)
Click on **`raw_order_payments`** (or thread `thread_payments_03`):

1. **Inspect Failing Parity**:
   - Notice the status badge: `NEEDS REVIEW (1 Check Divergent)`.
   - The segmented bar shows 4 green segments and 1 amber/red segment.
   - The failing row (`numeric_epsilon_payment_value`) is highlighted at the top of the table.
   - Divergence: `0.00138495` vs tolerance threshold `0.00000100`.
2. **Test "Request Changes"**:
   - On the Decision Rail, click **`[ REQUEST CHANGES ]`**.
   - Enter operator feedback: *"Recast payment_value using DECIMAL(18, 4) instead of standard FLOAT."*
   - Click **Submit Feedback**.
   - Notice the thread records the rejection feedback and queues the table for re-translation.
3. **Test "Abort Run"**:
   - Click **`[ ABORT RUN ]`**.
   - Observe the fail-closed confirmation: staging table `staging_silver_raw_order_payments` is purged immediately.

---

### Test U-06: Static Review Fixtures (Offline Demo Validation)
The API includes pre-built static fixtures reflecting the three canonical operator states. You can test them directly via browser or HTTP client:

1. **Passed First Time**: [http://127.0.0.1:8000/api/fixtures/passed](http://127.0.0.1:8000/api/fixtures/passed)
   - Demonstrates a table that passed all 6 checks on Pass 0 with zero repair cycles.
2. **Mid-Repair**: [http://127.0.0.1:8000/api/fixtures/mid_repair](http://127.0.0.1:8000/api/fixtures/mid_repair)
   - Demonstrates a table currently undergoing Fixer remediation with attempt count `1 of 3`.
3. **Failed-Closed**: [http://127.0.0.1:8000/api/fixtures/failed_closed](http://127.0.0.1:8000/api/fixtures/failed_closed)
   - Demonstrates an unrecoverable or rejected run that was safely aborted and isolated.

---

## 🔍 Code Architecture Reference

To understand where each feature is implemented in code:

| System Capability | Core Implementation Files | Description |
| :--- | :--- | :--- |
| **Parity Calculation** | [src/tools/metrics.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/tools/metrics.py) | SQL queries computing cardinality, duplicates, epsilon, nulls |
| **Validation Engine** | [src/agents/validator.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/validator.py) | Executes dual-engine checks comparing legacy source vs target |
| **Self-Healing Loop** | [src/agents/fixer.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/fixer.py), [src/agents/translator.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/translator.py) | Error diagnosis & repaired code re-generation |
| **Staging & Promotion** | [src/agents/steward.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/steward.py), [src/core/graph.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/core/graph.py) | Staging isolation, approval routing, abort cleanup node |
| **Salted PII Redaction** | [src/config.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/config.py), [src/agents/translator.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/agents/translator.py) | Keyed cryptographic salt injection for CPF national IDs |
| **FastAPI REST & SSE** | [src/api/app.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/api/app.py), [src/api/routes.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/api/routes.py), [src/api/runner.py](file:///d:/coding/github/legacy-to-lakehouse-copilot/src/api/runner.py) | REST API, SSE event stream, static UI asset server |
| **Web UI Components** | [web/src/components/MigrationBoard.tsx](file:///d:/coding/github/legacy-to-lakehouse-copilot/web/src/components/MigrationBoard.tsx), [TableReview.tsx](file:///d:/coding/github/legacy-to-lakehouse-copilot/web/src/components/TableReview.tsx) | Cyber-industrial React console components |
