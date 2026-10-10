import argparse
import sys
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import settings
from src.core.checkpointer import get_sqlite_checkpointer
from src.core.graph import build_migration_graph
from src.core.state import MigrationState
from src.tools.database import DuckDBRunner
from src.tools.harness import LegacyWarehouseHarness

console = Console()


def handle_seed(args: argparse.Namespace) -> None:
    """Seeds the legacy DuckDB database with synthetic tables and antipatterns."""
    console.print("[bold cyan]Seeding legacy warehouse test harness...[/bold cyan]")
    harness = LegacyWarehouseHarness(db_path=settings.database.legacy_path)
    ddl_map = harness.seed()

    table = Table(title="Generated Legacy Tables & Views")
    table.add_column("Entity Name", style="bold green")
    table.add_column("Antipattern / Role", style="yellow")

    roles = {
        "raw_customers": "Obfuscated columns, PII (CPF, email, phone)",
        "raw_categories": "Hierarchical self-joins (parent_category_id)",
        "raw_orders": "Dirty mixed dates, delimited status, duplicate updates",
        "raw_order_payments": "Unscaled DOUBLE floating currency amounts",
        "raw_order_items": "Foreign key relationships & prices",
        "v_order_summary": "Oracle DECODE, NVL, string concat ||",
    }

    for name in ddl_map.keys():
        table.add_row(name, roles.get(name, "Standard legacy table"))

    console.print(table)
    console.print(f"[bold green]Legacy database seeded at:[/bold green] {settings.database.legacy_path}")


def handle_run(args: argparse.Namespace) -> None:
    """Executes migration graph until human approval breakpoint."""
    target_table = args.table
    thread_id = args.thread_id or str(uuid.uuid4())[:8]

    console.print(f"[bold cyan]Starting migration for table:[/bold cyan] [yellow]{target_table}[/yellow]")
    console.print(f"[bold blue]Thread ID:[/bold blue] {thread_id}")

    # Initialize databases
    source_db = DuckDBRunner(settings.database.legacy_path)
    target_db = DuckDBRunner(settings.database.target_path)
    checkpointer = get_sqlite_checkpointer(settings.database.checkpoint_path)

    # Fetch DDL
    harness = LegacyWarehouseHarness(settings.database.legacy_path)
    ddl_map = harness.seed()

    if target_table not in ddl_map:
        console.print(f"[bold red]Error: Table '{target_table}' not found in legacy database.[/bold red]")
        sys.exit(1)

    initial_state: MigrationState = {
        "messages": [],
        "source_dialect": "Oracle",
        "raw_ddl_map": {target_table: ddl_map[target_table]},
        "profiles": {},
        "lineage_graph": {},
        "execution_order": [target_table],
        "current_table": target_table,
        "artifacts": {},
        "validation_metrics": [],
        "validation_passed": False,
        "fix_attempts": 0,
        "max_retries": settings.app.max_retries,
        "diagnostic_feedback": None,
        "human_approved": False,
        "human_feedback": None,
        "catalog_metadata": {},
        "final_migration_report": None,
    }

    graph = build_migration_graph(source_db=source_db, target_db=target_db, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    console.print("[dim]Executing LangGraph pipeline...[/dim]")
    for event in graph.stream(initial_state, config=config):
        for node_name, node_output in event.items():
            console.print(f"[bold green][PASS] Completed Node:[/bold green] {node_name}")
            if node_name == "validator":
                metrics = node_output.get("validation_metrics", [])
                passed = node_output.get("validation_passed", False)
                console.print(f"  Parity status: {'[bold green]PASSED[/bold green]' if passed else '[bold red]FAILED[/bold red]'}")
                for m in metrics:
                    st = "[green]OK[/green]" if m["passed"] else "[red]FAIL[/red]"
                    console.print(f"    - {m['metric_name']}: {st} (divergence={m['divergence_score']})")

    # State halted at human approval gate
    state_snap = graph.get_state(config)
    next_node = state_snap.next
    if next_node and "human_approval" in next_node:
        panel_text = (
            f"Execution halted at [bold yellow]Human Approval Gate[/bold yellow].\n"
            f"Review artifacts and metrics for thread: [bold green]{thread_id}[/bold green]\n\n"
            f"To resume, run:\n"
            f"  python -m src.cli resume --thread-id {thread_id} --action approve\n"
            f"  python -m src.cli resume --thread-id {thread_id} --action reject --feedback 'Fix XYZ'\n"
            f"  python -m src.cli resume --thread-id {thread_id} --action abort"
        )
        console.print(Panel(panel_text, title="Operator Action Required", border_style="yellow"))


def handle_resume(args: argparse.Namespace) -> None:
    """Resumes migration from SQLite checkpoint."""
    thread_id = args.thread_id
    action = args.action.lower()
    feedback = args.feedback

    console.print(f"[bold cyan]Resuming Thread:[/bold cyan] {thread_id} with action: [yellow]{action}[/yellow]")

    source_db = DuckDBRunner(settings.database.legacy_path)
    target_db = DuckDBRunner(settings.database.target_path)
    checkpointer = get_sqlite_checkpointer(settings.database.checkpoint_path)

    graph = build_migration_graph(source_db=source_db, target_db=target_db, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    if action == "approve":
        graph.update_state(config, {"human_approved": True, "human_feedback": None}, as_node="human_approval")
    elif action == "reject":
        graph.update_state(config, {"human_approved": False, "human_feedback": feedback or "Rejected by operator"}, as_node="human_approval")
    elif action == "abort":
        graph.update_state(config, {"human_approved": False, "human_feedback": None}, as_node="human_approval")
    else:
        console.print(f"[bold red]Unknown action:[/bold red] {action}")
        return

    console.print("[dim]Continuing graph execution...[/dim]")
    for event in graph.stream(None, config=config):
        for node_name, node_output in event.items():
            console.print(f"[bold green][PASS] Completed Node:[/bold green] {node_name}")
            if node_name == "steward":
                report = node_output.get("final_migration_report")
                if report:
                    console.print("\n[bold green]=== Steward Migration Report ===[/bold green]")
                    console.print(report[:400] + "\n...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Legacy-to-Lakehouse Migration Copilot CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Seed
    subparsers.add_parser("seed", help="Seed legacy DuckDB with test antipatterns")

    # Run
    run_parser = subparsers.add_parser("run", help="Run migration graph on a table")
    run_parser.add_argument("--table", default="raw_orders", help="Legacy table name")
    run_parser.add_argument("--thread-id", default=None, help="Optional thread ID")

    # Resume
    resume_parser = subparsers.add_parser("resume", help="Resume from human approval gate")
    resume_parser.add_argument("--thread-id", required=True, help="Thread ID")
    resume_parser.add_argument("--action", choices=["approve", "reject", "abort"], required=True)
    resume_parser.add_argument("--feedback", default=None, help="Correction feedback")

    args = parser.parse_args()

    if args.command == "seed":
        handle_seed(args)
    elif args.command == "run":
        handle_run(args)
    elif args.command == "resume":
        handle_resume(args)


if __name__ == "__main__":
    main()
