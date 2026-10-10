from src.agents.translator import TranslatorAgent
from src.agents.validator import ValidatorAgent


def test_validator_detects_parity(temp_legacy_db, temp_target_db):
    s_runner, s_path, ddl_map = temp_legacy_db
    t_runner, t_path = temp_target_db

    # Setup target silver table with deduplication using translator
    translator = TranslatorAgent(target_db=t_runner, source_db=s_runner)
    translator.execute_target_duckdb("raw_orders", ddl_map["raw_orders"], diagnostic_feedback="repaired")

    validator = ValidatorAgent(source_db=s_runner, target_db=t_runner)
    metrics = validator.validate_table("raw_orders", primary_key="order_id")

    assert len(metrics) > 0
    dup_m = [m for m in metrics if m["metric_name"] == "duplicate_index_parity"][0]
    assert dup_m["passed"] is True
