from typing import Any, Dict, List, Optional
from src.core.state import ParityMetric
from src.tools.database import DatabaseRunner


class ParityReconciliationEngine:
    """Computes mathematical ground-truth parity proofs between legacy source and target lakehouse."""

    def __init__(self, epsilon_tolerance: float = 1e-6):
        self.epsilon_tolerance = epsilon_tolerance

    def check_row_count(
        self,
        source_db: DatabaseRunner,
        target_db: DatabaseRunner,
        source_table: str,
        target_table: str,
    ) -> ParityMetric:
        """1. Row Cardinality Balance: |N_source - N_target| == 0"""
        s_res = source_db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {source_table}")
        t_res = target_db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {target_table}")
        s_count = int(s_res["cnt"]) if s_res else 0
        t_count = int(t_res["cnt"]) if t_res else 0

        diff = abs(s_count - t_count)
        passed = (diff == 0)

        return ParityMetric(
            metric_name="row_cardinality_balance",
            source_metric=s_count,
            target_metric=t_count,
            divergence_score=float(diff),
            tolerance_threshold=0.0,
            passed=passed,
            error_message=None if passed else f"Row count mismatch: source={s_count}, target={t_count}, delta={diff}",
        )

    def check_duplicate_index(
        self,
        target_db: DatabaseRunner,
        target_table: str,
        primary_key_col: str,
    ) -> ParityMetric:
        """2. Duplicate Index Parity: (N_target - |DISTINCT K_pk|) == 0"""
        res = target_db.fetch_one(
            f"SELECT COUNT(*) AS total_cnt, COUNT(DISTINCT {primary_key_col}) AS distinct_cnt FROM {target_table}"
        )
        total_cnt = int(res["total_cnt"]) if res else 0
        distinct_cnt = int(res["distinct_cnt"]) if res else 0

        dup_count = total_cnt - distinct_cnt
        passed = (dup_count == 0)

        return ParityMetric(
            metric_name="duplicate_index_parity",
            source_metric=0,
            target_metric=dup_count,
            divergence_score=float(dup_count),
            tolerance_threshold=0.0,
            passed=passed,
            error_message=None if passed else f"Found {dup_count} duplicate keys in target for PK column '{primary_key_col}'",
        )

    def check_checksum(
        self,
        source_db: DatabaseRunner,
        target_db: DatabaseRunner,
        source_table: str,
        target_table: str,
        common_columns: List[str],
    ) -> ParityMetric:
        """3. MD5 Checksum Equivalence across shared columns."""
        if not common_columns:
            return ParityMetric(
                metric_name="checksum_equivalence",
                source_metric=None,
                target_metric=None,
                divergence_score=1.0,
                tolerance_threshold=0.0,
                passed=False,
                error_message="No common columns specified for checksum computation",
            )

        concat_cols_source = ", ".join([f"COALESCE(CAST({c} AS VARCHAR), '__NULL__')" for c in common_columns])
        concat_cols_target = ", ".join([f"COALESCE(CAST({c} AS VARCHAR), '__NULL__')" for c in common_columns])

        # DuckDB supports md5 and xor_agg / string agg for deterministic checksum across rows
        s_query = f"""
            SELECT md5(string_agg(row_hash, '' ORDER BY row_hash)) AS batch_checksum
            FROM (
                SELECT md5(concat_ws('||', {concat_cols_source})) AS row_hash
                FROM {source_table}
            )
        """
        t_query = f"""
            SELECT md5(string_agg(row_hash, '' ORDER BY row_hash)) AS batch_checksum
            FROM (
                SELECT md5(concat_ws('||', {concat_cols_target})) AS row_hash
                FROM {target_table}
            )
        """

        s_res = source_db.fetch_one(s_query)
        t_res = target_db.fetch_one(t_query)
        s_hash = s_res.get("batch_checksum") if s_res else None
        t_hash = t_res.get("batch_checksum") if t_res else None

        passed = (s_hash is not None and s_hash == t_hash)

        return ParityMetric(
            metric_name="checksum_equivalence",
            source_metric=s_hash,
            target_metric=t_hash,
            divergence_score=0.0 if passed else 1.0,
            tolerance_threshold=0.0,
            passed=passed,
            error_message=None if passed else f"MD5 checksum mismatch: source={s_hash}, target={t_hash}",
        )

    def check_numeric_epsilon(
        self,
        source_db: DatabaseRunner,
        target_db: DatabaseRunner,
        source_table: str,
        target_table: str,
        source_col: str,
        target_col: str,
    ) -> ParityMetric:
        """4. Numeric Metric Epsilon Variance: |(sum_target - sum_source) / sum_source| <= epsilon"""
        s_res = source_db.fetch_one(f"SELECT SUM(CAST({source_col} AS DOUBLE)) AS col_sum FROM {source_table}")
        t_res = target_db.fetch_one(f"SELECT SUM(CAST({target_col} AS DOUBLE)) AS col_sum FROM {target_table}")

        s_sum = float(s_res["col_sum"]) if s_res and s_res["col_sum"] is not None else 0.0
        t_sum = float(t_res["col_sum"]) if t_res and t_res["col_sum"] is not None else 0.0

        if s_sum == 0.0:
            divergence = abs(t_sum - s_sum)
        else:
            divergence = abs(t_sum - s_sum) / abs(s_sum)

        passed = divergence <= self.epsilon_tolerance

        return ParityMetric(
            metric_name=f"numeric_epsilon_{target_col}",
            source_metric=s_sum,
            target_metric=t_sum,
            divergence_score=divergence,
            tolerance_threshold=self.epsilon_tolerance,
            passed=passed,
            error_message=None if passed else f"Numeric divergence {divergence:.8f} exceeds tolerance {self.epsilon_tolerance} (source={s_sum}, target={t_sum})",
        )

    def check_null_distribution(
        self,
        source_db: DatabaseRunner,
        target_db: DatabaseRunner,
        source_table: str,
        target_table: str,
        source_col: str,
        target_col: str,
    ) -> ParityMetric:
        """5. Null Distribution Invariance: |NullCount_source / N_source - NullCount_target / N_target| == 0"""
        s_res = source_db.fetch_one(
            f"SELECT COUNT(*) AS n_total, SUM(CASE WHEN {source_col} IS NULL THEN 1 ELSE 0 END) AS n_null FROM {source_table}"
        )
        t_res = target_db.fetch_one(
            f"SELECT COUNT(*) AS n_total, SUM(CASE WHEN {target_col} IS NULL THEN 1 ELSE 0 END) AS n_null FROM {target_table}"
        )

        s_total = float(s_res["n_total"]) if s_res and s_res["n_total"] else 1.0
        s_null = float(s_res["n_null"]) if s_res and s_res["n_null"] is not None else 0.0
        t_total = float(t_res["n_total"]) if t_res and t_res["n_total"] else 1.0
        t_null = float(t_res["n_null"]) if t_res and t_res["n_null"] is not None else 0.0

        s_ratio = s_null / s_total
        t_ratio = t_null / t_total
        diff = abs(s_ratio - t_ratio)
        passed = diff <= self.epsilon_tolerance

        return ParityMetric(
            metric_name=f"null_distribution_{target_col}",
            source_metric=s_ratio,
            target_metric=t_ratio,
            divergence_score=diff,
            tolerance_threshold=self.epsilon_tolerance,
            passed=passed,
            error_message=None if passed else f"Null ratio difference {diff:.6f} (source={s_ratio:.4f}, target={t_ratio:.4f})",
        )
