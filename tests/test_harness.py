def test_harness_seeds_expected_entities(temp_legacy_db):
    runner, db_path, ddl_map = temp_legacy_db
    tables = runner.list_tables()

    assert "raw_customers" in tables
    assert "raw_orders" in tables
    assert "raw_order_payments" in tables
    assert "raw_order_items" in tables
    assert "raw_categories" in tables
    assert "v_order_summary" in tables

    # Verify rows exist
    orders = runner.fetch_all("SELECT * FROM raw_orders")
    assert len(orders) == 5

    payments = runner.fetch_all("SELECT * FROM raw_order_payments")
    assert len(payments) == 4
