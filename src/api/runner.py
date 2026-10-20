import asyncio
import datetime
import json
import os
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.config import settings
from src.core.checkpointer import get_sqlite_checkpointer
from src.core.graph import build_migration_graph
from src.core.state import MigrationState
from src.tools.database import DuckDBRunner
from src.tools.harness import LegacyWarehouseHarness


class MigrationRunnerManager:
    """Manages active migration runs, checkpoint reconstruction, and SSE event streaming."""

    def __init__(self):
        self.runs: Dict[str, Dict[str, Any]] = {}
        self.event_queues: Dict[str, List[asyncio.Queue]] = {}
        self.active_threads: Dict[str, str] = {}  # thread_id -> run_id
        self._init_default_run()

    def _init_default_run(self) -> None:
        """Initializes default demonstration run reflecting current warehouse state."""
        run_id = "run_07"
        self.runs[run_id] = {
            "run_id": run_id,
            "target_environment": "LOCAL · DUCKDB",
            "model_name": f"{settings.llm.model_name} ({settings.llm.provider})",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "ACTIVE",
            "tables": [
                {
                    "table_num": 1,
                    "table_name": "raw_categories",
                    "depends_on": "-",
                    "checks": "5/5",
                    "attempts": "0",
                    "status": "PROMOTED",
                    "thread_id": "thread_cat_01",
                    "has_pii": False,
                    "pii_count": 0,
                },
                {
                    "table_num": 2,
                    "table_name": "raw_customers",
                    "depends_on": "-",
                    "checks": "6/6",
                    "attempts": "0",
                    "status": "NEEDS REVIEW",
                    "thread_id": "thread_cust_01",
                    "has_pii": True,
                    "pii_count": 3,
                },
                {
                    "table_num": 3,
                    "table_name": "raw_orders",
                    "depends_on": "raw_customers",
                    "checks": "5/6",
                    "attempts": "1 of 3",
                    "status": "NEEDS REVIEW",
                    "thread_id": "thread_orders_02",
                    "has_pii": False,
                    "pii_count": 0,
                },
                {
                    "table_num": 4,
                    "table_name": "raw_order_payments",
                    "depends_on": "raw_orders",
                    "checks": "4/5",
                    "attempts": "3 of 3",
                    "status": "FIXING",
                    "thread_id": "thread_payments_03",
                    "has_pii": False,
                    "pii_count": 0,
                },
                {
                    "table_num": 5,
                    "table_name": "raw_order_items",
                    "depends_on": "raw_orders",
                    "checks": "-/-",
                    "attempts": "-",
                    "status": "QUEUED",
                    "thread_id": "thread_items_01",
                    "has_pii": False,
                    "pii_count": 0,
                },
                {
                    "table_num": 6,
                    "table_name": "v_order_summary",
                    "depends_on": "raw_orders, raw_order_payments, raw_order_items",
                    "checks": "-/-",
                    "attempts": "-",
                    "status": "BLOCKED (waits on raw_order_payments)",
                    "thread_id": "thread_summary_01",
                    "has_pii": False,
                    "pii_count": 0,
                },
            ],
        }

    async def broadcast_event(self, run_id: str, event_data: Dict[str, Any]) -> None:
        """Broadcasts an SSE event to all connected listeners for this run."""
        if run_id not in self.event_queues:
            return
        for q in self.event_queues[run_id]:
            await q.put(event_data)

    async def event_generator(self, run_id: str) -> AsyncGenerator[str, None]:
        """Async generator producing Server-Sent Events with unique IDs."""
        q: asyncio.Queue = asyncio.Queue()
        if run_id not in self.event_queues:
            self.event_queues[run_id] = []
        self.event_queues[run_id].append(q)

        event_idx = 1
        # Send initial connected event
        init_event = {
            "event_id": f"evt_{run_id}_{event_idx}",
            "run_id": run_id,
            "type": "CONNECTION",
            "message": f"Connected to run {run_id} SSE event stream.",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        yield f"id: {init_event['event_id']}\nevent: message\ndata: {json.dumps(init_event)}\n\n"

        try:
            while True:
                data = await q.get()
                event_idx += 1
                data["event_id"] = f"evt_{run_id}_{event_idx}"
                yield f"id: {data['event_id']}\nevent: message\ndata: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            if run_id in self.event_queues and q in self.event_queues[run_id]:
                self.event_queues[run_id].remove(q)

    def get_board(self, run_id: str) -> Dict[str, Any]:
        """Returns board snapshot for the given run."""
        if run_id not in self.runs:
            self._init_default_run()
            if run_id not in self.runs:
                run_id = "run_07"
        run_data = self.runs[run_id]

        # Calculate counts
        tables = run_data.get("tables", [])
        total = len(tables)
        promoted = sum(1 for t in tables if t["status"] == "PROMOTED")
        needs_review = sum(1 for t in tables if "NEEDS REVIEW" in t["status"])
        fixing = sum(1 for t in tables if t["status"] == "FIXING")
        blocked = sum(1 for t in tables if "BLOCKED" in t["status"])

        return {
            "run_id": run_id,
            "target_environment": run_data.get("target_environment", "LOCAL · DUCKDB"),
            "model_name": run_data.get("model_name", "llama3.2 (ollama)"),
            "summary": {
                "total_tables": total,
                "promoted": promoted,
                "needs_review": needs_review,
                "fixing": fixing,
                "blocked": blocked,
                "display_counter": f"{promoted}/{total} PROMOTED",
            },
            "tables": tables,
        }

    def get_thread_state(self, thread_id: str) -> Dict[str, Any]:
        """Reconstructs full table review snapshot from SQLite checkpointer or fixtures."""
        # 1. Check fixtures
        fixture_map = {
            "thread_cust_01": "state_passed_first_time.json",
            "thread_orders_02": "state_mid_repair.json",
            "thread_payments_03": "state_failed_closed.json",
            "fixture_passed": "state_passed_first_time.json",
            "fixture_mid_repair": "state_mid_repair.json",
            "fixture_failed_closed": "state_failed_closed.json",
        }

        if thread_id in fixture_map:
            fx_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "tests",
                "fixtures",
                fixture_map[thread_id],
            )
            if os.path.exists(fx_path):
                with open(fx_path, "r", encoding="utf-8") as f:
                    return json.load(f)

        # 2. Reconstruct from live SQLite checkpointer
        checkpointer = get_sqlite_checkpointer(settings.database.checkpoint_path)
        source_db = DuckDBRunner(settings.database.legacy_path)
        target_db = DuckDBRunner(settings.database.target_path)
        graph = build_migration_graph(source_db=source_db, target_db=target_db, checkpointer=checkpointer)

        config = {"configurable": {"thread_id": thread_id}}
        state_snap = graph.get_state(config)

        if not state_snap or not state_snap.values:
            # Fallback to passed-first-time default fixture
            fx_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "tests",
                "fixtures",
                "state_passed_first_time.json",
            )
            with open(fx_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["thread_id"] = thread_id
                return data

        values = state_snap.values
        cur_table = values.get("current_table", "raw_orders")
        checks = values.get("checks", [])
        if not checks:
            # Fallback from validation_metrics
            for m in values.get("validation_metrics", []):
                checks.append({
                    "name": m.get("metric_name", ""),
                    "description": f"Verification on {m.get('metric_name')}",
                    "source_value": m.get("source_metric"),
                    "target_value": m.get("target_metric"),
                    "tolerance": m.get("tolerance_threshold", 0.0),
                    "divergence": m.get("divergence_score", 0.0),
                    "status": "PASS" if m.get("passed") else "FAIL",
                    "error_message": m.get("error_message"),
                })

        col_treatments = values.get("column_treatments", {}).get(cur_table, [])
        attempts = values.get("attempts", [])
        provenance = values.get("provenance", [])
        fix_attempts = values.get("fix_attempts", 0)

        # Determine status
        next_nodes = state_snap.next or ()
        if "human_approval" in next_nodes:
            status = "NEEDS_REVIEW"
        elif values.get("human_approved"):
            status = "PROMOTED"
        elif fix_attempts >= values.get("max_retries", 3) and not values.get("validation_passed"):
            status = "FAILED_CLOSED"
        else:
            status = "FIXING"

        return {
            "thread_id": thread_id,
            "run_id": "run_07",
            "current_table": cur_table,
            "target_environment": "LOCAL · DUCKDB",
            "model_name": f"{settings.llm.model_name} ({settings.llm.provider})",
            "staging_entity": values.get("staging_entity", f"staging.silver_{cur_table}"),
            "target_entity": f"silver.{cur_table}",
            "status": status,
            "repair_summary": f"Passed after {fix_attempts} repair" if fix_attempts > 0 else "Passed first time",
            "fix_attempts": fix_attempts,
            "max_retries": values.get("max_retries", 3),
            "checks": checks,
            "column_treatments": col_treatments,
            "provenance": provenance,
            "attempts": attempts,
            "telemetry": values.get("telemetry", []),
            "graph_nodes": [
                {"id": "profiler", "label": "PROFILER", "status": "COMPLETED"},
                {"id": "translator", "label": "TRANSLATOR", "status": "COMPLETED"},
                {"id": "validator", "label": "VALIDATOR", "status": "COMPLETED"},
                {"id": "gate", "label": "APPROVAL GATE", "status": "HALTED" if status == "NEEDS_REVIEW" else "COMPLETED"},
                {"id": "fixer", "label": "FIXER", "status": "RUNNING" if status == "FIXING" else "IDLE"},
                {"id": "steward", "label": "STEWARD", "status": "COMPLETED" if status == "PROMOTED" else "IDLE"},
            ],
        }

    async def resume_thread(
        self,
        thread_id: str,
        action: str,
        feedback: Optional[str] = None,
        column_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Resumes thread execution via LangGraph checkpoint."""
        source_db = DuckDBRunner(settings.database.legacy_path)
        target_db = DuckDBRunner(settings.database.target_path)
        checkpointer = get_sqlite_checkpointer(settings.database.checkpoint_path)
        graph = build_migration_graph(source_db=source_db, target_db=target_db, checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        action_norm = action.lower()
        if action_norm == "approve":
            graph.update_state(config, {"human_approved": True, "human_feedback": None}, as_node="human_approval")
            # Update board table status
            for t in self.runs.get("run_07", {}).get("tables", []):
                if t.get("thread_id") == thread_id:
                    t["status"] = "PROMOTED"
            await self.broadcast_event("run_07", {
                "type": "NODE_EVENT",
                "node": "steward",
                "status": "COMPLETED",
                "thread_id": thread_id,
                "message": f"Table promoted to silver layer.",
            })
        elif action_norm in ("changes", "reject"):
            msg = feedback or "Operator requested changes"
            if column_overrides:
                msg += f" Overrides: {json.dumps(column_overrides)}"
            graph.update_state(config, {"human_approved": False, "human_feedback": msg}, as_node="human_approval")
            for t in self.runs.get("run_07", {}).get("tables", []):
                if t.get("thread_id") == thread_id:
                    t["status"] = "FIXING"
            await self.broadcast_event("run_07", {
                "type": "NODE_EVENT",
                "node": "fixer",
                "status": "RUNNING",
                "thread_id": thread_id,
                "message": f"Fixer loop engaged with feedback: {msg}",
            })
        elif action_norm == "abort":
            graph.update_state(config, {"human_approved": False, "human_feedback": None}, as_node="human_approval")
            for t in self.runs.get("run_07", {}).get("tables", []):
                if t.get("thread_id") == thread_id:
                    t["status"] = "ABORTED"
            await self.broadcast_event("run_07", {
                "type": "NODE_EVENT",
                "node": "gate",
                "status": "ABORTED",
                "thread_id": thread_id,
                "message": f"Operator aborted migration.",
            })

        # Run next steps
        for event in graph.stream(None, config=config):
            for node_name, _ in event.items():
                await self.broadcast_event("run_07", {
                    "type": "NODE_EVENT",
                    "node": node_name,
                    "status": "COMPLETED",
                    "thread_id": thread_id,
                    "message": f"Completed node {node_name}",
                })

        return self.get_thread_state(thread_id)

    async def start_new_run(self, tables: Optional[List[str]] = None, target_env: str = "LOCAL · DUCKDB", provider: str = "ollama") -> str:
        """Starts a new migration run."""
        run_id = f"run_{str(uuid.uuid4())[:6]}"
        harness = LegacyWarehouseHarness(settings.database.legacy_path)
        ddl_map = harness.seed()

        target_tables = tables if tables else list(ddl_map.keys())
        table_rows = []
        for idx, tbl in enumerate(target_tables):
            has_p = tbl == "raw_customers"
            table_rows.append({
                "table_num": idx + 1,
                "table_name": tbl,
                "depends_on": "-" if idx == 0 else target_tables[idx - 1],
                "checks": "-/-",
                "attempts": "0",
                "status": "RUNNING" if idx == 0 else f"BLOCKED (waits on {target_tables[idx - 1]})",
                "thread_id": f"th_{tbl}_{str(uuid.uuid4())[:4]}",
                "has_pii": has_p,
                "pii_count": 3 if has_p else 0,
            })

        self.runs[run_id] = {
            "run_id": run_id,
            "target_environment": target_env,
            "model_name": f"{settings.llm.model_name} ({provider})",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "ACTIVE",
            "tables": table_rows,
        }
        return run_id


runner_manager = MigrationRunnerManager()
