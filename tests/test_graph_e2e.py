import tempfile
from pathlib import Path
from langgraph.checkpoint.memory import MemorySaver

from src.core.graph import build_migration_graph
from src.core.state import MigrationState
from src.tools.database import DuckDBRunner
from src.tools.harness import LegacyWarehouseHarness


def test_migration_graph_e2e_with_hitl():
    with tempfile.TemporaryDirectory() as tmpdir:
        s_path = str(Path(tmpdir) / "source.duckdb")
        t_path = str(Path(tmpdir) / "target.duckdb")

        # Seed source
        harness = LegacyWarehouseHarness(s_path)
        ddl_map = harness.seed()

        s_runner = DuckDBRunner(s_path)
        t_runner = DuckDBRunner(t_path)
        checkpointer = MemorySaver()

        graph = build_migration_graph(
            source_db=s_runner,
            target_db=t_runner,
            checkpointer=checkpointer,
        )

        table_to_migrate = "raw_orders"
        initial_state: MigrationState = {
            "messages": [],
            "source_dialect": "Oracle",
            "raw_ddl_map": {table_to_migrate: ddl_map[table_to_migrate]},
            "profiles": {},
            "lineage_graph": {},
            "execution_order": [table_to_migrate],
            "current_table": table_to_migrate,
            "artifacts": {},
            "validation_metrics": [],
            "validation_passed": False,
            "fix_attempts": 0,
            "max_retries": 2,
            "diagnostic_feedback": None,
            "human_approved": False,
            "human_feedback": None,
            "catalog_metadata": {},
            "final_migration_report": None,
        }

        config = {"configurable": {"thread_id": "test_thread_001"}}

        # 1. First execution run: should stop at human_approval interrupt
        events = list(graph.stream(initial_state, config=config))
        node_names = [list(e.keys())[0] for e in events]

        assert "profiler" in node_names
        assert "translator" in node_names
        assert "validator" in node_names
        assert "fixer" in node_names  # Confirms self-healing repair cycle engaged!

        state_snap = graph.get_state(config)
        assert "human_approval" in state_snap.next
        assert "staging_silver_raw_orders" in t_runner.list_tables()
        assert "silver_raw_orders" not in t_runner.list_tables()

        # 2. Operator approves state
        graph.update_state(
            config,
            {"human_approved": True, "human_feedback": None},
            as_node="human_approval",
        )

        # 3. Resume from checkpoint
        resume_events = list(graph.stream(None, config=config))
        resume_nodes = [list(e.keys())[0] for e in resume_events]

        assert "steward" in resume_nodes

        # 4. Verify promotion and final state
        assert "silver_raw_orders" in t_runner.list_tables(), "Production table must exist after approval"
        assert "staging_silver_raw_orders" not in t_runner.list_tables(), "Staging table must be dropped after promotion"
        final_state = graph.get_state(config).values
        assert final_state["final_migration_report"] is not None
        assert "Migration Runbook" in final_state["final_migration_report"]

        s_runner.close()
        t_runner.close()
