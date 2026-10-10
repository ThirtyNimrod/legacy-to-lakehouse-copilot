import tempfile
from pathlib import Path
import pytest
from src.tools.database import DuckDBRunner
from src.tools.harness import LegacyWarehouseHarness


@pytest.fixture
def temp_legacy_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "legacy.duckdb")
        harness = LegacyWarehouseHarness(db_path=db_path)
        ddl_map = harness.seed()
        runner = DuckDBRunner(db_path)
        yield runner, db_path, ddl_map
        runner.close()


@pytest.fixture
def temp_target_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "target.duckdb")
        runner = DuckDBRunner(db_path)
        yield runner, db_path
        runner.close()
