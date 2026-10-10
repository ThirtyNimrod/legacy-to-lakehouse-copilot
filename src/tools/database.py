from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb


class DatabaseRunner(ABC):
    """Abstract interface for database query execution and introspection."""

    @abstractmethod
    def execute(self, query: str, params: Optional[List[Any]] = None) -> None:
        pass

    @abstractmethod
    def fetch_all(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def fetch_one(self, query: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_tables(self) -> List[str]:
        pass


class DuckDBRunner(DatabaseRunner):
    """Local DuckDB database runner."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)

    def execute(self, query: str, params: Optional[List[Any]] = None) -> None:
        if params:
            self.conn.execute(query, params)
        else:
            self.conn.execute(query)

    def fetch_all(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        rel = self.conn.execute(query, params) if params else self.conn.execute(query)
        columns = [desc[0] for desc in rel.description] if rel.description else []
        rows = rel.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, query: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
        results = self.fetch_all(query, params)
        return results[0] if results else None

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        query = f"DESCRIBE {table_name}"
        rows = self.fetch_all(query)
        schema = []
        for r in rows:
            schema.append({
                "column_name": r.get("column_name"),
                "column_type": r.get("column_type"),
                "null": r.get("null") == "YES",
                "key": r.get("key"),
                "default": r.get("default"),
            })
        return schema

    def list_tables(self) -> List[str]:
        rows = self.fetch_all("SHOW TABLES")
        return [list(r.values())[0] for r in rows if r]

    def close(self) -> None:
        self.conn.close()
