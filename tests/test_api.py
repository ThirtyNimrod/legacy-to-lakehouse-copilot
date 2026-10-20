import pytest
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "target_environment" in data


def test_api_run_board():
    res = client.get("/api/runs/run_07")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == "run_07"
    assert "summary" in data
    assert "tables" in data
    assert len(data["tables"]) >= 6

    # Verify table row fields match ui-2.md
    t0 = data["tables"][0]
    assert "table_name" in t0
    assert "depends_on" in t0
    assert "checks" in t0
    assert "attempts" in t0
    assert "status" in t0


def test_api_fixtures_endpoints():
    for fx in ["passed", "mid_repair", "failed_closed"]:
        res = client.get(f"/api/fixtures/{fx}")
        assert res.status_code == 200
        data = res.json()
        assert "checks" in data
        assert "column_treatments" in data
        assert "status" in data


def test_api_thread_review_state():
    res = client.get("/api/threads/thread_cust_01/state")
    assert res.status_code == 200
    data = res.json()
    assert data["current_table"] == "raw_customers"
    assert len(data["checks"]) == 6
    assert data["status"] == "NEEDS_REVIEW"
    assert any(c["is_sensitive"] for c in data["column_treatments"])


def test_api_resume_approve():
    res = client.post(
        "/api/threads/thread_cust_01/resume",
        json={"action": "approve"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"


def test_api_resume_request_changes():
    res = client.post(
        "/api/threads/thread_orders_02/resume",
        json={"action": "changes", "feedback": "Fix tie-breaker in window"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
