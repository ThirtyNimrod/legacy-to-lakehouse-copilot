from src.agents.steward import StewardAgent
from src.agents.translator import TranslatorAgent


def test_staging_isolation_and_promotion(temp_legacy_db, temp_target_db):
    s_runner, s_path, ddl_map = temp_legacy_db
    t_runner, t_path = temp_target_db

    translator = TranslatorAgent(target_db=t_runner, source_db=s_runner)
    steward = StewardAgent(target_db=t_runner)

    # 1. Translate entity into staging
    stg_table = translator.execute_target_duckdb(
        table_name="raw_orders",
        source_ddl=ddl_map["raw_orders"],
        diagnostic_feedback="repaired",
    )
    assert stg_table == "staging_silver_raw_orders"

    tables_before = t_runner.list_tables()
    assert "staging_silver_raw_orders" in tables_before
    assert "silver_raw_orders" not in tables_before, "Production table must NOT exist before human approval"

    # 2. Promote to production
    prod_table = steward.promote_staging_to_production("raw_orders", stg_table)
    assert prod_table == "silver_raw_orders"

    tables_after = t_runner.list_tables()
    assert "silver_raw_orders" in tables_after, "Production table must exist after promotion"
    assert "staging_silver_raw_orders" not in tables_after, "Staging table must be dropped after promotion"


def test_abort_drops_staging_and_preserves_clean_production(temp_legacy_db, temp_target_db):
    s_runner, s_path, ddl_map = temp_legacy_db
    t_runner, t_path = temp_target_db

    translator = TranslatorAgent(target_db=t_runner, source_db=s_runner)

    stg_table = translator.execute_target_duckdb(
        table_name="raw_orders",
        source_ddl=ddl_map["raw_orders"],
        diagnostic_feedback="repaired",
    )
    assert "staging_silver_raw_orders" in t_runner.list_tables()

    # Operator aborts: drop staging table
    t_runner.execute(f"DROP TABLE IF EXISTS {stg_table};")

    tables = t_runner.list_tables()
    assert "staging_silver_raw_orders" not in tables
    assert "silver_raw_orders" not in tables
