from src.agents.fixer import FixerAgent
from src.agents.translator import TranslatorAgent
from src.agents.validator import ValidatorAgent
from src.tools.database import DuckDBRunner
from src.tools.harness import LegacyWarehouseHarness


def test_repair_loop_convergence_on_duplicate_ties(temp_legacy_db, temp_target_db):
    """Proves that seeded duplicate flaws fail Pass 0, trigger Fixer diagnostics, and converge on Pass 1."""
    s_runner, s_path, ddl_map = temp_legacy_db
    t_runner, t_path = temp_target_db

    translator = TranslatorAgent(target_db=t_runner, source_db=s_runner)
    validator = ValidatorAgent(source_db=s_runner, target_db=t_runner)
    fixer = FixerAgent()

    # Pass 0: Naive translation without diagnostic feedback
    stg_table = translator.execute_target_duckdb(
        table_name="raw_orders",
        source_ddl=ddl_map["raw_orders"],
        diagnostic_feedback=None,
    )
    assert stg_table == "staging_silver_raw_orders"

    # Pass 0 Validation MUST FAIL on duplicate index and cardinality balance
    metrics_pass_0 = validator.validate_table("raw_orders", primary_key="order_id", target_table_name=stg_table)
    failed_pass_0 = [m for m in metrics_pass_0 if not m["passed"]]
    assert len(failed_pass_0) > 0, "Pass 0 must fail on seeded duplicate flaw"

    dup_metric = [m for m in failed_pass_0 if m["metric_name"] == "duplicate_index_parity"][0]
    assert dup_metric["divergence_score"] > 0

    # Fixer diagnoses failure
    diagnostic_report = fixer.generate_diagnostic_payload("raw_orders", failed_pass_0)
    assert "DIAGNOSTIC REPORT: raw_orders" in diagnostic_report
    assert "Window row_number() deduplication missing" in diagnostic_report

    # Pass 1: Repaired translation with diagnostic feedback applied
    stg_table_repaired = translator.execute_target_duckdb(
        table_name="raw_orders",
        source_ddl=ddl_map["raw_orders"],
        diagnostic_feedback=diagnostic_report,
    )

    # Pass 1 Validation MUST PASS
    metrics_pass_1 = validator.validate_table("raw_orders", primary_key="order_id", target_table_name=stg_table_repaired)
    failed_pass_1 = [m for m in metrics_pass_1 if not m["passed"]]
    assert len(failed_pass_1) == 0, f"Pass 1 must achieve parity, but got failures: {failed_pass_1}"

    # Verify 0 duplicate keys remain
    dup_metric_1 = [m for m in metrics_pass_1 if m["metric_name"] == "duplicate_index_parity"][0]
    assert dup_metric_1["passed"] is True
    assert dup_metric_1["divergence_score"] == 0.0


def test_repair_loop_convergence_on_float_drift(temp_legacy_db, temp_target_db):
    """Proves that integer/float currency truncation fails Pass 0 and converges to decimal on Pass 1."""
    s_runner, s_path, ddl_map = temp_legacy_db
    t_runner, t_path = temp_target_db

    translator = TranslatorAgent(target_db=t_runner, source_db=s_runner)
    validator = ValidatorAgent(source_db=s_runner, target_db=t_runner)
    fixer = FixerAgent()

    # Pass 0: Naive cast to BIGINT
    stg_table = translator.execute_target_duckdb(
        table_name="raw_order_payments",
        source_ddl=ddl_map["raw_order_payments"],
        diagnostic_feedback=None,
    )

    # Pass 0 Validation MUST FAIL on numeric epsilon
    metrics_0 = validator.validate_table("raw_order_payments", primary_key="payment_id", target_table_name=stg_table)
    failed_0 = [m for m in metrics_0 if not m["passed"]]
    assert len(failed_0) > 0
    assert any("numeric_epsilon" in m["metric_name"] for m in failed_0)

    # Fixer diagnoses float/truncation failure
    diag = fixer.generate_diagnostic_payload("raw_order_payments", failed_0)
    assert "truncation" in diag.lower() or "numeric" in diag.lower()

    # Pass 1: Repaired translation with DECIMAL(18, 2)
    stg_table_1 = translator.execute_target_duckdb(
        table_name="raw_order_payments",
        source_ddl=ddl_map["raw_order_payments"],
        diagnostic_feedback=diag,
    )

    metrics_1 = validator.validate_table("raw_order_payments", primary_key="payment_id", target_table_name=stg_table_1)
    failed_1 = [m for m in metrics_1 if not m["passed"]]
    assert len(failed_1) == 0, f"Pass 1 must achieve numeric parity, but got: {failed_1}"
