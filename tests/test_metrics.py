from src.tools.metrics import ParityReconciliationEngine


def test_parity_metrics_assertions(temp_legacy_db, temp_target_db):
    s_runner, s_path, _ = temp_legacy_db
    t_runner, t_path = temp_target_db

    # Create matching table in target
    schema = s_runner.get_table_schema("raw_order_payments")
    cols_def = ", ".join([f"{c['column_name']} {c['column_type']}" for c in schema])
    t_runner.execute(f"CREATE TABLE silver_test ({cols_def});")
    rows = s_runner.fetch_all("SELECT * FROM raw_order_payments")
    cols = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    for r in rows:
        t_runner.execute(f"INSERT INTO silver_test ({', '.join(cols)}) VALUES ({placeholders})", [r[c] for c in cols])

    engine = ParityReconciliationEngine(epsilon_tolerance=1e-6)

    # 1. Row count balance
    row_metric = engine.check_row_count(s_runner, t_runner, "raw_order_payments", "silver_test")
    assert row_metric["passed"] is True
    assert row_metric["divergence_score"] == 0.0

    # 2. Duplicate index parity
    dup_metric = engine.check_duplicate_index(t_runner, "silver_test", "payment_id")
    assert dup_metric["passed"] is True

    # 3. Numeric epsilon variance
    eps_metric = engine.check_numeric_epsilon(
        s_runner, t_runner, "raw_order_payments", "silver_test", "payment_value", "payment_value"
    )
    assert eps_metric["passed"] is True
    assert eps_metric["divergence_score"] <= 1e-6

    # 4. Null distribution
    null_metric = engine.check_null_distribution(
        s_runner, t_runner, "raw_order_payments", "silver_test", "payment_type", "payment_type"
    )
    assert null_metric["passed"] is True
