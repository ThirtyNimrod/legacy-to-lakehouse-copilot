from src.agents.fixer import FixerAgent
from src.core.state import ParityMetric


def test_fixer_generates_diagnostic_report():
    fixer = FixerAgent()
    failed_metric = ParityMetric(
        metric_name="duplicate_index_parity",
        source_metric=0,
        target_metric=2,
        divergence_score=2.0,
        tolerance_threshold=0.0,
        passed=False,
        error_message="Duplicate keys found",
    )

    report = fixer.generate_diagnostic_payload("raw_orders", [failed_metric])
    assert "DIAGNOSTIC REPORT: raw_orders" in report
    assert "Suspected Mechanism: Window row_number()" in report
    assert "Prescribed Fix:" in report
