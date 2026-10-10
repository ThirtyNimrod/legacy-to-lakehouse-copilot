import tempfile
from pathlib import Path
from langgraph.checkpoint.memory import MemorySaver

from src.core.graph import build_migration_graph
from src.core.state import MigrationState
from src.tools.database import DuckDBRunner
from src.tools.harness import LegacyWarehouseHarness


def test_topological_dag_pipeline_multi_table():
    with tempfile.TemporaryDirectory() as tmpdir:
        s_path = str(Path(tmpdir) / "source.duckdb")
        t_path = str(Path(tmpdir) / "target.duckdb")

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

        # Subset for DAG test: raw_customers, raw_orders, raw_order_payments
        test_tables = {
            "raw_customers": ddl_map["raw_customers"],
            "raw_orders": ddl_map["raw_orders"],
            "raw_order_payments": ddl_map["raw_order_payments"],
        }
        table_keys = list(test_tables.keys())

        initial_state: MigrationState = {
            "messages": [],
            "source_dialect": "Oracle",
            "raw_ddl_map": test_tables,
            "profiles": {},
            "lineage_graph": {},
            "execution_order": table_keys,
            "pending_tables": table_keys[1:],
            "completed_tables": [],
            "staging_entity": f"staging_silver_{table_keys[0]}",
            "current_table": table_keys[0],
            "artifacts": {},
            "active_salt": "dag_salt_123",
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

        config = {"configurable": {"thread_id": "dag_thread_01"}}

        # Run table 1 until interrupt
        list(graph.stream(initial_state, config=config))
        snap1 = graph.get_state(config)
        assert "human_approval" in snap1.next

        # Approve table 1 -> advances through steward
        graph.update_state(config, {"human_approved": True, "human_feedback": None}, as_node="human_approval")
        list(graph.stream(None, config=config))

        tables_created = t_runner.list_tables()
        assert f"silver_{table_keys[0]}" in tables_created

        s_runner.close()
        t_runner.close()
