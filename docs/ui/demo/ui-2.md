# UI/UX Specification v2: Legacy-to-Lakehouse Migration Copilot
**Replaces**: `ui-1.md` | **User**: one operator reviewing migrations | **Stack**: FastAPI (REST + SSE) → React/Vite/TS

## 1. What this UI is for
The system's real output is a decision: *can I trust this table enough to promote it?* The UI is built around that decision. Every screen either helps judge one table or shows where the whole migration stands. Agent internals exist, but are tucked away.

Principles
1. **Decision first, plumbing second.**
2. **Evidence, not reassurance.** Every claim (passed, masked, translated) shows the values behind it.
3. **Design the failure state first.** All-green screens teach people to click Approve.
4. **Buttons say exactly what they do.**
5. **The server is the source of truth.** A review can sit for days. Refresh or restart must rebuild the same screen from the checkpoint.
6. **Always show where writes land.** A permanent badge: LOCAL · DUCKDB or DATABRICKS · catalog.schema.

## 2. Screens

### 2.1 Migration board (home)
One row per table, in dependency order (from the lineage graph).

```
LEGACY // LAKEHOUSE      TARGET: LOCAL · DUCKDB       MODEL: llama3.2 (ollama)
--------------------------------------------------------------------------------
RUN 07   6 TABLES   2 PROMOTED · 2 NEEDS REVIEW · 1 FIXING · 1 BLOCKED
--------------------------------------------------------------------------------
 #  TABLE               DEPENDS ON      CHECKS   ATTEMPTS   STATUS
 1  raw_categories      -               5/5      0          PROMOTED
 2  raw_customers       -               6/6      0          NEEDS REVIEW  [PII 3]
 3  raw_orders          raw_customers   6/6      1          NEEDS REVIEW
 4  raw_order_payments  raw_orders      4/5      2 of 3     FIXING
 5  raw_order_items     raw_orders      -        -          QUEUED
 6  v_order_summary     3, 4, 5         -        -          BLOCKED (waits on 4)
```
- A table is BLOCKED until everything it depends on is promoted.
- Filter chips by status. "Start run" panel: pick tables (default all), model, target.
- Thread IDs are hidden behind a copy icon.

### 2.2 Table review page (main screen)
Evidence on the left (tabs), decision rail on the right (always visible).

```
< BOARD   raw_orders        RUN 07            TARGET: LOCAL · DUCKDB
--------------------------------------------------------------------------------
 [CHECKS 6/6] [SCHEMA & PII] [CODE] [ATTEMPTS 1]    |  NEEDS REVIEW
                                                    |  Passed after 1 repair
 6 OF 6 CHECKS PASS   [■][■][■][■][■][■]            |
                                                    |  [ ] I reviewed 2 sensitive
 CHECK                SOURCE  TARGET  TOL    RESULT |      columns
 dedup_cardinality    1,000   1,000   0      PASS   |
 duplicate_pk_count   -       0       0      PASS   |  [ APPROVE ]
 null_ratio_cust_id   0.00%   0.00%   0      PASS   |  Promotes staging.silver_orders
 ...                                                |  to silver.orders, writes tags
                                                    |  [ REQUEST CHANGES ]
                                                    |  [ ABORT ]
--------------------------------------------------------------------------------
 > RUN TRACE (developer)
```

**Evidence tabs**
- **Checks**: one row per check with a plain-words description, source value, target value, tolerance and result. Failing rows come first and are expanded. The headline is the worst case ("5 of 6 pass, 1 failing"), never an average. The segmented bar has exactly one segment per check.
- **Schema & PII**: source column → target column, side by side, with rename, type change, sensitivity tag and treatment (hash / mask / keep / drop). It shows 3 sample rows before and after, with sensitive values masked on both sides. Anything the model proposed carries an AI-SUGGESTED tag. The reviewer can change a treatment inline, and that change goes to the fixer as structured feedback.
- **Code**: source SQL beside generated PySpark, aligned by statement. Each statement is tagged RULE (sqlglot) or MODEL (LLM-written). Read-only in v1.
- **Attempts**: a timeline of attempt, failed check, diagnosis, code diff, then the next result. With zero repairs it says "Passed first time".

