from typing import Any, Dict, List, Optional
from src.core.state import MigrationState, ParityMetric
from src.tools.database import DatabaseRunner
from src.tools.metrics import ParityReconciliationEngine


class ValidatorAgent:
    """Deterministic Reconciliation Engine comparing legacy source and staging lakehouse target."""

    def __init__(self, source_db: DatabaseRunner, target_db: DatabaseRunner, epsilon_tolerance: float = 1e-6):
        self.source_db = source_db
        self.target_db = target_db
        self.engine = ParityReconciliationEngine(epsilon_tolerance=epsilon_tolerance)

    def validate_table(
        self,
        table_name: str,
        primary_key: str = "order_id",
        target_table_name: Optional[str] = None,
    ) -> List[ParityMetric]:
        """Runs the complete suite of mathematical parity assertions against target table."""
        # Validate against staging table if available, else standard target
        if target_table_name:
            target_table = target_table_name
        else:
            tables = self.target_db.list_tables()
            if f"staging_silver_{table_name}" in tables:
                target_table = f"staging_silver_{table_name}"
            else:
                target_table = f"silver_{table_name}"

        metrics: List[ParityMetric] = []

        # 1. Duplicate Index Parity
        dup_metric = self.engine.check_duplicate_index(
            target_db=self.target_db,
            target_table=target_table,
            primary_key_col=primary_key,
        )
        metrics.append(dup_metric)

        # Introspect shared columns
        s_schema = self.source_db.get_table_schema(table_name)
        t_schema = self.target_db.get_table_schema(target_table)
        s_cols = {c["column_name"].lower() for c in s_schema}
        t_cols = {c["column_name"].lower() for c in t_schema}
        common_cols = list(s_cols.intersection(t_cols))

        # Check numeric epsilon if numeric columns exist
        numeric_cols = [
            c["column_name"] for c in s_schema
            if any(num_t in str(c["column_type"]).upper() for num_t in ["DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "INT"])
            and c["column_name"].lower() in t_cols
        ]
        for ncol in numeric_cols:
            num_metric = self.engine.check_numeric_epsilon(
                source_db=self.source_db,
                target_db=self.target_db,
                source_table=table_name,
                target_table=target_table,
                source_col=ncol,
                target_col=ncol,
            )
            metrics.append(num_metric)

        # Check null distribution on a primary attribute
        non_pk_cols = [c for c in common_cols if c != primary_key]
        if non_pk_cols:
            test_col = non_pk_cols[0]
            null_metric = self.engine.check_null_distribution(
                source_db=self.source_db,
                target_db=self.target_db,
                source_table=table_name,
                target_table=target_table,
                source_col=test_col,
                target_col=test_col,
            )
            metrics.append(null_metric)

        # Row count check against distinct source PK count
        s_distinct = self.source_db.fetch_one(f"SELECT COUNT(DISTINCT {primary_key}) AS cnt FROM {table_name}")
        t_count = self.target_db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {target_table}")
        s_expected = int(s_distinct["cnt"]) if s_distinct else 0
        t_actual = int(t_count["cnt"]) if t_count else 0
        row_diff = abs(s_expected - t_actual)
        passed_row = (row_diff == 0)

        metrics.append(
            ParityMetric(
                metric_name="deduplicated_cardinality_balance",
                source_metric=s_expected,
                target_metric=t_actual,
                divergence_score=float(row_diff),
                tolerance_threshold=0.0,
                passed=passed_row,
                error_message=None if passed_row else f"Target row count {t_actual} does not match expected unique source entities {s_expected}",
            )
        )

        return metrics

    def run(self, state: MigrationState) -> Dict[str, Any]:
        """LangGraph node execution."""
        current_table = state.get("current_table")
        if not current_table:
            return {"validation_metrics": [], "validation_passed": True}

        profiles = state.get("profiles", {}).get(current_table, [])
        pk_cols = [p["column_name"] for p in profiles if p["is_primary_key"]]
        primary_key = pk_cols[0] if pk_cols else "order_id"
        staging_entity = state.get("staging_entity")

        metrics = self.validate_table(current_table, primary_key, target_table_name=staging_entity)
        all_passed = all(m["passed"] for m in metrics)

        return {
            "validation_metrics": metrics,
            "validation_passed": all_passed,
        }
