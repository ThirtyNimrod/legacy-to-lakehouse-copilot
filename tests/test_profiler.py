from src.agents.profiler import ProfilerAgent


def test_profiler_detects_pii_and_lineage(temp_legacy_db):
    runner, db_path, ddl_map = temp_legacy_db
    profiler = ProfilerAgent(legacy_db=runner)

    # Test customer profile and PII detection
    cust_profiles = profiler.profile_columns("raw_customers", ddl_map["raw_customers"])
    assert len(cust_profiles) > 0

    col_map = {c["column_name"]: c for c in cust_profiles}
    assert col_map["CUST_NAT_DOC_NUM_ID"]["is_sensitive"] is True
    assert col_map["CUST_COMM_EML_ADDR_TX"]["is_sensitive"] is True

    # Test Lineage and DAG
    lineage, exec_order = profiler.build_lineage_and_execution_order(ddl_map)
    assert len(exec_order) == len(ddl_map)
    # v_order_summary depends on raw_orders, so raw_orders must be migrated before v_order_summary
    assert exec_order.index("raw_orders") < exec_order.index("v_order_summary")
