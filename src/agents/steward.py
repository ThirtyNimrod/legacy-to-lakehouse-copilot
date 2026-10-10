from pathlib import Path
from typing import Any, Dict, List, Optional
from src.core.state import ColumnProfile, MigrationState
from src.tools.database import DatabaseRunner


class StewardAgent:
    """Generates Unity Catalog governance metadata, promotes staging to production, and produces runbooks."""

    def __init__(self, runbook_dir: str = "docs/runbooks", target_db: Optional[DatabaseRunner] = None):
        self.runbook_dir = Path(runbook_dir)
        self.runbook_dir.mkdir(parents=True, exist_ok=True)
        self.target_db = target_db

    def promote_staging_to_production(self, table_name: str, staging_table: Optional[str] = None) -> str:
        """Promotes staging table to final production table upon explicit human approval."""
        prod_table = f"silver_{table_name}"
        stg_table = staging_table or f"staging_silver_{table_name}"

        if self.target_db:
            tables = self.target_db.list_tables()
            if stg_table in tables:
                self.target_db.execute(f"CREATE OR REPLACE TABLE {prod_table} AS SELECT * FROM {stg_table};")
                self.target_db.execute(f"DROP TABLE IF EXISTS {stg_table};")

        return prod_table

    def generate_uc_catalog_ddl(self, table_name: str, profiles: List[ColumnProfile]) -> Dict[str, str]:
        """Generates Unity Catalog metadata statements."""
        target_table = f"lakehouse.silver.{table_name}"
        ddl_statements = [f"COMMENT ON TABLE {target_table} IS 'Migrated Medallion table from legacy warehouse';"]

        for col in profiles:
            col_name = col["column_name"]
            if col["is_sensitive"]:
                ddl_statements.append(
                    f"ALTER TABLE {target_table} ALTER COLUMN {col_name} SET TAGS ('classification' = 'pii', 'compliance' = 'gdpr');"
                )
            ddl_statements.append(
                f"COMMENT ON COLUMN {target_table}.{col_name} IS 'Target type {col['target_type']} (legacy: {col['legacy_type']})';"
            )

        return {
            "target_table": target_table,
            "ddl_script": "\n".join(ddl_statements),
        }

    def generate_migration_runbook(
        self,
        table_name: str,
        state: MigrationState,
    ) -> str:
        """Generates comprehensive markdown migration audit runbook."""
        metrics = state.get("validation_metrics", [])
        profiles = state.get("profiles", {}).get(table_name, [])
        attempts = state.get("fix_attempts", 0)

        lines = [
            f"# Migration Runbook: {table_name}",
            "",
            "## 1. Migration Summary",
            f"- **Source Entity**: `{table_name}`",
            f"- **Target Lakehouse Table**: `silver_{table_name}` (Promoted from Staging)",
            f"- **Parity Verification**: {'PASSED' if state.get('validation_passed') else 'FAILED'}",
            f"- **Repair Feedback Cycles**: {attempts}",
            "",
            "## 2. Reconciled Parity Metrics",
            "| Metric | Source Value | Target Value | Divergence | Status |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for m in metrics:
            status = "PASSED" if m["passed"] else "FAILED"
            lines.append(
                f"| `{m['metric_name']}` | `{m['source_metric']}` | `{m['target_metric']}` | `{m['divergence_score']}` | {status} |"
            )

        lines.extend([
            "",
            "## 3. Unity Catalog Governance Tags",
            "```sql",
            self.generate_uc_catalog_ddl(table_name, profiles)["ddl_script"],
            "```",
            "",
            "## 4. Generated Artifacts",
            "- Bronze Ingestion Stream PySpark Code",
            "- Silver Medallion Window Deduplication & Cleansing PySpark Code (Salted PII Hash)",
            "- Production Promotion from Staging",
            "",
            "_Generated autonomously by Legacy-to-Lakehouse Migration Copilot._",
        ])

        report = "\n".join(lines)
        report_file = self.runbook_dir / f"migration_runbook_{table_name}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        return report

    def run(self, state: MigrationState) -> Dict[str, Any]:
        """LangGraph node execution."""
        current_table = state.get("current_table", "table")
        profiles = state.get("profiles", {}).get(current_table, [])
        staging_entity = state.get("staging_entity")

        # Promote staging table to production
        self.promote_staging_to_production(current_table, staging_entity)

        uc_meta = self.generate_uc_catalog_ddl(current_table, profiles)
        runbook = self.generate_migration_runbook(current_table, state)

        # Update multi-table queues
        completed = list(state.get("completed_tables", []))
        if current_table not in completed:
            completed.append(current_table)
        pending = [t for t in state.get("pending_tables", []) if t != current_table]
        next_table = pending[0] if pending else ""

        return {
            "catalog_metadata": {current_table: uc_meta},
            "final_migration_report": runbook,
            "completed_tables": completed,
            "pending_tables": pending,
            "current_table": next_table,
            "staging_entity": "",
            # Reset verification counters for next table
            "fix_attempts": 0,
            "diagnostic_feedback": None,
            "validation_passed": False,
        }
