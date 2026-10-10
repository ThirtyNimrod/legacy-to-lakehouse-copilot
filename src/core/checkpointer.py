import sqlite3
from pathlib import Path
from typing import Optional
from langgraph.checkpoint.sqlite import SqliteSaver


def get_sqlite_checkpointer(db_path: str = "checkpoints.db") -> SqliteSaver:
    """Creates a persistent SQLite checkpointer for LangGraph human-in-the-loop state."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(conn)
