# Migration Runbook: raw_customers

## 1. Migration Summary
- **Source Entity**: `raw_customers`
- **Target Lakehouse Table**: `silver_raw_customers` (Promoted from Staging)
- **Parity Verification**: PASSED
- **Repair Feedback Cycles**: 0

## 2. Reconciled Parity Metrics
| Metric | Source Value | Target Value | Divergence | Status |
| :--- | :--- | :--- | :--- | :--- |
| `duplicate_index_parity` | `0` | `0` | `0.0` | PASSED |
| `null_distribution_cust_state_cd_tx` | `0.0` | `0.0` | `0.0` | PASSED |
| `deduplicated_cardinality_balance` | `5` | `5` | `0.0` | PASSED |

## 3. Unity Catalog Governance Tags
```sql
COMMENT ON TABLE lakehouse.silver.raw_customers IS 'Migrated Medallion table from legacy warehouse';
COMMENT ON COLUMN lakehouse.silver.raw_customers.CUST_LST_ADDR_ID_TX IS 'Target type STRING (legacy: VARCHAR)';
ALTER TABLE lakehouse.silver.raw_customers ALTER COLUMN CUST_NAT_DOC_NUM_ID SET TAGS ('classification' = 'pii', 'compliance' = 'gdpr');
COMMENT ON COLUMN lakehouse.silver.raw_customers.CUST_NAT_DOC_NUM_ID IS 'Target type STRING (legacy: VARCHAR)';
ALTER TABLE lakehouse.silver.raw_customers ALTER COLUMN CUST_COMM_EML_ADDR_TX SET TAGS ('classification' = 'pii', 'compliance' = 'gdpr');
COMMENT ON COLUMN lakehouse.silver.raw_customers.CUST_COMM_EML_ADDR_TX IS 'Target type STRING (legacy: VARCHAR)';
ALTER TABLE lakehouse.silver.raw_customers ALTER COLUMN CUST_TEL_NUM_TX SET TAGS ('classification' = 'pii', 'compliance' = 'gdpr');
COMMENT ON COLUMN lakehouse.silver.raw_customers.CUST_TEL_NUM_TX IS 'Target type STRING (legacy: VARCHAR)';
COMMENT ON COLUMN lakehouse.silver.raw_customers.CUST_CITY_NAME_TX IS 'Target type STRING (legacy: VARCHAR)';
COMMENT ON COLUMN lakehouse.silver.raw_customers.CUST_STATE_CD_TX IS 'Target type STRING (legacy: VARCHAR)';
```

## 4. Generated Artifacts
- Bronze Ingestion Stream PySpark Code
- Silver Medallion Window Deduplication & Cleansing PySpark Code (Salted PII Hash)
- Production Promotion from Staging

_Generated autonomously by Legacy-to-Lakehouse Migration Copilot._