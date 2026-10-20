export interface CheckRecord {
  name: string
  description: string
  source_value: string | number | null
  target_value: string | number | null
  tolerance: number
  divergence: number
  status: 'PASS' | 'FAIL' | 'WARN'
  error_message: string | null
}

export interface ColumnTreatment {
  source_col: string
  target_col: string
  source_type: string
  target_type: string
  is_sensitive: boolean
  sensitivity_type: string | null
  treatment: 'hash' | 'mask' | 'keep' | 'drop'
  ai_suggested: boolean
  sample_before: string[]
  sample_after: string[]
}

export interface StatementProvenance {
  statement_index: number
  statement_sql: string
  pyspark_equivalent: string
  provenance: 'RULE' | 'MODEL'
}

export interface AttemptRecord {
  attempt_number: number
  timestamp: string
  diagnosis: string
  patch_diff: string
  failed_checks: string[]
  result_status: 'PASSED' | 'FAILED'
}

export interface NodeTelemetry {
  node_name: string
  duration_ms: number
  model_name: string
  tokens_input: number
  tokens_output: number
  prompt: string | null
  response: string | null
}

export interface GraphNode {
  id: string
  label: string
  status: 'COMPLETED' | 'RUNNING' | 'HALTED' | 'IDLE' | 'FAILED'
}

export interface TableReviewState {
  thread_id: string
  run_id: string
  current_table: string
  target_environment: string
  model_name: string
  staging_entity: string
  target_entity: string
  status: 'NEEDS_REVIEW' | 'FIXING' | 'PROMOTED' | 'FAILED_CLOSED' | 'ABORTED'
  repair_summary: string
  fix_attempts: number
  max_retries: number
  checks: CheckRecord[]
  column_treatments: ColumnTreatment[]
  provenance: StatementProvenance[]
  attempts: AttemptRecord[]
  telemetry: NodeTelemetry[]
  graph_nodes: GraphNode[]
}

export interface TableRow {
  table_num: number
  table_name: string
  depends_on: string
  checks: string
  attempts: string
  status: string
  thread_id: string
  has_pii: boolean
  pii_count: number
}

export interface RunSummary {
  total_tables: number
  promoted: number
  needs_review: number
  fixing: number
  blocked: number
  display_counter: string
}

export interface BoardData {
  run_id: string
  target_environment: string
  model_name: string
  summary: RunSummary
  tables: TableRow[]
}
