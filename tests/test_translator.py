from src.agents.translator import TranslatorAgent
from src.core.state import ColumnProfile


def test_translator_generates_pyspark_artifacts(temp_target_db):
    t_runner, _ = temp_target_db
    translator = TranslatorAgent(target_db=t_runner)

    cols = [
        ColumnProfile(
            column_name="order_id",
            legacy_type="VARCHAR",
            target_type="STRING",
            is_nullable=False,
            is_primary_key=True,
            is_sensitive=False,
            sensitivity_type=None,
            sample_values=["o_1001"],
        ),
        ColumnProfile(
            column_name="email",
            legacy_type="VARCHAR",
            target_type="STRING",
            is_nullable=True,
            is_primary_key=False,
            is_sensitive=True,
            sensitivity_type="PII",
            sample_values=["a@b.com"],
        ),
    ]

    artifacts = translator.translate_to_pyspark("orders", cols, "order_id")
    assert "bronze" in artifacts
    assert "silver" in artifacts

    bronze_code = artifacts["bronze"]["pyspark_code"]
    silver_code = artifacts["silver"]["pyspark_code"]

    assert "cloudFiles" in bronze_code
    assert "Window.partitionBy" in silver_code
    assert "sha2" in silver_code  # PII redaction
