import re
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage
import networkx as nx
import sqlglot
from sqlglot import exp
from src.core.state import ColumnProfile, MigrationState, TableLineage
from src.llm.factory import get_chat_model
from src.tools.database import DatabaseRunner


class ProfilerAgent:
    """Reverse-engineers legacy DDLs, builds lineage DAGs, and detects PII."""

    PII_REGEX_MAP = {
        "PII_EMAIL": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
        "PII_CPF": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
        "PII_PHONE": re.compile(r"(\+?\d{2}\s?)?(\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}"),
    }

    def __init__(self, legacy_db: DatabaseRunner):
        self.legacy_db = legacy_db
        self.llm = get_chat_model()

    def profile_columns(self, table_name: str, ddl: str) -> List[ColumnProfile]:
        """Extracts column metadata and checks sample values for sensitive patterns."""
        parsed = sqlglot.parse_one(ddl, read="oracle")
        columns: List[ColumnProfile] = []

        # Introspect table schema from DuckDB
        schema_rows = self.legacy_db.get_table_schema(table_name)
        schema_lookup = {r["column_name"].lower(): r for r in schema_rows}

        # Query sample rows to evaluate data privacy / PII
        samples = self.legacy_db.fetch_all(f"SELECT * FROM {table_name} LIMIT 5")

        for col_def in parsed.find_all(exp.ColumnDef):
            col_name = col_def.name
            data_type = str(col_def.kind) if col_def.kind else "VARCHAR"
            is_pk = bool(col_def.find(exp.PrimaryKeyColumnConstraint))

            # Fetch sample string values for regex scanning
            col_samples = [str(row.get(col_name, "")) for row in samples if row.get(col_name) is not None]

            # Detect PII
            is_sensitive = False
            sens_type: Optional[Any] = None
            for pii_name, pattern in self.PII_REGEX_MAP.items():
                for sample_val in col_samples:
                    if pattern.search(sample_val):
                        is_sensitive = True
                        sens_type = "PII"
                        break
                if is_sensitive:
                    break

            # Fallback sensitivity check on column name
            if not is_sensitive and any(k in col_name.lower() for k in ["doc", "eml", "tel", "tax", "cpf"]):
                is_sensitive = True
                sens_type = "PII"

            db_info = schema_lookup.get(col_name.lower(), {})
            is_nullable = db_info.get("null", True)

            columns.append(
                ColumnProfile(
                    column_name=col_name,
                    legacy_type=data_type,
                    target_type=self._map_legacy_type(data_type),
                    is_nullable=is_nullable,
                    is_primary_key=is_pk,
                    is_sensitive=is_sensitive,
                    sensitivity_type=sens_type,
                    sample_values=col_samples[:3],
                )
            )

        return columns

    def _map_legacy_type(self, legacy_type: str) -> str:
        """Maps legacy database types to Lakehouse Delta types."""
        lt = legacy_type.upper()
        if "INT" in lt:
            return "BIGINT"
        elif "DOUBLE" in lt or "FLOAT" in lt or "NUMBER" in lt:
            return "DECIMAL(18, 2)"
        elif "DATE" in lt or "TIME" in lt:
            return "TIMESTAMP"
        return "STRING"

    def build_lineage_and_execution_order(self, raw_ddl_map: Dict[str, str]) -> tuple[Dict[str, TableLineage], List[str]]:
        """Constructs NetworkX DAG and derives topological migration order."""
        G = nx.DiGraph()

        # Add all tables to graph
        for table in raw_ddl_map.keys():
            G.add_node(table)

        # Detect foreign keys or view table dependencies
        for table, ddl in raw_ddl_map.items():
            parsed = sqlglot.parse_one(ddl, read="oracle")
            for table_ref in parsed.find_all(exp.Table):
                ref_name = table_ref.name
                if ref_name in raw_ddl_map and ref_name != table:
                    # Upstream -> Downstream edge: ref_name must be migrated before table
                    G.add_edge(ref_name, table)

        # Compute topological order
        try:
            exec_order = list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible:
            # Cyclic dependency fallback
            exec_order = list(raw_ddl_map.keys())

        lineage_map: Dict[str, TableLineage] = {}
        for node in G.nodes():
            upstreams = list(G.predecessors(node))
            downstreams = list(G.successors(node))
            depth = nx.shortest_path_length(G, target=node) if upstreams else 0
            lineage_map[node] = TableLineage(
                table_name=node,
                upstream_dependencies=upstreams,
                downstream_dependents=downstreams,
                transformation_depth=int(depth) if isinstance(depth, int) else 0,
            )

        return lineage_map, exec_order

    def run(self, state: MigrationState) -> Dict[str, Any]:
        """LangGraph node execution."""
        ddl_map = state.get("raw_ddl_map", {})
        profiles: Dict[str, List[ColumnProfile]] = {}

        for table_name, ddl in ddl_map.items():
            profiles[table_name] = self.profile_columns(table_name, ddl)

        lineage_map, exec_order = self.build_lineage_and_execution_order(ddl_map)

        # LLM semantic inference prompt
        prompt = (
            f"Profiler analysis for legacy tables: {list(ddl_map.keys())}.\n"
            "Infer semantic business definitions and lakehouse column mappings."
        )
        ai_msg = self.llm.invoke([HumanMessage(content=prompt)])

        cur_tbl = exec_order[0] if exec_order else ""

        # Build column_treatments and initial table_status_map per ui-2.md
        column_treatments: Dict[str, Any] = {}
        for tbl, col_list in profiles.items():
            treatments = []
            for col in col_list:
                s_name = col["column_name"]
                is_sens = col.get("is_sensitive", False)
                sens_type = col.get("sensitivity_type")
                if is_sens and any(k in s_name.lower() for k in ["doc", "cpf", "tax", "ssn"]):
                    treat = "hash"
                elif is_sens:
                    treat = "mask"
                else:
                    treat = "keep"

                # Safe masked samples
                raw_samples = col.get("sample_values", [])[:3]
                if is_sens:
                    samples_before = ["***MASKED***" for _ in raw_samples]
                    samples_after = ["***HASHED***" if treat == "hash" else "***MASKED***" for _ in raw_samples]
                else:
                    samples_before = raw_samples
                    samples_after = raw_samples

                treatments.append({
                    "source_col": s_name,
                    "target_col": s_name,
                    "source_type": col.get("legacy_type", "VARCHAR"),
                    "target_type": col.get("target_type", "STRING"),
                    "is_sensitive": is_sens,
                    "sensitivity_type": sens_type,
                    "treatment": treat,
                    "ai_suggested": bool(is_sens or col.get("legacy_type") != col.get("target_type")),
                    "sample_before": samples_before,
                    "sample_after": samples_after,
                })
            column_treatments[tbl] = treatments

        # Build table status map
        status_map: Dict[str, str] = {}
        for idx, tbl in enumerate(exec_order):
            if idx == 0:
                status_map[tbl] = "NEEDS_REVIEW"
            else:
                upstreams = lineage_map.get(tbl, {}).get("upstream_dependencies", [])
                if upstreams:
                    status_map[tbl] = f"BLOCKED (waits on {', '.join(upstreams)})"
                else:
                    status_map[tbl] = "QUEUED"

        return {
            "profiles": profiles,
            "lineage_graph": lineage_map,
            "execution_order": exec_order,
            "current_table": cur_tbl,
            "pending_tables": exec_order[1:] if len(exec_order) > 1 else [],
            "completed_tables": [],
            "column_treatments": column_treatments,
            "table_status_map": status_map,
            "messages": [ai_msg],
        }

