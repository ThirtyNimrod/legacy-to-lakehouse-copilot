# Migration Runbook: raw_orders

## 1. Migration Summary
- **Source Entity**: `raw_orders`
- **Target Lakehouse Table**: `silver_raw_orders`
- **Parity Verification**: PASSED
- **Repair Feedback Cycles**: 0

## 2. Reconciled Parity Metrics
| Metric | Source Value | Target Value | Divergence | Status |
| :--- | :--- | :--- | :--- | :--- |
| `duplicate_index_parity` | `0` | `0` | `0.0` | PASSED |
| `null_distribution_customer_id` | `0.0` | `0.0` | `0.0` | PASSED |
| `deduplicated_cardinality_balance` | `4` | `4` | `0.0` | PASSED |

## 3. Unity Catalog Governance Tags
```sql
COMMENT ON TABLE lakehouse.silver.raw_orders IS 'Migrated Medallion table from legacy warehouse';
COMMENT ON COLUMN lakehouse.silver.raw_orders.order_id IS 'Target type STRING (legacy: VARCHAR)';
COMMENT ON COLUMN lakehouse.silver.raw_orders.customer_id IS 'Target type STRING (legacy: VARCHAR)';
COMMENT ON COLUMN lakehouse.silver.raw_orders.order_status_history IS 'Target type STRING (legacy: VARCHAR)';
COMMENT ON COLUMN lakehouse.silver.raw_orders.order_purchase_date_str IS 'Target type STRING (legacy: VARCHAR)';
COMMENT ON COLUMN lakehouse.silver.raw_orders.ingest_date IS 'Target type STRING (legacy: VARCHAR)';
```

## 4. Generated Artifacts
- Bronze Ingestion Stream PySpark Code
- Silver Medallion Window Deduplication & Cleansing PySpark Code

_Generated autonomously by Legacy-to-Lakehouse Migration Copilot._