**Decision rail**
- Approve enables only after each sensitive column is individually confirmed.
- The Approve label states its effect (see the wireframe).
- Request changes asks for a target (a check, a column, or general) plus a comment. It spends one retry, and the remaining count is shown.
- Abort asks for confirmation.
- If the retry budget is spent and a check still fails, Approve is hidden. Only Request changes (extra attempt), Abort and Export diagnostics remain.

### 2.3 Run trace (developer drawer, collapsed by default)
- The real graph drawn properly, with the validator → fixer → translator loop and the gate. The current node is highlighted.
- Per-node duration, model and token counts.
- Expandable prompt and response for each LLM call.
- Live log stream.
- Phase 2: link to the MLflow run.

### 2.4 Evals (later)
A grid of seeded faults (float drift, dedup tie-break, empty-vs-null, ...) against models. Each cell shows solved?, attempts, tokens and time. The header shows the overall solve rate. This screen turns the project from a demo into evidence about how well agents do this job.

## 3. Visual language
Keep the Nothing-inspired look: OLED black / warm paper, mono for data, grotesk for labels, square panels, pill buttons. Changes from ui-1:

| Topic | ui-1 | ui-2 |
| :--- | :--- | :--- |
| Red | Gate and errors | Failures and breaches only |
| Waiting for review | Red, pulsing | Inverted white tag (attention without alarm) |
| Amber | Warning | Retry in progress |
| Green | Values | Passed values only, never backgrounds |
| Pulse | Gate dot, always | RUNNING state only |
| Glow / shadows | Glow on dots | None |
| Doto font | Hero numbers, titles | One counter only (e.g. 4/6 PROMOTED) |
| Precise numbers | Mixed | Space Mono |
| Small text | 11px, #666 | At least 12px, 4.5:1 contrast for anything informative |
| Fonts | Google CDN | Self-hosted (local-first, works offline) |
| Hero metric | "Total divergence" | "N of M checks pass" + worst check |

Dropped: the 20-block bar and the aggregate divergence number.

## 4. States to design
Passed first time · Failing, fixer working (attempt 2 of 3) · Failed closed · Waiting for review after repairs · Promoted · Aborted · Blocked on upstream · Connection lost / run crashed · No runs yet · Databricks target unreachable.

## 5. Backend contract
Use SSE rather than WebSocket: the stream is one-way, and resume is a normal POST.
- `POST /runs` `{tables, provider, target}`
- `GET /runs/{id}` board snapshot
- `GET /runs/{id}/events` SSE of graph updates, with event IDs so the browser can reconnect
- `GET /threads/{id}/state` full review snapshot built from the checkpoint
- `POST /threads/{id}/resume` `{action: approve|changes|abort, feedback, column_overrides}`

State the UI needs that `MigrationState` doesn't carry yet:
- Checks as structured records (name, plain description, source, target, tolerance, status)
- Attempts as a list (diagnosis, patch diff, results), not just a counter
- Per-statement provenance (rule vs model)
- Per-column treatment and an AI-suggested flag
- Table status including staged vs promoted, plus target environment
- Per-node duration and token counts

Related backend changes: loop over the whole warehouse in dependency order, and stage first, then promote on approval.

## 6. Build order
1. **Fixtures first**: dump real state JSON for three situations (passed, mid-repair, failed closed) and build static views against them. Failed closed needs the seeded faults.
2. FastAPI bridge with board and review page live on the local target.
3. Phase 2: environment badge, links to the Unity Catalog table and MLflow run, real promote flow.
4. Evals screen once the seeded-fault suite exists.

## 7. Out of scope (v1)
Auth and multi-user, editing code in the browser, approving over failing checks, mobile layout.