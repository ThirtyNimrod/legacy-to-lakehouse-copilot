# Legacy-to-Lakehouse Migration Copilot

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)
[![Databricks](https://img.shields.io/badge/Platform-Databricks-FF3621.svg?logo=databricks&logoColor=white)](https://databricks.com)
[![Storage](https://img.shields.io/badge/Format-Delta_Lake-00A4E4.svg)](https://delta.io)

An autonomous multi-agent engineering copilot that ingests legacy stored procedures and DDL 
(Oracle/Netezza), translates them into PySpark Medallion architectures (Bronze/Silver/Gold), 
and validates migration fidelity using deterministic dual-engine reconciliation gates.

## 🎯 The Problem: The "Unknown-Unknowns" of Migration

Legacy ETL pipelines (Mainframe, Oracle, Netezza) have:
- Zero documentation
- Embedded tribal knowledge
- Undocumented edge cases and business rules
- Subtle type coercion behaviors
- Complex stateful restart logic
- No automated regression suite

**Result:** Every migration is a high-risk, manual, heuristic-driven detective operation.
---

## 🚀 The Solution: The Autonomous Medallion Copilot 

# Directory Architecture
```
legacy-to-lakehouse-copilot/
├── .github/
│   └── workflows/              # Linting, type checks, unit tests
├── configs/
│   └── settings.yaml           # Dialect rules, retry thresholds
├── data/
│   ├── legacy/                 # Olist raw seed CSVs / DuckDB legacy file
│   └── medallion/              # Local DuckDB target tables (Phase 1)
├── src/
│   ├── agents/
│   │   ├── profiler.py         # Schema parsing & NetworkX DAG
│   │   ├── translator.py       # SQLGlot & PySpark generator
│   │   ├── validator.py        # Parity & reconciliation queries
│   │   ├── fixer.py            # Error diagnostics & repair loop
│   │   └── steward.py          # Metadata & Unity Catalog documentation
│   ├── core/
│   │   ├── graph.py            # StateGraph declaration & compilation
│   │   └── state.py            # TypedDict state schema
│   └── tools/
│       ├── database.py         # Swappable DB interfaces (DuckDB / Databricks)
│       └── metrics.py          # Row counts, MD5 hashing, epsilon calculations
├── tests/
│   └── test_reconciliation.py  # Unit assertions on metric checks
├── .env.example
├── .gitignore
├── LICENSE
├── pyproject.toml              # Dependencies & package configuration
└── README.md
```