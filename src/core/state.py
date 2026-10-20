from typing import Annotated, Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ColumnProfile(TypedDict):
    column_name: str
    legacy_type: str
    target_type: str
    is_nullable: bool
    is_primary_key: bool
    is_sensitive: bool
    sensitivity_type: Optional[Literal["PII", "PCI", "FINANCIAL", "INTERNAL"]]
    sample_values: List[str]


class TableLineage(TypedDict):
    table_name: str
    upstream_dependencies: List[str]
    downstream_dependents: List[str]
    transformation_depth: int


class CodeArtifact(TypedDict):
    source_entity: str
    target_entity: str
    layer: Literal["bronze", "silver", "gold"]
    pyspark_code: str
    ddl_statement: str
    execution_status: Literal["pending", "executed", "failed"]


class ParityMetric(TypedDict):
    metric_name: str
    source_metric: Any
    target_metric: Any
    divergence_score: float
    tolerance_threshold: float
    passed: bool
    error_message: Optional[str]


class CheckRecord(TypedDict):
    name: str
    description: str
    source_value: Any
    target_value: Any
    tolerance: float
    divergence: float
    status: Literal["PASS", "FAIL", "WARN"]
    error_message: Optional[str]


class AttemptRecord(TypedDict):
    attempt_number: int
    timestamp: str
    diagnosis: str
    patch_diff: str
    failed_checks: List[str]
    result_status: Literal["PASSED", "FAILED"]


class ColumnTreatmentRecord(TypedDict):
    source_col: str
    target_col: str
    source_type: str
    target_type: str
    is_sensitive: bool
    sensitivity_type: Optional[str]
    treatment: Literal["hash", "mask", "keep", "drop"]
    ai_suggested: bool
    sample_before: List[str]
    sample_after: List[str]


class StatementProvenanceRecord(TypedDict):
    statement_index: int
    statement_sql: str
    pyspark_equivalent: str
    provenance: Literal["RULE", "MODEL"]


class NodeTelemetryRecord(TypedDict):
    node_name: str
    duration_ms: float
    model_name: str
    tokens_input: int
    tokens_output: int
    prompt: Optional[str]
    response: Optional[str]


class MigrationState(TypedDict):
    # Message log for multi-agent LLM communication
    messages: Annotated[List[BaseMessage], add_messages]

    # Static Profiling Context
    source_dialect: str                          # e.g., "Oracle", "Netezza", "Teradata"
    raw_ddl_map: Dict[str, str]                  # Table name -> Raw DDL statement
    profiles: Dict[str, List[ColumnProfile]]     # Table name -> Column metadata
    lineage_graph: Dict[str, TableLineage]       # NetworkX-compatible adjacency mapping
    execution_order: List[str]                   # Topologically sorted table list

    # Multi-Table Pipeline Queue
    pending_tables: List[str]                    # Unmigrated tables remaining in execution order
    completed_tables: List[str]                  # Tables successfully validated and promoted
    staging_entity: str                          # Current active staging table name
    table_status_map: Dict[str, str]             # Table -> PROMOTED | NEEDS_REVIEW | FIXING | BLOCKED | QUEUED

    # Active Migration Workspace
    current_table: str                           # Active table under migration
    artifacts: Dict[str, CodeArtifact]           # Layer -> Generated PySpark artifacts
    active_salt: str                             # Salt for PII hashing

    # Evidence & Structured Review (ui-2)
    checks: List[CheckRecord]
    attempts: List[AttemptRecord]
    column_treatments: Dict[str, List[ColumnTreatmentRecord]]
    provenance: List[StatementProvenanceRecord]
    telemetry: List[NodeTelemetryRecord]

    # Verification & Error Recovery
    validation_metrics: List[ParityMetric]
    validation_passed: bool
    fix_attempts: int
    max_retries: int
    diagnostic_feedback: Optional[str]

    # Governance & Approval
    human_approved: bool
    human_feedback: Optional[str]
    catalog_metadata: Dict[str, Dict[str, str]]  # Table/Column descriptions and tags
    final_migration_report: Optional[str]
