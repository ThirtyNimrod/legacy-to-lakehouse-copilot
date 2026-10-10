from typing import Any, Dict, Literal, Optional
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.fixer import FixerAgent
from src.agents.profiler import ProfilerAgent
from src.agents.steward import StewardAgent
from src.agents.translator import TranslatorAgent
from src.agents.validator import ValidatorAgent
from src.core.checkpointer import get_sqlite_checkpointer
from src.core.state import MigrationState
from src.tools.database import DatabaseRunner, DuckDBRunner


def build_migration_graph(
    source_db: DatabaseRunner,
    target_db: DatabaseRunner,
    checkpointer: Optional[Any] = None,
) -> CompiledStateGraph:
    """Builds and compiles the deterministic LangGraph multi-agent migration state machine."""

    # Initialize agent instances
    profiler = ProfilerAgent(legacy_db=source_db)
    translator = TranslatorAgent(target_db=target_db, source_db=source_db)
    validator = ValidatorAgent(source_db=source_db, target_db=target_db)
    fixer = FixerAgent()
    steward = StewardAgent(target_db=target_db)

    builder = StateGraph(MigrationState)

    # 1. Add agent nodes
    builder.add_node("profiler", profiler.run)
    builder.add_node("translator", translator.run)
    builder.add_node("validator", validator.run)
    builder.add_node("fixer", fixer.run)

    # Human approval node (acts as state checkpoint gate)
    def human_approval_node(state: MigrationState) -> Dict[str, Any]:
        return {}

    # Cleanup staging node on abort
    def abort_cleanup_node(state: MigrationState) -> Dict[str, Any]:
        stg = state.get("staging_entity")
        if stg:
            target_db.execute(f"DROP TABLE IF EXISTS {stg};")
        return {"staging_entity": ""}

    builder.add_node("human_approval", human_approval_node)
    builder.add_node("abort_cleanup", abort_cleanup_node)
    builder.add_node("steward", steward.run)

    # 2. Add sequential edges
    builder.add_edge(START, "profiler")
    builder.add_edge("profiler", "translator")
    builder.add_edge("translator", "validator")

    # 3. Conditional routing after validation
    def route_after_validation(state: MigrationState) -> Literal["fixer", "human_approval"]:
        passed = state.get("validation_passed", False)
        attempts = state.get("fix_attempts", 0)
        max_retries = state.get("max_retries", 3)

        if not passed and attempts < max_retries:
            return "fixer"
        return "human_approval"

    builder.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "fixer": "fixer",
            "human_approval": "human_approval",
        },
    )

    # Fixer feeds back into translator (closed-loop repair cycle)
    builder.add_edge("fixer", "translator")

    # 4. Conditional routing after human approval gate
    def route_after_approval(state: MigrationState) -> Literal["steward", "fixer", "abort_cleanup"]:
        if state.get("human_approved", False):
            return "steward"
        elif state.get("human_feedback"):
            return "fixer"
        return "abort_cleanup"

    builder.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "steward": "steward",
            "fixer": "fixer",
            "abort_cleanup": "abort_cleanup",
        },
    )

    builder.add_edge("abort_cleanup", END)

    # 5. Multi-table DAG loop routing after steward promotion
    def route_after_steward(state: MigrationState) -> Literal["translator", "__end__"]:
        pending = state.get("pending_tables", [])
        if pending and pending[0] != "":
            return "translator"
        return "__end__"

    builder.add_conditional_edges(
        "steward",
        route_after_steward,
        {
            "translator": "translator",
            "__end__": END,
        },
    )

    # Compile with checkpointing and human-in-the-loop interruption
    if checkpointer is None:
        checkpointer = get_sqlite_checkpointer()

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"],
    )
