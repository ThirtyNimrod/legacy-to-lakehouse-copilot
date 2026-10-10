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


class MigrationState(TypedDict):
    # Message log for multi-agent LLM communication
    messages: Annotated[List[BaseMessage], add_messages]

    # Static Profiling Context
    source_dialect: str                          # e.g., "Oracle", "Netezza", "Teradata"
    raw_ddl_map: Dict[str, str]                  # Table name -> Raw DDL statement
    profiles: Dict[str, List[ColumnProfile]]     # Table name -> Column metadata
    lineage_graph: Dict[str, TableLineage]       # NetworkX-compatible adjacency mapping
    execution_order: List[str]                   # Topologically sorted table list

    # Active Migration Workspace
    current_table: str                           # Active table under migration
    artifacts: Dict[str, CodeArtifact]           # Layer -> Generated PySpark artifacts

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
