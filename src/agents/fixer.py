from typing import Any, Dict, List
from langchain_core.messages import AIMessage
from src.core.state import MigrationState, ParityMetric
from src.llm.factory import get_chat_model


class FixerAgent:
    """Diagnoses validation failures and prescribes deterministic PySpark/SQL repairs."""

    def __init__(self):
        self.llm = get_chat_model()

    def generate_diagnostic_payload(
        self,
        current_table: str,
        failed_metrics: List[ParityMetric],
    ) -> str:
        """Constructs structured diagnostic payload described in architectural blueprint."""
        diagnostics = [f"=== DIAGNOSTIC REPORT: {current_table} ==="]

        for m in failed_metrics:
            diagnostics.append(f"• Failure Target: {current_table}.{m['metric_name']}")
            diagnostics.append(f"• Divergence Score: {m['divergence_score']}")
            diagnostics.append(f"• Source Metric: {m['source_metric']}")
            diagnostics.append(f"• Target Metric: {m['target_metric']}")
            diagnostics.append(f"• Error Message: {m.get('error_message')}")

            # Root-cause deduction
            if "duplicate" in m["metric_name"] or "cardinality" in m["metric_name"]:
                diagnostics.append(
                    "• Suspected Mechanism: Window row_number() deduplication missing explicit secondary tie-breaker."
                )
                diagnostics.append(
                    "• Prescribed Fix: Append unique primary key column to window orderBy clause."
                )
            elif "numeric" in m["metric_name"]:
                diagnostics.append(
                    "• Suspected Mechanism: Implicit float truncation or missing coalesce in null values."
                )
                diagnostics.append(
                    "• Prescribed Fix: Cast to DECIMAL(18, 2) and enforce COALESCE(col, 0.0)."
                )
            elif "null" in m["metric_name"]:
                diagnostics.append(
                    "• Suspected Mechanism: Oracle treats empty string '' as NULL while lakehouse preserves empty string."
                )
                diagnostics.append(
                    "• Prescribed Fix: Enforce NULLIF(TRIM(col), '') in transformation layer."
                )

        diagnostics.append("=========================================")
        return "\n".join(diagnostics)

    def run(self, state: MigrationState) -> Dict[str, Any]:
        """LangGraph node execution."""
        current_table = state.get("current_table", "unknown")
        metrics = state.get("validation_metrics", [])
        failed = [m for m in metrics if not m.get("passed", False)]

        # Check human feedback if rejected at HITL breakpoint
        human_feedback = state.get("human_feedback")
        feedback_text = ""
        if human_feedback:
            feedback_text = f"Human operator feedback: {human_feedback}\n"

        import datetime

        diagnostic_payload = feedback_text + self.generate_diagnostic_payload(current_table, failed)
        current_attempts = state.get("fix_attempts", 0) + 1

        attempts = list(state.get("attempts", []))
        failed_check_names = [m.get("metric_name", "") for m in failed]
        attempts.append({
            "attempt_number": current_attempts,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "diagnosis": diagnostic_payload,
            "patch_diff": "Prescribed transformation refinement in Translator repair loop",
            "failed_checks": failed_check_names,
            "result_status": "FAILED",
        })

        ai_msg = AIMessage(content=f"Fixer Agent diagnostic:\n{diagnostic_payload}")

        return {
            "diagnostic_feedback": diagnostic_payload,
            "fix_attempts": current_attempts,
            "attempts": attempts,
            "messages": [ai_msg],
        }
